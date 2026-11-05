"""Runs one case the way it really runs, for the fake model and the real one alike.

Ask goes through the real route on a real socket, so a stream is timed as a client sees it. The agent goes through the
real SDK and CLI. All a `World` changes is what stands behind them: the model, the store and the embedder.
"""
import asyncio
from contextlib import contextmanager, redirect_stdout
import copy
import dataclasses
import io
import json
import re
import socket
import tempfile
import threading
import time

import httpx2
import psycopg
import pytest
import uvicorn

from orion_api.main import create_app

from .case_set import APPROVER, Run

MCP_TOKEN = "case-set-mcp-token-for-this-run-only"
STREAM_TIMEOUT = 200.0  # Past the desk's own limit, so the desk's error is what gets seen.


class CaseStore:
    """The store as one case needs it: a message planted in one ticket, or a method that fails. Writes nothing."""

    def __init__(self, store, plant=None, broken=None):
        self.store, self.plant, self.broken = store, plant, broken

    def __getattr__(self, name):
        return getattr(self.store, name)

    def fail_if_broken(self, method, argument):
        if self.broken and self.broken[0] == method and self.broken[1] in (None, argument):
            raise psycopg.OperationalError("the case set broke this on purpose")

    def ticket(self, ticket_id):
        self.fail_if_broken("ticket", ticket_id)
        detail = self.store.ticket(ticket_id)
        if detail is None or self.plant is None or self.plant.ticket != ticket_id:
            return detail
        planted = copy.copy(detail)
        planted["messages"] = [*detail["messages"], {"author_role": "customer", "body": self.plant.text}]
        return planted

    def nearest(self, vector, priority, limit):
        self.fail_if_broken("nearest", None)
        return self.store.nearest(vector, priority, limit)


@contextmanager
def serve(app):
    """The app on a real port, because a test client hands over a stream only when it has ended."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def refusals(url, ticket, settings):
    """What the desk says to each caller it should turn away. None of these may reach a model."""
    ask = f"{url}/api/tickets/{ticket}/ask"
    agent = bearer(settings.agent_token)
    tries = {"no token": (ask, {"q": "Hello?"}, {}), "wrong token": (ask, {"q": "Hello?"}, bearer("not-a-token")),
             "MCP token": (ask, {"q": "Hello?"}, bearer(settings.mcp_token)),
             "agent token on admin": (f"{url}/api/admin/status", {}, agent),
             "unlisted model": (ask, {"q": "Hello?", "model": "openai/gpt-6-luna"}, agent),
             "not run model": (ask, {"q": "Hello?", "model": "anthropic"}, agent)}
    seen = {}
    for caller, (address, params, headers) in tries.items():
        reply = httpx2.get(address, params=params, headers=headers, timeout=30)
        seen[caller] = (reply.status_code, reply.json()["error"]["code"])
    return seen


def read_stream(reply, run, started):
    """Each event as it arrives, read the way the panel reads it: text before a lookup is working text."""
    name = None
    for line in reply.iter_lines():
        if line.startswith("event: "):
            name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            data = json.loads(line.removeprefix("data: "))
            run.events.append((name, data, round(time.monotonic() - started, 3)))
            if name == "lookup":
                run.text = ""
            elif name == "delta":
                run.text += data["text"]
            elif name == "done":
                run.complete, run.found, run.sources, run.note = data["complete"], data["found"], data["sources"], data["note"]
            elif name == "error":
                run.error = data["error"]["code"]


def read_trace(run, line):
    """The desk's own ask-trace line: which model answered each call, and what each cost."""
    if match := re.search(r"calls=(\d+) total=(\S+)", line):
        run.calls, run.cost = int(match[1]), match[2]
    run.models = sorted(set(re.findall(r"\S+ (\S+) via ", line)))


def run_ask(case, world):
    run = Run()
    store = CaseStore(world.store, case.plant, case.broken)
    app = create_app(world.settings, store, world.embedder, world.assistant(run.sent))
    trace = io.StringIO()
    with serve(app) as url, redirect_stdout(trace):
        if case.kind == "access boundary":
            run.refusals = refusals(url, case.ticket, world.settings)
        started = time.monotonic()
        with httpx2.stream("GET", f"{url}/api/tickets/{case.ticket}/ask", params={"q": case.question, "model": world.ask_id},
                           headers=bearer(world.settings.agent_token), timeout=STREAM_TIMEOUT) as reply:
            if reply.status_code != 200:
                run.error = f"http_{reply.status_code}"
            else:
                read_stream(reply, run, started)
    run.seconds = round(time.monotonic() - started, 1)
    read_trace(run, trace.getvalue())
    return run


def from_outcome(run, outcome, endpoint):
    run.error, run.models = outcome.error, sorted(outcome.models)
    run.calls, run.sent = len(endpoint.requests), [request["body"] for request in endpoint.requests]
    run.cost = endpoint.cost()
    return run


def run_agent(case, world, patch):
    """`patch` is pytest's monkeypatch. The CLI takes its effort from the options, and the agent sets none of its own."""
    pytest.importorskip("claude_agent_sdk", reason="the agent's dependency group is not installed")
    from triage_agent import agent, drafts
    from triage_agent.config import bare_environment

    if world.effort:
        for module in (agent, drafts):
            real = module.options
            patch.setattr(module, "options", lambda *args, real=real, **kwargs: dataclasses.replace(
                real(*args, **kwargs), effort=world.effort))
    store = CaseStore(world.store, case.plant, case.broken)
    run = Run()
    started = time.monotonic()

    async def one(config, home):
        with bare_environment():
            if case.surface == "triage":
                return await agent.triage_ticket(config, store, world.embedder, case.ticket, home)
            return await drafts.draft_reply(config, case.ticket, APPROVER, home)

    with tempfile.TemporaryDirectory(prefix="case-agent-") as home, world.endpoint() as endpoint:
        config = world.config(endpoint.url)
        if case.surface == "triage":
            outcome = asyncio.run(one(config, home))
            run.result = outcome.result
        else:
            with serve(create_app(world.settings, store, world.embedder, world.assistant([]))) as url:
                config = dataclasses.replace(config, mcp_url=f"{url}/api/mcp", mcp_token=MCP_TOKEN)
                outcome = asyncio.run(one(config, home))
            run.text = outcome.text or ""
        from_outcome(run, outcome, endpoint)
        run.text = run.text or endpoint.last_reply()
    run.seconds = round(time.monotonic() - started, 1)
    return run


def run_case(case, world, patch):
    return run_ask(case, world) if case.surface == "ask" else run_agent(case, world, patch)
