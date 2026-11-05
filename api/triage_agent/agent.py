"""The agent: one Claude Agent SDK run per ticket, on the free model through OpenRouter, with the desk's read-only tools.

The Python around the model holds every limit and writes every proposal. The model only reads through TriageLookups, the
tools behind the Triage button, so it sees each ticket as it arrived and cannot copy the labels it is asked to propose.
Those tools run here, so the database login never reaches the CLI. The CLI gets an empty home and no built-in tools.
"""
import asyncio
from collections import deque
from dataclasses import dataclass, field
import hashlib
import logging
import re
import tempfile
import time
import uuid

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultError, ResultMessage, create_sdk_mcp_server,
                              query, tool)
import httpx
import psycopg
from psycopg_pool import PoolTimeout

from orion_api.assistant import TRIAGE_SYSTEM, ModelFailed, case_text, checked_triage
from orion_api.embedding import Embedder
from orion_api.lookups import TriageLookups, intake
from orion_api.store import Store

from .config import bare_environment, cli_environment

log = logging.getLogger("triage_agent")
SERVER = "desk"
# The CLI writes this name on messages it makes itself, such as an API error shown as a reply. No model made those.
NOT_A_MODEL = "<synthetic>"
QUEUE = """SELECT t.ticket_id, t.subject, t.status, t.category, t.priority, a.team
FROM tickets t LEFT JOIN agents a ON a.agent_id = t.agent_id
WHERE t.status IS DISTINCT FROM 'resolved'
ORDER BY t.created_at DESC NULLS LAST, t.ticket_id"""
LABELS = """SELECT ticket_id, category, priority, status, agent_id, component FROM tickets ORDER BY ticket_id"""
WRITABLE = """SELECT COUNT(*) AS n FROM pg_tables
WHERE schemaname = 'public' AND has_table_privilege(current_user, format('public.%I', tablename),
                                                    'INSERT, UPDATE, DELETE, TRUNCATE')"""
FORM_START = re.compile(r'\{\s*"category"')
RESULT_ERRORS = {"error_max_turns": "turn_limit", "error_max_budget_usd": "budget_limit"}
BUSY = {"model_busy"}


@dataclass
class Outcome:
    ticket_id: str
    result: dict | None = None
    error: str | None = None
    turns: int = 0
    tool_calls: int = 0
    estimated_usd: float = 0.0
    seconds: float = 0.0
    models: set = field(default_factory=set)


def desk_tools(lookups, broken):
    """TriageLookups as SDK tools. A failure goes in `broken`: "could not look" must not pass for "no record"."""
    def one(schema):
        @tool(schema["name"], schema["description"], schema["input_schema"])
        async def run(arguments):
            try:
                text, failed = await asyncio.to_thread(lookups.run, schema["name"], arguments)
            except Exception as exc:
                broken.append("database_unavailable" if isinstance(exc, (psycopg.OperationalError, PoolTimeout)) else "lookup_failed")
                text, failed = "The desk could not look that up.", True
            return {"content": [{"type": "text", "text": text}], "is_error": failed}
        return run
    return [one(schema) for schema in lookups.schemas]


def options(config, lookups, broken, home):
    tools = desk_tools(lookups, broken)
    return ClaudeAgentOptions(
        model=config.model,
        system_prompt=TRIAGE_SYSTEM,
        tools=[],  # No built-in tools: no shell, no files, no web, no subagents.
        allowed_tools=[f"mcp__{SERVER}__{item.name}" for item in tools],
        permission_mode="dontAsk",  # Anything not allowed above is refused, with nobody to ask.
        mcp_servers={SERVER: create_sdk_mcp_server(SERVER, tools=tools)},
        strict_mcp_config=True,
        setting_sources=[],  # Left out, the SDK loads ~/.claude and this repository's .claude.
        cwd=str(home),
        env=cli_environment(config, home),
        max_turns=config.limits.max_turns,
        max_budget_usd=config.limits.estimated_usd_per_ticket,
        stderr=lambda line: None,  # Each run warns that it does not know the model, and a failure could quote the request.
    )


def form_in(text):
    """The answer from its form onward. The free model sometimes writes its reasoning first, and nothing on this route can
    hold it to a schema. What comes back still has to pass the whole check, so nothing else gets in."""
    starts = [match.start() for match in FORM_START.finditer(text)]
    return text[starts[-1]:] if starts else text


def failure(final):
    """The reason a finished run gave no answer, or None."""
    if final is None:
        return "model_unavailable"
    if final.subtype in RESULT_ERRORS:
        return RESULT_ERRORS[final.subtype]
    if not final.is_error:
        return None
    return {429: "model_busy", 401: "model_key_refused", 403: "model_key_refused", 402: "model_credits",
            404: "model_not_found"}.get(final.api_error_status, "model_unavailable")


async def triage_ticket(config, store, embedder, ticket_id, home):
    """One ticket through the SDK. Whatever goes wrong comes back as Outcome.error, with no result."""
    started = time.monotonic()
    outcome = Outcome(ticket_id)
    try:
        detail = await asyncio.to_thread(store.ticket, ticket_id)
    except (psycopg.OperationalError, PoolTimeout):
        outcome.error = "database_unavailable"
        return outcome
    lookups = TriageLookups(store, embedder, detail)
    broken = []
    prompt = f"<case>{case_text(intake(detail))}</case>\n\nTriage this case."

    final = None

    async def conversation():
        nonlocal final
        async for message in query(prompt=prompt, options=options(config, lookups, broken, home)):
            if isinstance(message, AssistantMessage):
                outcome.models.add(message.model)
            elif isinstance(message, ResultMessage):
                final = message

    try:
        await asyncio.wait_for(conversation(), config.limits.seconds_per_ticket)
    except ResultError:
        pass  # The CLI exits with an error after an error result, and `final` already holds that result.
    except TimeoutError:
        outcome.error = "time_limit"
    except Exception as exc:  # The CLI's own failure text can quote the request, so only the type is kept.
        log.error("the agent failed: %s", type(exc).__name__)
        outcome.error = "agent_failed"
    if final is not None:
        outcome.turns, outcome.estimated_usd = final.num_turns, final.total_cost_usd or 0.0
        outcome.models |= set(final.model_usage or ())
    outcome.error = outcome.error or (broken[0] if broken else failure(final))
    if outcome.error is None:
        try:
            outcome.result = checked_triage(form_in(final.result or ""), lookups, config.model)
        except ModelFailed as failed:
            outcome.error = failed.body["code"]
    outcome.models.discard(NOT_A_MODEL)
    if outcome.models - {config.model}:
        outcome.result, outcome.error = None, "wrong_model"
    outcome.tool_calls = lookups.used
    outcome.seconds = round(time.monotonic() - started, 1)
    return outcome


def key_usage(config):
    """What OpenRouter has charged the key so far, in dollars. The check itself is free and uses no tokens."""
    response = httpx.get(f"{config.base_url}/v1/key", headers={"Authorization": f"Bearer {config.openrouter_key}"}, timeout=30)
    response.raise_for_status()
    return response.json()["data"]["usage"]


def fingerprint(store):
    """A hash of every ticket's labels, so a run can show it changed none of them."""
    with store.pool.connection() as db:
        rows = db.execute(LABELS).fetchall()
    return hashlib.sha256(repr([tuple(row.values()) for row in rows]).encode()).hexdigest()


def queue_rows(store):
    with store.pool.connection() as db:
        return db.execute(QUEUE).fetchall()


def require_read_only(store):
    with store.pool.connection() as db:
        if db.execute(WRITABLE).fetchone()["n"]:
            raise SystemExit("This login can write to the database. The agent needs the read-only login.")


def require_free_model(config):
    """Check OpenRouter's price for the model before a run. The name ending in :free is only a name."""
    response = httpx.get(f"{config.base_url}/v1/models/{config.model}/endpoints", timeout=30)
    response.raise_for_status()
    endpoints = response.json()["data"]["endpoints"]
    if not endpoints or any(float(price) for endpoint in endpoints for price in endpoint["pricing"].values()):
        raise SystemExit(f"OpenRouter does not list {config.model} as free.")


async def work_through(config, review, rows, run_id, triage, spent):
    """Triage `rows` until they run out or a limit stops the run. Returns the tally."""
    limits = config.limits
    waiting = deque(rows)
    tally = {"tried": 0, "proposed": 0, "failed": {}, "estimated_usd": 0.0, "real_usd": 0.0, "seconds": 0.0, "stopped_by": None}
    failures = 0
    started_at = await asyncio.to_thread(spent)

    async def attempt(row):
        outcome = await triage(row["ticket_id"])
        if outcome.error in BUSY:
            await asyncio.sleep(limits.busy_wait_seconds)
            retry = await triage(row["ticket_id"])
            retry.estimated_usd += outcome.estimated_usd
            return retry
        return outcome

    async def worker():
        nonlocal failures
        while waiting and tally["stopped_by"] is None:
            row = waiting.popleft()
            outcome = await attempt(row)
            tally["tried"] += 1
            tally["estimated_usd"] += outcome.estimated_usd
            tally["seconds"] += outcome.seconds
            if outcome.result is None:
                failures += 1
                tally["failed"][outcome.error] = tally["failed"].get(outcome.error, 0) + 1
            else:
                failures = 0
                tally["proposed"] += 1
                review.propose(run_id, row, outcome)
            print(row["ticket_id"], outcome.error or "proposed", f"{outcome.seconds}s", f"{outcome.turns} turns", flush=True)
            try:
                tally["real_usd"] = await asyncio.to_thread(spent) - started_at
            except (httpx.HTTPError, KeyError, ValueError):
                tally["stopped_by"] = "real_spend_unknown"
            if outcome.error == "wrong_model":
                tally["stopped_by"] = "wrong_model"
            elif tally["real_usd"] > limits.real_usd_per_run:
                tally["stopped_by"] = "real_spend_limit"
            elif tally["estimated_usd"] >= limits.estimated_usd_per_run:
                tally["stopped_by"] = tally["stopped_by"] or "estimated_budget_limit"
            elif failures >= limits.failures_in_a_row:
                tally["stopped_by"] = tally["stopped_by"] or "failures_in_a_row"

    await asyncio.gather(*(worker() for _ in range(limits.workers)))
    return tally


async def run_queue(config, review, tickets=None):
    """One run over the tickets with no proposal yet. A later run carries on where this one stopped."""
    limit = min(tickets or config.limits.tickets_per_run, config.limits.tickets_per_run)
    store = Store(config.database)
    store.open()
    try:
        require_read_only(store)
        await asyncio.to_thread(require_free_model, config)
        before = await asyncio.to_thread(fingerprint, store)
        queue = await asyncio.to_thread(queue_rows, store)
        done = review.proposals()
        rows = [row for row in queue if row["ticket_id"] not in done]
        run_id = uuid.uuid4().hex[:8]
        embedder = Embedder()
        print(f"run {run_id}: {len(queue)} in the queue, {len(rows)} with no proposal, taking up to {limit}", flush=True)
        # Transcripts hold ticket text, so they go when the run does.
        with tempfile.TemporaryDirectory(prefix="triage-agent-") as home, bare_environment():
            tally = await work_through(config, review, rows[:limit], run_id,
                                       lambda ticket_id: triage_ticket(config, store, embedder, ticket_id, home),
                                       lambda: key_usage(config))
        after = await asyncio.to_thread(fingerprint, store)
    finally:
        store.close()
    summary = {"type": "run", "run_id": run_id, "model": config.model, "queue": len(queue), "waiting": len(rows), **tally,
               "estimated_usd": round(tally["estimated_usd"], 4), "seconds": round(tally["seconds"], 1),
               "tickets_unchanged": before == after}
    review.add(summary)
    return summary
