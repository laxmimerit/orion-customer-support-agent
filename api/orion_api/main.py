"""Read-only Orion desk API (plan increment 2).

Every data route is under /api and reads only orion_desk. Run it as a factory:

    uv run uvicorn orion_api.main:create_app --factory --port 8000
"""
from contextlib import asynccontextmanager
from http import HTTPStatus
import logging
import secrets

from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import psycopg
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from .models import AdminStatus, ErrorResponse, TicketDetail, TicketPage
from .settings import load_settings

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


def create_app(settings=None, store_instance=None):
    """Build the app. Tests pass their own settings and store; uvicorn passes neither."""
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

    @app.get("/api/admin/status", response_model=AdminStatus, tags=["admin"],
             responses=errors(401, 403, 503), summary="Row count of every table (admin token only)")
    def admin_status(_: str = Depends(require_admin), db=Depends(store)):
        return {"database": db.database, "tables": db.table_counts()}

    return app
