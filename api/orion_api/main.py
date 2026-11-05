"""Read-only Orion desk API (plan increment 2).

Every data route is under /api and reads only orion_desk. Run it as a factory:

    uv run uvicorn orion_api.main:create_app --factory --port 8000
"""
import asyncio
from contextlib import asynccontextmanager
from http import HTTPStatus
import json
import logging
import re
import secrets
from typing import Literal

from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import psycopg
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from .assistant import COMPOSE_LABEL, DEFAULT_MODEL, MODELS, Assistant, ModelFailed, case_text
from .embedding import Embedder
from .lookups import NOTE_LIMIT, ComposeLookups, Lookups, TriageLookups, intake
from .mail import TICKET_ID, Mailbox, MailProblem, new_links, subject_ids
from .mail_sender import MailSender
from .mail_writer import MailWriter
from .mcp import PARSE_ERROR
from .mcp import answer as mcp_answer
from .mcp import failure as mcp_failure
from .models import (AdminStatus, AllowedModel, ApproveRequest, Article, ArticleSummary, BacklogRow, CaseNote, CaseNotes,
                     CategoryRow, Company, ComposeRequest, CustomerListItem, CustomerProfile, Draft, DraftState,
                     ErrorResponse, FirstReplyRow, FollowUp, LanguageModels, LinkRequest, Listing, MailAction, MailMatch,
                     MailMessage, MailStatus, MailSync, NoteRequest, PriorityRow, Report, SearchResults, SimilarTickets,
                     Snapshot, TicketDetail, TicketPage, Triage, VolumeRow)
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


def mailbox(request: Request):
    return request.app.state.mailbox


def mail_writer(request: Request):
    return request.app.state.mail_writer


def mail_sender(request: Request):
    return request.app.state.mail_sender


def allowed_model(model: str = Query(DEFAULT_MODEL, max_length=64,
                                     description="An `id` from /api/language-models/allow-list")):
    """Not a Literal, as other fixed choices are: the allow-list is the point here, so a refusal says which rule it hit."""
    line = MODELS.get(model)
    if line is None:
        raise ApiError(422, "model_not_allowed", f"{model!r} is not on the desk's model list.")
    if not line.run:
        raise ApiError(422, "model_not_run", f"{line.label} on {line.provider} is listed but has not been run, so the desk will not call it.")
    return line


async def unless_gone(request, work):
    """Await `work`, and cancel it if the client leaves. A stream stops by itself when nobody reads it; a plain response
    would run to the end, and spend the model's tokens, for nobody."""
    task = asyncio.ensure_future(work)
    while not (await asyncio.wait({task}, timeout=DISCONNECT_CHECK))[0]:
        if await request.is_disconnected():
            task.cancel()
            raise ApiError(503, "client_gone", "The client left before the answer finished.")
    return task.result()


UNLINKED_SHOWN = 100
LATE_SHOWN = 100
MATCH_POOL = 50  # Nearest documents looked at for a duplicate; most tickets are resolved, so the pool has to be wide.
MATCH_FLOOR = 0.65  # Measured on the test mail: real issues scored 0.69 to 0.70, junk text 0.49 to 0.56.
MAIL_LINE = "luna-high"  # Mail goes to a line marked `mail` and no other.
MAIL_PROBLEMS = {
    "too_soon": (429, "mail_sync_too_soon", "The desk read the label under a minute ago. Try again shortly."),
    "not_set_up": (503, "mail_not_set_up", "The customer mailbox is not set up."),
    "unavailable": (503, "mail_unavailable", "The customer mailbox did not answer. Try again shortly."),
    "recipient_not_allowed": (422, "recipient_not_allowed", "The desk sends only to its own mailbox or a plus form of it."),
}


def reply_subject(subject, ticket_id):
    """`Re:` and the original subject unchanged, on one line, because Gmail starts a new conversation if the words change.
    Only a subject with no ticket ID gains one in square brackets (contract C7)."""
    line = " ".join((subject or "").split())
    replied = line if re.match(r"re:", line, re.IGNORECASE) else f"Re: {line}"
    return replied if ticket_id in TICKET_ID.findall(line) else f"{replied} [{ticket_id}]"


def hours(value):
    return f"{round(value, 2).normalize():f}"


def follow_up_draft(case):
    """An unsent status follow-up from the ticket's own fields, in the Orion reply voice. It is text to read: it is not
    stored, and it can't be approved or sent. A reply goes through Compose, on a mail linked to the case."""
    ticket_id, subject = case["ticket_id"], case["subject"] or "No subject recorded"
    lines = [f"This is a follow-up on {ticket_id}, {subject}. Its status is {case['status'] or 'not recorded'}."]
    if case["late_reply"]:
        done = case["first_response_hours"]
        target = hours(case["sla_response_hours"])
        lines.append(f"No first response is recorded yet, against our {target} hour target." if done is None
                     else f"The first response took {hours(done)} hours against our {target} hour target.")
    if case["late_resolution"]:
        lines.append(f"It has not been resolved yet, against our {hours(case['sla_resolution_hours'])} hour target.")
    lines.append("We don't yet know when this will be resolved. We will write again once we have checked.")
    approver = case["approver"] or "no agent on this case, so name one before approving"
    return (f"DRAFT. NOT SENT. Awaiting approval by: {approver}\n\n"
            f"Ticket: {ticket_id}   Customer: {case['customer_id'] or 'not recorded'}, {case['company'] or 'not recorded'}\n\n"
            f"Subject: Re: {ticket_id}, {subject}\n\nHello,\n\n" + "\n\n".join(lines) + "\n\nOrion Support\n\n"
            "--- Notes for the approver (not part of the reply) ---\n"
            "Questions found: not checked. Read the case and answer each question before this goes out.\n"
            "Sources used: ticket status and target fields.\n"
            "Not known / needs checking: when the case will be resolved.")


def draft_rows(db, draft_id):
    rows = db.draft_actions(draft_id)
    if rows is None or "drafted" not in rows:
        raise ApiError(404, "draft_not_found", f"No draft has the ID {draft_id!r}.")
    return rows

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


def create_app(settings=None, store_instance=None, embedder_instance=None, assistant_instance=None, mailbox_instance=None,
               mail_writer_instance=None, mail_sender_instance=None):
    """Build the app. Tests pass their own settings, store, embedder, assistant and mailbox; uvicorn passes none."""
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
    app.state.mailbox = mailbox_instance or Mailbox(settings)
    app.state.mail_writer = mail_writer_instance or MailWriter(settings)
    app.state.mail_sender = mail_sender_instance or MailSender(settings)
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

    @app.get("/api/tickets/{ticket_id}/mail", response_model=Listing[MailMessage], tags=["tickets"],
             responses=errors(401, 404, 422, 503), summary="Customer mail linked to the ticket")
    def list_ticket_mail(ticket_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
        """Exact, case-sensitive ID lookup (M01). Oldest first. Mail is as the sender wrote it, and nothing checks who
        sent it. A ticket with no mail has an empty list."""
        items = db.ticket_mail(ticket_id)
        if items is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        return {"total": len(items), "items": items}

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
        chosen=Depends(allowed_model),
        db=Depends(store),
        model=Depends(assistant),
        search_model=Depends(embedder),
    ):
        """Exact, case-sensitive ID lookup (M01). The ticket, its messages and its customer go to the language model,
        which can read other tickets, customers and help articles through read-only tools, all without emails or
        dates. OpenRouter also runs a sandboxed shell with no network for it, and, only when `web` is true, web search
        and web fetch, each with a limit per question. A model line marked `mail` can also read customer mail, but
        not when `web` is true. Nothing is stored or sent to the customer, so a question knows
        the last one only through `note`, which the client sends back. Events: `lookup` has `label`,
        and any `delta` text before it was working text to drop; `delta` has `text`; `done` has `complete`, false when
        the answer was cut short, `found`, false when the model says the records don't hold the answer, `sources`,
        the records the answer names that the case or a lookup returned, each with `kind`, `id` and `title`, `pages`,
        every web page a web tool gave, each with `url` and `title` (null when it was fetched, because OpenRouter does
        not say if a fetch worked), `searches`, the words the model searched for, and `note`, for the next question,
        or null; `error` has the usual error body,
        because the status is already sent. The desk calls only the model named, and a failure is never retried on
        another: `model_not_found`, `model_timeout`, `model_daily_limit` and `wrong_model` arrive as `error` events, and so do
        `database_unavailable` and `lookup_failed`, which mean a tool broke and not the model. A 422 `model_not_allowed`
        or `model_not_run` means nothing was called. A 503 `model_not_configured` means no key is set."""
        q = q.strip()
        if not q:
            raise ApiError(422, "invalid_request", "The question is empty.")
        detail = db.ticket(ticket_id)
        if detail is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        if not model.configured:
            raise ApiError(503, "model_not_configured", "No language model is set up. OPENROUTER_API_KEY is missing.")
        lookups = Lookups(db, search_model, detail, mail=chosen.mail and not web)
        answer = model.answer(case_text(detail), q, lookups, ServerTools(web), (note or "").strip() or None, chosen.ask)
        return StreamingResponse(answer, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store, no-transform"})

    # async, unlike the routes above: it waits on the model through the async client, so the store goes to a thread.
    @app.get("/api/tickets/{ticket_id}/triage", response_model=Triage, tags=["tickets"],
             responses=errors(401, 402, 404, 422, 429, 502, 503, 504),
             summary="Category, priority and team from the language model, with the records it used")
    async def triage_ticket(
        request: Request,
        ticket_id: str = Path(max_length=32),
        _: str = Depends(role),
        chosen=Depends(allowed_model),
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
        the same ticket can come back different. The desk calls only the model named: a 422 `model_not_allowed` or
        `model_not_run` means nothing was called, and a 504 `model_timeout` means it did not finish in time. A 503
        `model_not_configured` means no key is set."""
        detail = await asyncio.to_thread(db.ticket, ticket_id)
        if detail is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        if not model.configured:
            raise ApiError(503, "model_not_configured", "No language model is set up. OPENROUTER_API_KEY is missing.")
        try:
            return await unless_gone(request, model.triage(case_text(intake(detail)), TriageLookups(db, search_model, detail), chosen.triage))
        except ModelFailed as failed:
            raise ApiError(failed.body["status"], failed.body["code"], failed.body["message"]) from None

    @app.get("/api/tickets/{ticket_id}/notes", response_model=CaseNotes, tags=["tickets"],
             responses=errors(401, 404, 422, 503), summary="Internal notes and handoffs on the ticket, oldest first")
    def list_case_notes(ticket_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
        """Exact, case-sensitive ID lookup (M01). Notes are for agents: no model tool, draft or mail reads them. `author`
        and `handed_to` are names picked by whoever held the shared token. `agents` lists the names to pick from."""
        rows = db.case_notes(ticket_id)
        if rows is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        return {"total": len(rows), "items": rows, "agents": db.approvers()}

    @app.post("/api/tickets/{ticket_id}/notes", response_model=CaseNote, tags=["tickets"],
              responses=errors(401, 404, 422, 503), summary="Add an internal note, or hand the case to another agent")
    def add_case_note(form: NoteRequest, ticket_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store),
                      writer=Depends(mail_writer)):
        """A note with `handed_to` is a handoff, recorded here only: the ticket's stored agent doesn't change. A note can't
        be changed or removed."""
        if not db.existing_tickets({ticket_id}):
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        if not writer.configured:
            raise ApiError(503, "mail_writer_not_set_up", "The login that stores mail is not set up.")
        body = form.body.strip()
        if not body:
            raise ApiError(422, "invalid_request", "Write the note first.")
        agents = db.approvers()
        if form.author not in agents or form.handed_to not in (None, *agents):
            raise ApiError(422, "unknown_agent", "Pick a name from the desk's agents.")
        if form.handed_to == form.author:
            raise ApiError(422, "same_agent", "Hand the case to another agent.")
        row = {"note_id": "NT" + secrets.token_hex(6).upper(), "ticket_id": ticket_id, "author": form.author,
               "handed_to": form.handed_to, "body": body}
        return {**row, "noted_at": writer.add_note(row)}

    # async, as triage is: it waits on the model, so the store and both mail steps go to threads.
    @app.post("/api/tickets/{ticket_id}/drafts", response_model=Draft, tags=["tickets"],
              responses=errors(401, 402, 404, 422, 429, 502, 503, 504),
              summary="Draft a reply to one linked mail on GPT-6 Luna, citing one help article")
    async def compose_draft(
        request: Request,
        form: ComposeRequest,
        ticket_id: str = Path(max_length=32),
        _: str = Depends(role),
        db=Depends(store),
        model=Depends(assistant),
        search_model=Depends(embedder),
        box=Depends(mailbox),
        sender=Depends(mail_sender),
        writer=Depends(mail_writer),
    ):
        """Always Luna: this route takes no model. The recipient is the From address of the mail answered, read from the
        label, and a 422 `recipient_not_allowed` comes before any model call if that isn't the desk's own mailbox or a
        plus form of it. A 422 `insufficient_evidence` means the model read no article that supports a reply, and no
        draft is stored. A stored draft can't change: a different text is a new draft. Nothing is sent here."""
        detail = await asyncio.to_thread(db.ticket, ticket_id)
        if detail is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        mail = await asyncio.to_thread(db.thread_mail, ticket_id, form.mail_id)
        if mail is None:
            raise ApiError(404, "mail_not_found", f"No mail on this ticket has the ID {form.mail_id!r}.")
        if not model.configured:
            raise ApiError(503, "model_not_configured", "No language model is set up. OPENROUTER_API_KEY is missing.")
        if not writer.configured:
            raise ApiError(503, "mail_writer_not_set_up", "The login that stores mail is not set up.")
        try:
            recipient = await asyncio.to_thread(box.reply_address, mail["rfc_message_id"])
        except MailProblem as problem:
            raise ApiError(*MAIL_PROBLEMS[problem.code]) from None
        if not sender.allowed(recipient):
            raise ApiError(*MAIL_PROBLEMS["recipient_not_allowed"])
        lookups = ComposeLookups(db, search_model, detail)
        try:
            decision = await unless_gone(request, model.compose(case_text(detail), mail, form.template, form.tone,
                                                                form.language, lookups))
        except ModelFailed as failed:
            raise ApiError(failed.body["status"], failed.body["code"], failed.body["message"]) from None
        article = await asyncio.to_thread(db.article, decision["article_id"])
        cited = f"\n\nHelp article: {article['article_id']} · {article['title']}"
        draft = {"recipient": recipient, "subject": reply_subject(mail["subject"], ticket_id),
                 "body": decision["reply"].strip() + cited, "english": decision["english"].strip() + cited,
                 "language": form.language, "article_id": article["article_id"], "article_title": article["title"]}
        thread = {"in_reply_to": mail["rfc_message_id"],
                  "references": f"{mail['replies_to']} {mail['rfc_message_id']}".strip()}
        draft_id = "DR" + secrets.token_hex(6).upper()
        await asyncio.to_thread(writer.add_action, {
            "draft_id": draft_id, "action": "drafted", "ticket_id": ticket_id, "actor": COMPOSE_LABEL,
            "details": json.dumps({**draft, **thread, "template": form.template, "tone": form.tone})})
        return {**draft, "draft_id": draft_id, "status": "drafted", "approvers": await asyncio.to_thread(db.approvers)}

    @app.get("/api/tickets/{ticket_id}/actions", response_model=Listing[MailAction], tags=["tickets"],
             responses=errors(401, 404, 422, 503), summary="Every draft, approval and send on the ticket, oldest first")
    def list_ticket_actions(ticket_id: str = Path(max_length=32), _: str = Depends(role), db=Depends(store)):
        """Exact, case-sensitive ID lookup (M01). Rows are never changed. `actor` is a name picked by whoever held the
        shared token, not a signed-in person. A ticket with no actions has an empty list."""
        rows = db.ticket_actions(ticket_id)
        if rows is None:
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {ticket_id!r}.")
        drafts = {row["draft_id"]: json.loads(row["details"]) for row in rows if row["action"] == "drafted"}
        items = [{**row, **{name: drafts.get(row["draft_id"], {}).get(name) for name in ("recipient", "subject", "article_id")}}
                 for row in rows]
        return {"total": len(items), "items": items}

    @app.post("/api/drafts/{draft_id}/approve", response_model=DraftState, tags=["drafts"],
              responses=errors(401, 404, 409, 422, 503), summary="Record who approved the exact draft")
    def approve_draft(form: ApproveRequest, draft_id: str = Path(max_length=16), _: str = Depends(role), db=Depends(store),
                      writer=Depends(mail_writer)):
        """`approved_by` must be a name in the agents table. The shared token can't prove who pressed the button, so this
        records a name, not a signed-in person. A draft is approved once: a 409 `already_approved` changes nothing."""
        rows = draft_rows(db, draft_id)
        if form.approved_by not in db.approvers():
            raise ApiError(422, "unknown_approver", "Pick a name from the desk's agents.")
        added = writer.add_action({"draft_id": draft_id, "action": "approved", "ticket_id": rows["drafted"]["ticket_id"],
                                   "actor": form.approved_by, "details": None})
        if not added:
            raise ApiError(409, "already_approved", "This draft has already been approved.")
        return {"draft_id": draft_id, "status": "approved", "approved_by": form.approved_by}

    @app.post("/api/drafts/{draft_id}/send", response_model=DraftState, tags=["drafts"],
              responses=errors(401, 404, 409, 422, 503), summary="Send an approved draft over SMTP in the mail's thread")
    def send_draft(draft_id: str = Path(max_length=16), _: str = Depends(role), db=Depends(store), sender=Depends(mail_sender),
                   writer=Depends(mail_writer)):
        """Only an approved draft, and at most once: the `sending` row goes in first, and its primary key stops a second
        press. A failure logs `failed` and is never retried, because SMTP can fail after the server took the mail. Compose
        a new draft to try again. The stored text goes out exactly as it was approved."""
        rows = draft_rows(db, draft_id)
        if "approved" not in rows:
            raise ApiError(409, "not_approved", "Only an approved draft can be sent.")
        approver, ticket_id = rows["approved"]["actor"], rows["drafted"]["ticket_id"]

        def log_action(action, details=None):
            return writer.add_action({"draft_id": draft_id, "action": action, "ticket_id": ticket_id, "actor": approver,
                                      "details": details})

        if not log_action("sending"):
            raise ApiError(409, "already_sent", "This draft has already gone to the mail server.")
        try:
            message_id = sender.send(json.loads(rows["drafted"]["details"]))
        except MailProblem as problem:
            log_action("failed", problem.code)
            raise ApiError(*MAIL_PROBLEMS[problem.code]) from None
        log_action("sent", message_id)
        return {"draft_id": draft_id, "status": "sent", "approved_by": approver}

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
             responses=errors(401), summary="The language model connection and every line of the allow-list")
    async def get_language_models(_: str = Depends(role), model=Depends(assistant)):
        """`state` comes from a live check of the key and each model that has been run, which uses no tokens. A line
        that has not been run is `not_run` and is not checked. The key is never returned."""
        return await model.connection()

    @app.get("/api/language-models/allow-list", response_model=Listing[AllowedModel], tags=["language-models"],
             responses=errors(401), summary="The models the desk may call, the default first")
    def get_allow_list(_: str = Depends(role)):
        """No check and no call, so a case page can read it on every load. `run` is false for a line the desk refuses."""
        return {"total": len(MODELS), "items": [line.listed() for line in MODELS.values()]}

    @app.get("/api/mail/status", response_model=MailStatus, tags=["mail"], responses=errors(401),
             summary="Whether the desk can reach the customer mailbox, and how much is under its label")
    def get_mail_status(_: str = Depends(role), box=Depends(mailbox)):
        """A live check at most once a minute. Other calls get the last answer, a failure included, so a change to the
        mailbox can take up to a minute to show. IMAP logs in and asks for the label's counts, which opens no message and marks
        none as read. SMTP logs in and quits, and this check sends nothing. `state` is the first check that did not
        pass, IMAP before SMTP. `label`, `messages` and `unread` stay null when they aren't known. The mailbox address
        and the password are never returned."""
        return box.status()

    @app.get("/api/mail/unlinked", response_model=Listing[MailMessage], tags=["mail"], responses=errors(401, 503),
             summary="Customer mail that matched no ticket, newest first")
    def list_unlinked_mail(_: str = Depends(role), db=Depends(store)):
        """`items` stops at 100, and `total` counts them all."""
        total, items = db.unlinked_mail(UNLINKED_SHOWN)
        return {"total": total, "items": items}

    # async, as triage is. Always a line marked `mail`, so this route takes no model.
    @app.get("/api/mail/{mail_id}/triage", response_model=Triage, tags=["mail"],
             responses=errors(401, 402, 404, 422, 429, 502, 503, 504),
             summary="Category, priority and team for one mail, from GPT-6 Luna")
    async def triage_mail(
        request: Request,
        mail_id: str = Path(max_length=16),
        _: str = Depends(role),
        db=Depends(store),
        model=Depends(assistant),
        search_model=Depends(embedder),
    ):
        """The model sees the mail's subject and body as a case that arrived by email, with no customer, and the reading
        tools triage has. Nothing is stored, and nothing is linked."""
        mail = await asyncio.to_thread(db.mail, mail_id)
        if mail is None:
            raise ApiError(404, "mail_not_found", f"No mail has the ID {mail_id!r}.")
        if not model.configured:
            raise ApiError(503, "model_not_configured", "No language model is set up. OPENROUTER_API_KEY is missing.")
        detail = {"ticket": {"ticket_id": mail_id, "subject": mail["subject"], "body": mail["body"], "channel": "email"},
                  "customer": None, "messages": []}
        try:
            return await unless_gone(request, model.triage(case_text(intake(detail)), TriageLookups(db, search_model, detail),
                                                           MODELS[MAIL_LINE].triage))
        except ModelFailed as failed:
            raise ApiError(failed.body["status"], failed.body["code"], failed.body["message"]) from None

    @app.get("/api/mail/{mail_id}/match", response_model=MailMatch, tags=["mail"], responses=errors(401, 404, 422, 503),
             summary="The closest case still open, as a possible duplicate of one mail")
    def match_mail(mail_id: str = Path(max_length=16), _: str = Depends(role), db=Depends(store),
                   search_model=Depends(embedder)):
        """Nearest by meaning, not proof: a person decides. `match` is null when no active case is close enough."""
        mail = db.mail(mail_id)
        if mail is None:
            raise ApiError(404, "mail_not_found", f"No mail has the ID {mail_id!r}.")
        text = f"{mail['subject'] or ''}\n{mail['body'] or ''}".strip()
        hits = db.nearest(search_model.query(text), None, MATCH_POOL) if text else []
        best = next((hit for hit in hits if hit["kind"] == "ticket" and hit["status"] != "resolved"
                     and hit["similarity"] >= MATCH_FLOOR), None)
        return {"match": best and {"ticket_id": best["id"], "subject": best["title"], "status": best["status"],
                                   "similarity": best["similarity"]}}

    @app.post("/api/mail/{mail_id}/link", response_model=MailMessage, tags=["mail"],
              responses=errors(401, 404, 409, 422, 503), summary="Link one unlinked mail to a ticket by hand")
    def link_mail(form: LinkRequest, mail_id: str = Path(max_length=16), _: str = Depends(role), db=Depends(store),
                  writer=Depends(mail_writer)):
        """A link can't be changed: a 409 `mail_already_linked` changes nothing."""
        mail = db.mail(mail_id)
        if mail is None:
            raise ApiError(404, "mail_not_found", f"No mail has the ID {mail_id!r}.")
        if not db.existing_tickets({form.ticket_id}):
            raise ApiError(404, "ticket_not_found", f"No ticket has the ID {form.ticket_id!r}.")
        if not writer.configured:
            raise ApiError(503, "mail_writer_not_set_up", "The login that stores mail is not set up.")
        if not writer.add_link(mail_id, form.ticket_id):
            raise ApiError(409, "mail_already_linked", "This mail is already linked to a case.")
        return {**mail, "ticket_id": form.ticket_id, "linked_by": "manual"}

    @app.get("/api/follow-ups", response_model=Listing[FollowUp], tags=["follow-ups"], responses=errors(401, 503),
             summary="Active cases past a target, oldest first, each with an unsent follow-up draft")
    def list_follow_ups(_: str = Depends(role), db=Depends(store)):
        """Late as on the queue, aged at the data snapshot. `items` stops at 100, and `total` counts them all. A `draft`
        is text to read: it is not stored, and only Compose makes a reply that can be approved and sent."""
        total, rows = db.late_cases(LATE_SHOWN)
        return {"total": total, "items": [{**row, "draft": follow_up_draft(row)} for row in rows]}

    @app.post("/api/mail/sync", response_model=MailSync, tags=["mail"], responses=errors(401, 429, 503),
              summary="Copy new mail from the label into the desk and link it to tickets")
    def sync_mail(_: str = Depends(role), db=Depends(store), box=Depends(mailbox), writer=Depends(mail_writer)):
        """It reads the label without marking anything as read, adds rows to the two mail
        tables through their own login, and sends nothing. At most once a minute and 25 mails a sync; `remaining` says
        what is left. A subject with one known ticket ID links a mail, and a reply takes the ticket of what it answers."""
        if not writer.configured:
            raise ApiError(503, "mail_writer_not_set_up", "The login that stores mail is not set up.")
        stored = db.mail_index()
        try:
            rows, skipped, remaining = box.read_new({row["rfc_message_id"] for row in stored})
        except MailProblem as problem:
            raise ApiError(*MAIL_PROBLEMS[problem.code]) from None
        mails = [row for row in rows if row is not None]
        wanted = set().union(*(subject_ids(mail) for mail in mails)) if mails else set()
        links = new_links(mails, stored, db.existing_tickets(wanted) if wanted else set())
        writer.save(mails, links)
        new_ids = {mail["mail_id"] for mail in mails}
        return {"added": len(mails), "linked": len(links), "skipped": skipped + len(rows) - len(mails),
                "unlinked": len(new_ids - {link["mail_id"] for link in links}), "remaining": remaining}

    for path, name, row, summary in REPORT_ROUTES:
        app.get(f"/api/reports/{path}", response_model=Report[row], tags=["reports"],
                responses=errors(401, 503), summary=summary, description=report_description(name),
                name=f"report_{name}")(report_route(name))

    @app.get("/api/admin/status", response_model=AdminStatus, tags=["admin"],
             responses=errors(401, 403, 503), summary="Row count of every table (admin token only)")
    def admin_status(_: str = Depends(require_admin), db=Depends(store)):
        return {"database": db.database, "tables": db.table_counts()}

    return app
