"""Read-only Orion desk API (plan increment 2).

Every data route is under /api and reads only orion_desk. Run it as a factory:

    uv run uvicorn orion_api.main:create_app --factory --port 8000
"""
import asyncio
from contextlib import asynccontextmanager
from http import HTTPStatus
import json
import logging
import secrets
from typing import Literal

from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import psycopg
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from .assistant import Assistant, ModelFailed, case_text
from .embedding import Embedder
from .lookups import NOTE_LIMIT, Lookups, TriageLookups, intake
from .mcp import PARSE_ERROR
from .mcp import answer as mcp_answer
from .mcp import failure as mcp_failure
from .models import (AdminStatus, Article, ArticleSummary, BacklogRow, CategoryRow, Company, CustomerListItem,
                     CustomerProfile, ErrorResponse, FirstReplyRow, LanguageModels, Listing, PriorityRow, Report,
                     SearchResults, SimilarTickets, Snapshot, TicketDetail, TicketPage, Triage, VolumeRow)
from .server_tools import ServerTools
from .settings import load_settings
from .store import report_description

log = logging.getLogger("orion_api")
DISCONNECT_CHECK = 0.5  # Seconds between looks at whether the client is still there.
MCP_BODY_LIMIT = 16_384  # Bytes. The longest message this server understands is a few hundred.
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


def mcp_caller(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """Only ORION_MCP_TOKEN opens /api/mcp, and with that unset nothing does. It is carried outside the desk, so it opens
    this one route and no other, and the agent and admin tokens stay where they are."""
    if credentials is None:
        raise ApiError(401, "missing_token", "Send Authorization: Bearer <token>.", {"WWW-Authenticate": "Bearer"})
    expected = request.app.state.settings.mcp_token
    if not expected or not secrets.compare_digest(credentials.credentials.encode(), expected.encode()):
        raise ApiError(401, "invalid_token", "The token is not valid.", {"WWW-Authenticate": "Bearer"})


async def mcp_message(request: Request, _: None = Depends(mcp_caller)):
    """The body, read only once the token has passed, so a caller without one can't get an answer about their JSON."""
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MCP_BODY_LIMIT:
            return None
    try:
        return json.loads(body)
    except (ValueError, RecursionError):  # A short body of nothing but brackets is the second.
        return None


def require_admin(current: str = Depends(role)):
    if current != "admin":
        raise ApiError(403, "admin_only", "Only the admin token may open this route.")
    return current


def store(request: Request):
    return request.app.state.store


def embedder(request: Request):
    return request.app.state.embedder


def assistant(request: Request):
    return request.app.state.assistant


async def unless_gone(request, work):
    """Await `work`, and cancel it if the client leaves. A stream stops by itself when nobody reads it; a plain response
    would run to the end, and spend the model's tokens, for nobody."""
    task = asyncio.ensure_future(work)
    while not (await asyncio.wait({task}, timeout=DISCONNECT_CHECK))[0]:
        if await request.is_disconnected():
            task.cancel()
            raise ApiError(503, "client_gone", "The client left before the answer finished.")
    return task.result()


EVENT_STREAM = {200: {"description": "A stream of `lookup` and `delta` events, then one `done` or `error`",
                      "content": {"text/event-stream": {"schema": {"type": "string"}}}}}

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


def split_owner(owner):
    """company_documents.owner holds "Name · Team". No separator means no team; a null owner stays null."""
    if owner is None:
        return {"owner": None, "team": None}
    name, separator, team = owner.partition(" · ")
    return {"owner": name, "team": team if separator else None}


def create_app(settings=None, store_instance=None, embedder_instance=None, assistant_instance=None):
    """Build the app. Tests pass their own settings, store, embedder and assistant; uvicorn passes none."""
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
    app.state.assistant = assistant_instance or Assistant(settings.openrouter_api_key)
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
        """Queue order as on the legacy desk: `created_at` newest first, then `ticket_id`. `age_hours` is the
        ticket's age at the data snapshot, not today, and is null with no `created_at` or no snapshot."""
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

    @app.get("/api/tickets/{ticket_id}/knowledge", response_model=Listing[ArticleSummary], tags=["tickets"],
             responses=errors(401, 404, 422, 503), summary="Help articles titled exactly as the ticket's subject")
    def list_ticket_articles(ticket_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
        """Exact, case-sensitive ID lookup (M01). Articles are by ID. An article matches when its title equals the
        ticket's subject, the rule `related_tickets` uses. Every match is listed, because nothing records which of
        two articles with one title applies. A ticket with no match has an empty list."""
        items = db.ticket_articles(ticket_id)
        if items is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        return {"total": len(items), "items": items}

    @app.get("/api/tickets/{ticket_id}/similar", response_model=SimilarTickets, tags=["tickets"],
             responses=errors(401, 404, 422, 503), summary="Resolved tickets closest to this one, with why each matched")
    def list_similar_tickets(
        ticket_id: str = Path(max_length=32),
        limit: int = Query(10, ge=1, le=50),
        _: str = Depends(role),
        db=Depends(store),
    ):
        """Exact, case-sensitive ID lookup (M01). The ticket's stored embedding is compared with every other document;
        the resolved tickets among its 50 nearest are returned, closest first. `total`, `matched_on` and `replies`
        cover all of them, while `items` stops at `limit`. An item's `matched_on` may be empty: it is then close in
        meaning only. `articles` are titled as the ticket's subject and contain the most used reply. A ticket with no stored
        embedding has an empty list."""
        similar = db.similar_tickets(ticket_id)
        if similar is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        return {**similar, "items": similar["items"][:limit]}

    @app.get("/api/tickets/{ticket_id}/ask", response_class=StreamingResponse, tags=["tickets"],
             responses={**EVENT_STREAM, **errors(401, 404, 422, 503)},
             summary="Ask the language model from one case, answered as a stream with its sources")
    def ask_ticket(
        ticket_id: str = Path(max_length=32),
        q: str = Query(min_length=1, max_length=500, description="The agent's question"),
        web: bool = Query(False, description="Offer web search and web fetch for this question"),
        note: str | None = Query(None, max_length=NOTE_LIMIT, description="The note the last answer kept, if any"),
        _: str = Depends(role),
        db=Depends(store),
        model=Depends(assistant),
        search_model=Depends(embedder),
    ):
        """Exact, case-sensitive ID lookup (M01). The ticket, its messages and its customer go to the language model,
        which can read other tickets, customers and help articles through read-only tools, all without emails or
        dates. OpenRouter also runs a sandboxed shell with no network for it, and, only when `web` is true, web search
        and web fetch, each with a limit per question. Nothing is stored or sent to the customer, so a question knows
        the last one only through `note`, which the client sends back. Events: `lookup` has `label`,
        and any `delta` text before it was working text to drop; `delta` has `text`; `done` has `complete`, false when
        the answer was cut short, `found`, false when the model says the records don't hold the answer, `sources`,
        the records the answer names that the case or a lookup returned, each with `kind`, `id` and `title`, `pages`,
        every web page a web tool gave, each with `url` and `title` (null when it was fetched, because OpenRouter does
        not say if a fetch worked), `searches`, the words the model searched for, and `note`, for the next question,
        or null; `error` has the usual error body,
        because the status is already sent. A 503 `model_not_configured` means no key is set."""
        q = q.strip()
        if not q:
            raise ApiError(422, "invalid_request", "The question is empty.")
        detail = db.ticket(ticket_id)
        if detail is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        if not model.configured:
            raise ApiError(503, "model_not_configured", "No language model is set up. OPENROUTER_API_KEY is missing.")
        lookups = Lookups(db, search_model, detail)
        answer = model.answer(case_text(detail), q, lookups, ServerTools(web), (note or "").strip() or None)
        return StreamingResponse(answer, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store, no-transform"})

    # async, unlike the routes above: it waits on the model through the async client, so the store goes to a thread.
    @app.get("/api/tickets/{ticket_id}/triage", response_model=Triage, tags=["tickets"],
             responses=errors(401, 402, 404, 422, 429, 502, 503),
             summary="Category, priority and team from the language model, with the records it used")
    async def triage_ticket(
        request: Request,
        ticket_id: str = Path(max_length=32),
        _: str = Depends(role),
        db=Depends(store),
        model=Depends(assistant),
        search_model=Depends(embedder),
    ):
        """Exact, case-sensitive ID lookup (M01). The model sees the ticket as it arrived: subject, body, channel, the
        customer's own messages and the customer. The ticket's stored category, priority, component, targets, agent and
        replies are held back, here and in its tools, so a result can be compared with them. `category`, `priority` and
        `team` are closed lists, and an answer outside the form is a 502 `triage_invalid`, not a result. `record_ids`
        holds only records a tool returned: the open case is there only if the model read it, and an empty list means
        it relied on none. `dropped_ids` counts the IDs taken out because no tool returned them. Nothing is stored, so
        the same ticket can come back different. A 503 `model_not_configured` means no key is set."""
        detail = await asyncio.to_thread(db.ticket, ticket_id)
        if detail is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        if not model.configured:
            raise ApiError(503, "model_not_configured", "No language model is set up. OPENROUTER_API_KEY is missing.")
        try:
            return await unless_gone(request, model.triage(case_text(intake(detail)), TriageLookups(db, search_model, detail)))
        except ModelFailed as failed:
            raise ApiError(failed.body["status"], failed.body["code"], failed.body["message"]) from None

    @app.post("/api/mcp", tags=["mcp"], responses=errors(401, 503), summary="Read one ticket over MCP")
    def mcp(message=Depends(mcp_message), db=Depends(store)):
        """MCP's Streamable HTTP transport, with one read-only tool. A POST because MCP sends everything that way; it
        changes nothing. Takes ORION_MCP_TOKEN only. The body is a JSON-RPC message, read after the token is checked.
        There is no response_model, as the answer is JSON-RPC: case_text's named fields are the filter here."""
        reply = mcp_failure(None, PARSE_ERROR, "The body is not JSON.") if message is None else mcp_answer(message, db)
        return Response(status_code=202) if reply is None else JSONResponse(reply)

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

    @app.get("/api/customers", response_model=Listing[CustomerListItem], tags=["customers"],
             responses=errors(401, 503), summary="Every customer with plan and case counts, by company")
    def list_customers(_: str = Depends(role), db=Depends(store)):
        """`active_cases` counts tickets not resolved, a missing status included; `all_cases` counts every ticket."""
        items = db.customers()
        return {"total": len(items), "items": items}

    @app.get("/api/customers/{customer_id}", response_model=CustomerProfile, tags=["customers"],
             responses=errors(401, 404, 422, 503), summary="One customer with subscription, tickets and invoices")
    def get_customer(customer_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
        """Exact, case-sensitive ID lookup. Tickets are newest first, invoices oldest first."""
        profile = db.customer(customer_id)
        if profile is None:
            raise ApiError(404, "customer_not_found", f"No customer has the ID {customer_id!r}.")
        return profile

    @app.get("/api/knowledge", response_model=Listing[ArticleSummary], tags=["knowledge"],
             responses=errors(401, 503), summary="Every help article, by ID")
    def list_articles(_: str = Depends(role), db=Depends(store)):
        items = db.articles()
        return {"total": len(items), "items": items}

    @app.get("/api/knowledge/{article_id}", response_model=Article, tags=["knowledge"],
             responses=errors(401, 404, 422, 503), summary="One help article with related tickets")
    def get_article(article_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
        """Related tickets have the article title as their exact subject: at most 5 here, unresolved first,
        then newest, with `total` counting them all. `more_in_category` lists the category's other articles."""
        article = db.article(article_id)
        if article is None:
            raise ApiError(404, "article_not_found", f"No article has the ID {article_id!r}.")
        return article

    @app.get("/api/company", response_model=Company, tags=["company"], responses=errors(401, 503),
             summary="Company documents and staff requests")
    def get_company(_: str = Depends(role), db=Depends(store)):
        sections, staff_requests = db.company()
        return {"sections": [{**row, **split_owner(row["owner"])} for row in sections],
                "staff_requests": staff_requests}

    @app.get("/api/snapshot", response_model=Snapshot, tags=["snapshot"], responses=errors(401, 404, 503),
             summary="When the lab data snapshot was taken")
    def get_snapshot(_: str = Depends(role), db=Depends(store)):
        """The moment the lab data was frozen, in UTC. Reports age tickets at this time, not today. It is not when
        the data was copied into orion_desk. `snapshot_utc` is null if the row records no time."""
        snapshot = db.snapshot()
        if snapshot is None:
            raise ApiError(404, "snapshot_not_found", "No data snapshot is recorded.")
        return snapshot

    # async, unlike the routes above: it reads no store, and only waits on the network through the async client.
    @app.get("/api/language-models", response_model=LanguageModels, tags=["language-models"],
             responses=errors(401), summary="The language model connection and the providers not set up")
    async def get_language_models(_: str = Depends(role), model=Depends(assistant)):
        """`state` comes from a live check of the key and the model, which uses no tokens. The key is never returned."""
        return await model.connection()

    for path, name, row, summary in REPORT_ROUTES:
        app.get(f"/api/reports/{path}", response_model=Report[row], tags=["reports"],
                responses=errors(401, 503), summary=summary, description=report_description(name),
                name=f"report_{name}")(report_route(name))

    @app.get("/api/admin/status", response_model=AdminStatus, tags=["admin"],
             responses=errors(401, 403, 503), summary="Row count of every table (admin token only)")
    def admin_status(_: str = Depends(require_admin), db=Depends(store)):
        return {"database": db.database, "tables": db.table_counts()}

    return app
