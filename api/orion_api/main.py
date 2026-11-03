"""Read-only Orion desk API (plan increment 2).

Every data route is under /api and reads only orion_desk. Run it as a factory:

    uv run uvicorn orion_api.main:create_app --factory --port 8000
"""
from contextlib import asynccontextmanager
from http import HTTPStatus
import logging
import secrets
from typing import Literal

from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import psycopg
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from .embedding import Embedder
from .models import (AdminStatus, BacklogRow, CategoryRow, ErrorResponse, FirstReplyRow, PriorityRow, Report,
                     SearchResults, TicketDetail, TicketPage, VolumeRow)
from .settings import load_settings
from .store import report_description

log = logging.getLogger("orion_api")
bearer = HTTPBearer(auto_error=False, description="ORION_AGENT_TOKEN, or ORION_ADMIN_TOKEN for admin routes")


class ApiError(Exception):
    def __init__(self, status, code, message, headers=None):
        self.status, self.code, self.message, self.headers = status, code, message, headers


def error(status, code, message, details=None, headers=None):
    body = {"status": status, "code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse({"error": body}, status_code=status, headers=headers)


def errors(*statuses):
    return {status: {"model": ErrorResponse} for status in statuses}


def role(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise ApiError(401, "missing_token", "Send Authorization: Bearer <token>.", {"WWW-Authenticate": "Bearer"})
    settings = request.app.state.settings
    token = credentials.credentials.encode()
    if secrets.compare_digest(token, settings.admin_token.encode()):
        return "admin"
    if secrets.compare_digest(token, settings.agent_token.encode()):
        return "agent"
    raise ApiError(401, "invalid_token", "The token is not valid.", {"WWW-Authenticate": "Bearer"})


def require_admin(current: str = Depends(role)):
    if current != "admin":
        raise ApiError(403, "admin_only", "Only the admin token may open this route.")
    return current


def store(request: Request):
    return request.app.state.store


def embedder(request: Request):
    return request.app.state.embedder


# Read-only reports: URL path, SQL file in api/reports, row model, summary.
REPORT_ROUTES = (
    ("volume", "volume", VolumeRow, "Tickets created per month, resolved and unresolved"),
    ("backlog", "backlog", BacklogRow, "Unresolved tickets by status, aged at the data snapshot"),
    ("priority", "priority", PriorityRow, "Tickets, response times and satisfaction by priority"),
    ("category", "category", CategoryRow, "Tickets, response times and satisfaction by category"),
    ("first-reply", "first_reply", FirstReplyRow,
     "First replies met and missed against each ticket's own target, with satisfaction"),
)


def report_route(name):
    def route(_: str = Depends(role), db=Depends(store)):
        return {"report": name, "rows": db.report(name)}
    return route


def create_app(settings=None, store_instance=None, embedder_instance=None):
    """Build the app. Tests pass their own settings, store and embedder; uvicorn passes none."""
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app):
        if store_instance is not None:
            app.state.store = store_instance
            yield
            return
        from .store import Store
        app.state.store = Store(settings)
        app.state.store.open()
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(
        title="Orion desk API",
        version="0.1.0",
        summary="Read-only tickets, customers and messages from orion_desk (plan increment 2).",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.embedder = embedder_instance or Embedder()
    if store_instance is not None:
        app.state.store = store_instance

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        return error(exc.status, exc.code, exc.message, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        phrase = HTTPStatus(exc.status_code).phrase
        return error(exc.status_code, phrase.lower().replace(" ", "_"), phrase + ".", headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        details = [{"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]} for item in exc.errors()]
        return error(422, "invalid_request", "The request has invalid parameters.", details)

    @app.exception_handler(PoolTimeout)
    @app.exception_handler(psycopg.OperationalError)
    async def database_unavailable(request, exc):
        log.error("database unavailable: %s", type(exc).__name__)
        return error(503, "database_unavailable", "The database did not answer. Try again shortly.")

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        # Only the type is logged: driver messages can carry host names.
        log.error("unexpected error: %s", type(exc).__name__)
        return error(500, "internal_error", "Something went wrong on the server.")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/docs")

    @app.get("/api/tickets", response_model=TicketPage, tags=["tickets"], responses=errors(401, 422, 503),
             summary="List tickets, newest first")
    def list_tickets(
        page: int = Query(1, ge=1, le=100_000),
        page_size: int = Query(25, ge=1, le=100),
        _: str = Depends(role),
        db=Depends(store),
    ):
        """Queue order as on the legacy desk: `created_at` newest first, then `ticket_id`."""
        total, items = db.ticket_page(page_size, (page - 1) * page_size)
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @app.get("/api/tickets/{ticket_id}", response_model=TicketDetail, tags=["tickets"],
             responses=errors(401, 404, 422, 503), summary="One ticket with its customer and messages")
    def get_ticket(ticket_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
        """Exact, case-sensitive ID lookup (M01). Messages are oldest first (M02)."""
        detail = db.ticket(ticket_id)
        if detail is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        return detail

    @app.get("/api/search", response_model=SearchResults, tags=["search"], responses=errors(401, 422, 503),
             summary="Find tickets and help articles by meaning, or one ticket by its exact ID")
    def search(
        q: str = Query(min_length=1, max_length=500, description="Words to search for, or an exact ticket ID"),
        priority: Literal["P1", "P2", "P3", "P4"] | None = Query(None, description="Only tickets with this priority"),
        limit: int = Query(10, ge=1, le=50),
        _: str = Depends(role),
        db=Depends(store),
        model=Depends(embedder),
    ):
        """If `q` (trimmed) is exactly a ticket ID, case-sensitive as in M01, only that ticket comes back,
        whatever the filter. Otherwise `q` is embedded locally and the nearest tickets and articles are
        returned by cosine similarity. A priority filter leaves articles out, since they have no priority."""
        q = q.strip()
        if not q:
            raise ApiError(422, "invalid_request", "The query is empty.")
        ticket = db.exact_ticket(q)
        if ticket is not None:
            return {"query": q, "match": "exact_id", "items": [ticket]}
        return {"query": q, "match": "semantic", "items": db.nearest(model.query(q), priority, limit)}

    for path, name, row, summary in REPORT_ROUTES:
        app.get(f"/api/reports/{path}", response_model=Report[row], tags=["reports"],
                responses=errors(401, 503), summary=summary, description=report_description(name),
                name=f"report_{name}")(report_route(name))

    @app.get("/api/admin/status", response_model=AdminStatus, tags=["admin"],
             responses=errors(401, 403, 503), summary="Row count of every table (admin token only)")
    def admin_status(_: str = Depends(require_admin), db=Depends(store)):
        return {"database": db.database, "tables": db.table_counts()}

    return app
