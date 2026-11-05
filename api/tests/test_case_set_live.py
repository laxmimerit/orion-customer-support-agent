"""The case set on the real models and the real orion_desk. Marked live, so CI never runs it, and it needs asking for:

    ORION_LIVE_MODELS=free,luna-high uv run --locked --group agent pytest tests/test_case_set_live.py -m live -rf --tb=line

Luna is paid, so a plain `pytest -m live` skips these. ORION_CASE_ROUNDS repeats each case. ORION_CASE_OUT names a JSON
file for the results. A failed case stays failed: nothing here is marked as expected to fail, and only a busy model is
tried again, because that says nothing about the answer.

The agent's limits are its real ones, but it runs here on a model its own settings refuse. This file builds that config
for the test alone: `load_config` and `require_free_model` are unchanged, so `python -m triage_agent` stays free-only.
"""
from contextlib import contextmanager
import dataclasses
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time

import httpx
import httpx2
import pytest

from orion_api.assistant import BASE_URL, MODELS, Assistant
from orion_api.embedding import Embedder
from orion_api.settings import load_settings
from orion_api.store import Store

from .case_runner import MCP_TOKEN, run_case
from .case_set import CASES
from .conftest import CASE_RESULTS

CHOSEN = [name for name in os.environ.get("ORION_LIVE_MODELS", "").split(",") if name]
ROUNDS = range(1, int(os.environ.get("ORION_CASE_ROUNDS", "1")) + 1)
BUSY = {"model_busy"}
TRIES, BUSY_WAIT_SECONDS = 3, 60

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not CHOSEN, reason="set ORION_LIVE_MODELS=free,luna-high: these call OpenRouter, and Luna is paid")]


class Recorder(httpx2.AsyncHTTPTransport):
    """Keeps every request body, so a check can see what really left the desk."""

    def __init__(self, sent):
        super().__init__()
        self.sent = sent

    async def handle_async_request(self, request):
        self.sent.append(json.loads(request.content))
        return await super().handle_async_request(request)


class ModelProxy:
    """Sits between the CLI and OpenRouter on this machine, to see what the agent sends and what each call costs.

    The agent's own requests carry no provider rule, so `extra` adds the line's, as the desk does for Luna.
    """

    def __init__(self, extra):
        self.requests, self.costs, self.replies = [], [], []
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_HEAD(self):
                self.send_response(404)
                self.end_headers()

            do_GET = do_HEAD

            def do_POST(self):
                body = {**json.loads(self.rfile.read(int(self.headers["content-length"]))), **extra}
                proxy.requests.append({"body": body})
                headers = {name: value for name, value in self.headers.items()
                           if name.lower() in ("authorization", "content-type") or name.lower().startswith("anthropic-")}
                with httpx.stream("POST", BASE_URL + self.path, json=body, headers=headers, timeout=120) as reply:
                    self.send_response(reply.status_code)
                    self.send_header("content-type", reply.headers.get("content-type", "application/json"))
                    self.end_headers()
                    text, cost = "", None
                    for line in reply.iter_lines():
                        self.wfile.write(line.encode() + b"\n")
                        self.wfile.flush()
                        if line.startswith("data: {"):
                            event = json.loads(line.removeprefix("data: "))
                            text += (event.get("delta") or {}).get("text") or ""
                            cost = (event.get("usage") or {}).get("cost", cost)
                    proxy.costs.append(cost)
                    proxy.replies.append(text)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def cost(self):
        known = [cost for cost in self.costs if cost is not None]
        return f"${sum(known):.6f}" + ("" if len(known) == len(self.costs) else "+?")

    def last_reply(self):
        return self.replies[-1] if self.replies else ""


class LiveWorld:
    def __init__(self, line, settings, store, embedder):
        self.line, self.settings, self.store, self.embedder = line, settings, store, embedder
        self.ask_id = line.id
        self.effort = line.ask.options.get("output_config", {}).get("effort")

    def assistant(self, sent):
        return Assistant(self.settings.openrouter_api_key, lambda: httpx2.AsyncClient(transport=Recorder(sent)))

    @contextmanager
    def endpoint(self):
        proxy = ModelProxy({key: value for key, value in self.line.ask.options.items() if key == "provider"})
        yield proxy
        proxy.server.shutdown()

    def config(self, url):
        from triage_agent.config import load_config
        return dataclasses.replace(load_config(needs_database=False), model=self.line.model, base_url=url)


@pytest.fixture(scope="module")
def desk():
    try:
        settings = dataclasses.replace(load_settings(), mcp_token=MCP_TOKEN)
    except RuntimeError as reason:
        pytest.skip(str(reason))
    if not settings.openrouter_api_key:
        pytest.skip("OPENROUTER_API_KEY is not set")
    store = Store(settings)
    store.open()
    yield settings, store, Embedder()
    store.close()


@pytest.fixture(scope="module", autouse=True)
def write_results():
    yield
    if out := os.environ.get("ORION_CASE_OUT"):
        Path(out).write_text(json.dumps(CASE_RESULTS, indent=2, default=str) + "\n")


def summary(case, run, line, attempt, problems):
    return {"case": case.id, "kind": case.kind, "surface": case.surface, "line": line, "attempts": attempt, "passed": not problems,
            "problems": problems, "error": run.error, "text": run.text, "found": run.found, "sources": run.sources,
            "note": run.note, "result": run.result, "models": run.models, "calls": run.calls, "cost": run.cost,
            "seconds": run.seconds, "first_delta": next((at for name, _, at in run.events if name == "delta"), None),
            "deltas": sum(name == "delta" for name, _, _ in run.events)}


@pytest.mark.parametrize("attempt_round", ROUNDS, ids=lambda number: f"round{number}")
@pytest.mark.parametrize("line", CHOSEN or ["none"])
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_case(case, line, attempt_round, desk, monkeypatch):
    settings, store, embedder = desk
    world = LiveWorld(MODELS[line], settings, store, embedder)
    for attempt in range(1, TRIES + 1):
        run = run_case(case, world, monkeypatch)
        monkeypatch.undo()
        if run.error not in BUSY or attempt == TRIES:
            break
        time.sleep(BUSY_WAIT_SECONDS)
    problems = case.check(case, run, store)
    wrong = set(run.models) - {MODELS[line].model}
    if wrong:
        problems.append(f"answered by {sorted(wrong)}")
    if world.effort and any(body.get("output_config", {}).get("effort") != world.effort for body in run.sent):
        problems.append(f"a request did not carry effort {world.effort}")
    CASE_RESULTS.append(summary(case, run, line, attempt, problems))
    assert not problems, f"{case.id} on {line}: {'; '.join(problems)}\n--- what it produced ---\n{run.text or run.result}"
