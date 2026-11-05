"""The agent: the real SDK and its real CLI against a local stand-in for OpenRouter, so no request leaves this machine.

The stand-in logs every request. That is how these tests see what the agent really offers and sends, rather than what
its options ask for. The live tests at the end read the real orion_desk through the read-only login.
"""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess
import threading
import time
from types import SimpleNamespace

import httpx
import psycopg
import pytest

pytest.importorskip("claude_agent_sdk", reason="the agent's dependency group is not installed")

from triage_agent.agent import (Outcome, fingerprint, options, queue_rows, require_free_model,  # noqa: E402
                                require_read_only, triage_ticket, work_through)
from triage_agent.config import ENV_FILE, TOML_FILE, AgentConfig, Limits, bare_environment, load_config  # noqa: E402
from triage_agent.review import ReviewList  # noqa: E402

from orion_api.lookups import TriageLookups  # noqa: E402
from orion_api.store import Store  # noqa: E402

from .conftest import C0086, MESSAGES, SETTINGS, T00727  # noqa: E402

CASE = {"ticket": T00727, "customer": C0086, "messages": MESSAGES}

FREE = "test/model:free"
KEY = "sk-stand-in"
FORM = {"category": "account access", "priority": "P2", "team": "Customer care", "reason": "Invitation trouble.",
        "record_ids": []}
ANSWER = json.dumps(FORM)
DESK_TOOLS = {f"mcp__desk__{name}" for name in ("search_records", "list_articles", "read_ticket", "find_customers",
                                                "read_customer", "read_article")}
LIMITS = dict(max_turns=6, estimated_usd_per_ticket=5.0, estimated_usd_per_run=5.0, real_usd_per_run=0.0, tickets_per_run=25,
              seconds_per_ticket=60, failures_in_a_row=3, busy_wait_seconds=0, workers=1)


def tool_call(name, **arguments):
    return {"tool": name, "input": arguments}


def stream(reply, model):
    usage = {"input_tokens": reply.get("input_tokens", 100), "output_tokens": 10}
    start = {"id": "msg_1", "type": "message", "role": "assistant", "model": model, "content": [], "stop_reason": None,
             "stop_sequence": None, "usage": usage}
    if "tool" in reply:
        block = {"type": "tool_use", "id": f"toolu_{time.monotonic_ns()}", "name": reply["tool"], "input": {}}
        delta = {"type": "input_json_delta", "partial_json": json.dumps(reply["input"])}
    else:
        block, delta = {"type": "text", "text": ""}, {"type": "text_delta", "text": reply["text"]}
    events = [("message_start", {"message": start}), ("content_block_start", {"index": 0, "content_block": block}),
              ("content_block_delta", {"index": 0, "delta": delta}), ("content_block_stop", {"index": 0}),
              ("message_delta", {"delta": {"stop_reason": "tool_use" if "tool" in reply else "end_turn", "stop_sequence": None},
                                 "usage": {"output_tokens": 10}}),
              ("message_stop", {})]
    return "".join(f"event: {name}\ndata: {json.dumps({'type': name, **data})}\n\n" for name, data in events).encode()


class StandIn:
    """Answers each request with the next reply, repeating the last. A reply is text, a tool call, a status or a hang."""

    def __init__(self, *replies, model=FREE):
        self.replies, self.model, self.requests = list(replies), model, []
        stand_in = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_HEAD(self):
                self.send_response(404)
                self.end_headers()

            do_GET = do_HEAD

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                stand_in.requests.append({"headers": {name.lower(): value for name, value in self.headers.items()}, "body": body})
                reply = stand_in.replies.pop(0) if len(stand_in.replies) > 1 else stand_in.replies[0]
                if "hang" in reply:
                    time.sleep(reply["hang"])
                    return
                if "status" in reply:
                    answer = json.dumps({"type": "error", "error": {"type": "rate_limit_error", "message": "busy"}}).encode()
                    self.send_response(reply["status"])
                    self.send_header("content-type", "application/json")
                    self.send_header("retry-after", "0")
                else:
                    answer = stream(reply, stand_in.model)
                    self.send_response(200)
                    self.send_header("content-type", "text/event-stream")
                self.send_header("content-length", str(len(answer)))
                self.end_headers()
                self.wfile.write(answer)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"


def config_for(url, **limits):
    return AgentConfig(model=FREE, base_url=url, limits=Limits(**{**LIMITS, **limits}), openrouter_key=KEY, database=SETTINGS)


@pytest.fixture
def agent(fake_store, fake_embedder, tmp_path):
    def run(*replies, model=FREE, **limits):
        stand_in = StandIn(*replies, model=model)
        home = tmp_path / "agent-home"
        home.mkdir(exist_ok=True)

        async def one():
            with bare_environment():
                return await triage_ticket(config_for(stand_in.url, **limits), fake_store, fake_embedder, "T00727", home)
        outcome = asyncio.run(one())
        stand_in.server.shutdown()
        outcome.requests = stand_in.requests
        return outcome
    return run


def sent(outcome):
    return json.dumps([request["body"] for request in outcome.requests])


def test_each_isolating_option_is_set_on_its_own(fake_store, fake_embedder, tmp_path):
    """The stand-in can't see these. Each sits behind another layer, so removing one alone changes no request."""
    lookups = TriageLookups(fake_store, fake_embedder, CASE)
    chosen = options(config_for("http://unused"), lookups, [], tmp_path)
    assert chosen.setting_sources == []
    assert chosen.permission_mode == "dontAsk"
    assert chosen.strict_mcp_config is True
    assert chosen.tools == []
    assert chosen.fallback_model is None
    assert chosen.cwd == str(tmp_path)
    assert set(chosen.allowed_tools) == DESK_TOOLS


def test_an_answer_becomes_a_result_on_the_free_model(agent):
    outcome = agent({"text": ANSWER})
    assert outcome.error is None
    assert outcome.result == {**FORM, "model": FREE, "dropped_ids": 0}
    assert outcome.models == {FREE}
    assert outcome.estimated_usd > 0  # The SDK prices a free model it does not know, which is why real spend is read too.


def test_every_request_goes_on_the_free_model_with_only_the_desk_s_tools(agent):
    outcome = agent(tool_call("mcp__desk__list_articles"), {"text": ANSWER})
    assert len(outcome.requests) == 2
    for request in outcome.requests:
        assert request["body"]["model"] == FREE
        assert {tool["name"] for tool in request["body"]["tools"]} == DESK_TOOLS


def test_the_key_goes_as_a_token_whatever_the_parent_has_set(agent, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-mine")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-mine")
    outcome = agent({"text": ANSWER})
    assert outcome.error is None
    headers = outcome.requests[0]["headers"]
    assert headers["authorization"] == f"Bearer {KEY}"
    assert "x-api-key" not in headers


def test_nothing_of_the_person_s_own_setup_reaches_the_model(agent, monkeypatch, tmp_path):
    mine = tmp_path / "my-home"
    (mine / ".claude").mkdir(parents=True)
    (mine / ".claude" / "CLAUDE.md").write_text("MY-OWN-RULES")
    (mine / ".claude" / "settings.json").write_text(json.dumps({"env": {"ANTHROPIC_MODEL": "claude-mine"}}))
    monkeypatch.setenv("HOME", str(mine))
    monkeypatch.chdir(mine)
    outcome = agent({"text": ANSWER})
    assert outcome.error is None
    assert "MY-OWN-RULES" not in sent(outcome)
    assert sorted(path.name for path in (mine / ".claude").iterdir()) == ["CLAUDE.md", "settings.json"]


def test_a_built_in_tool_the_model_asks_for_does_not_run(agent, tmp_path):
    planted = tmp_path / "ran"
    outcome = agent(tool_call("Bash", command=f"touch {planted}"), {"text": ANSWER})
    assert not planted.exists()
    assert outcome.tool_calls == 0


def test_the_note_tool_is_not_there_to_call(agent):
    outcome = agent(tool_call("mcp__desk__keep_note", text="Planted"), {"text": ANSWER})
    assert outcome.tool_calls == 0


def test_the_model_never_sees_the_ticket_s_own_labels(agent):
    outcome = agent(tool_call("mcp__desk__read_ticket", ticket_id="T00727"), {"text": ANSWER})
    assert outcome.tool_calls == 1
    text = sent(outcome)
    assert T00727["subject"] in text
    for held_back in ("Identity", "A03", "7.9600", "24.0000"):
        assert held_back not in text


def test_the_turn_limit_ends_the_ticket_with_no_result(agent):
    outcome = agent(tool_call("mcp__desk__list_articles"), max_turns=2)
    assert outcome.error == "turn_limit"
    assert outcome.result is None
    assert len(outcome.requests) == 2


def test_the_budget_limit_ends_the_ticket_with_no_result(agent):
    outcome = agent({**tool_call("mcp__desk__list_articles"), "input_tokens": 10_000_000}, estimated_usd_per_ticket=0.01)
    assert outcome.error == "budget_limit"
    assert outcome.result is None
    assert len(outcome.requests) == 1


def test_the_time_limit_ends_the_ticket_with_no_result(agent):
    started = time.monotonic()
    outcome = agent({"hang": 30}, seconds_per_ticket=2)
    assert outcome.error == "time_limit"
    assert outcome.result is None
    assert time.monotonic() - started < 20
    left = subprocess.run(["pgrep", "-P", str(os.getpid()), "-f", "claude"], capture_output=True, text=True).stdout
    assert left == ""  # A timed-out CLI must not go on working, or spending, behind the run.


def test_a_busy_model_is_named(agent):
    outcome = agent({"status": 429})
    assert outcome.error == "model_busy"
    assert outcome.result is None


def test_an_answer_outside_the_form_is_no_result(agent):
    outcome = agent({"text": json.dumps({**FORM, "priority": "urgent"})})
    assert outcome.error == "triage_invalid"
    assert outcome.result is None


def test_reasoning_before_the_form_is_left_out(agent):
    outcome = agent({"text": f"Based on my research, this is **account access**.\n\n{ANSWER}"})
    assert outcome.error is None
    assert outcome.result == {**FORM, "model": FREE, "dropped_ids": 0}


@pytest.mark.parametrize("text", ["No form here.", f"{ANSWER} And one more thing.", '{"category": "bug"}'])
def test_anything_else_around_the_form_is_still_no_result(agent, text):
    outcome = agent({"text": text})
    assert outcome.error == "triage_invalid"
    assert outcome.result is None


def test_an_id_no_tool_returned_is_taken_out(agent):
    outcome = agent({"text": json.dumps({**FORM, "record_ids": ["T99999"], "reason": "Same as C9999."})})
    assert outcome.result["record_ids"] == []
    assert outcome.result["reason"] == "Same as [ID removed]."
    assert outcome.result["dropped_ids"] == 2


def test_a_reply_from_another_model_voids_the_result(agent):
    outcome = agent({"text": ANSWER}, model="anthropic/claude-haiku")
    assert outcome.error == "wrong_model"
    assert outcome.result is None


def test_a_lookup_that_breaks_some_other_way_is_not_called_a_database_failure(agent, fake_store, monkeypatch):
    def broken():
        raise ValueError("a bad row")
    monkeypatch.setattr(fake_store, "articles", broken)
    outcome = agent(tool_call("mcp__desk__list_articles"), {"text": ANSWER})
    assert outcome.error == "lookup_failed"
    assert outcome.result is None


def test_a_database_failure_is_not_read_as_a_missing_record(agent, fake_store, monkeypatch):
    def down():
        raise psycopg.OperationalError("db.invalid")
    monkeypatch.setattr(fake_store, "articles", down)
    outcome = agent(tool_call("mcp__desk__list_articles"), {"text": ANSWER})
    assert outcome.error == "database_unavailable"
    assert outcome.result is None
    assert "db.invalid" not in sent(outcome)


ROWS = [{"ticket_id": f"T0000{n}", "subject": "S", "status": "open", "category": "bug", "priority": "P3", "team": "Technical support"}
        for n in range(1, 6)]
PROPOSED = {"category": "bug", "priority": "P3", "team": "Technical support", "reason": "R", "record_ids": [], "model": FREE,
            "dropped_ids": 0}


def good(ticket_id, cost=0.1):
    return Outcome(ticket_id, result=PROPOSED, turns=2, estimated_usd=cost, seconds=1.0)


def bad(ticket_id, error="model_unavailable"):
    return Outcome(ticket_id, error=error, seconds=1.0)


def work(tmp_path, triage, spent=lambda: 1.0, rows=ROWS, **limits):
    async def answer(ticket_id):
        return triage(ticket_id)
    review = ReviewList(tmp_path / "review.jsonl")
    tally = asyncio.run(work_through(config_for("http://unused", **limits), review, rows, "run1", answer, spent))
    return tally, review


def priced(monkeypatch, *prices):
    data = {"data": {"endpoints": [{"pricing": {"prompt": price, "completion": "0"}} for price in prices]}}
    monkeypatch.setattr(httpx, "get", lambda *_, **__: SimpleNamespace(raise_for_status=lambda: None, json=lambda: data))
    return config_for("http://unused")


def test_a_free_price_passes(monkeypatch):
    require_free_model(priced(monkeypatch, "0", "0"))


@pytest.mark.parametrize("prices", [("0", "0.000001"), ()])
def test_a_price_or_no_listing_stops_the_run_before_it_starts(monkeypatch, prices):
    with pytest.raises(SystemExit, match="free"):
        require_free_model(priced(monkeypatch, *prices))


def test_a_run_proposes_for_every_ticket_it_finishes(tmp_path):
    tally, review = work(tmp_path, good)
    assert tally["stopped_by"] is None
    assert tally["proposed"] == 5
    assert list(review.proposals()) == [row["ticket_id"] for row in ROWS]


def test_a_failed_ticket_gets_no_proposal_and_the_run_goes_on(tmp_path):
    tally, review = work(tmp_path, lambda ticket_id: bad(ticket_id) if ticket_id == "T00002" else good(ticket_id))
    assert tally["failed"] == {"model_unavailable": 1}
    assert "T00002" not in review.proposals()
    assert len(review.proposals()) == 4


def test_any_real_spend_stops_the_run(tmp_path):
    readings = iter([1.0, 1.0, 1.001, 1.001, 1.001, 1.001])
    tally, review = work(tmp_path, good, spent=lambda: next(readings))
    assert tally["stopped_by"] == "real_spend_limit"
    assert tally["tried"] == 2


def test_real_spend_that_can_t_be_read_stops_the_run(tmp_path):
    readings = iter([1.0])

    def spent():
        try:
            return next(readings)
        except StopIteration:
            raise httpx.ConnectError("down") from None
    tally, _ = work(tmp_path, good, spent=spent)
    assert tally["stopped_by"] == "real_spend_unknown"
    assert tally["tried"] == 1


def test_the_estimate_stops_the_run(tmp_path):
    tally, _ = work(tmp_path, good, estimated_usd_per_run=0.25)
    assert tally["stopped_by"] == "estimated_budget_limit"
    assert tally["tried"] == 3


def test_failures_in_a_row_stop_the_run(tmp_path):
    tally, _ = work(tmp_path, bad)
    assert tally["stopped_by"] == "failures_in_a_row"
    assert tally["tried"] == 3


def test_a_success_resets_failures_in_a_row(tmp_path):
    answers = iter([bad, bad, good, bad, bad])
    tally, _ = work(tmp_path, lambda ticket_id: next(answers)(ticket_id))
    assert tally["stopped_by"] is None
    assert tally["tried"] == 5


def test_a_busy_ticket_waits_and_gets_one_more_try(tmp_path):
    tries = []

    def triage(ticket_id):
        tries.append(ticket_id)
        return bad(ticket_id, "model_busy") if tries == ["T00001"] else good(ticket_id)
    tally, _ = work(tmp_path, triage, rows=ROWS[:1])
    assert tries == ["T00001", "T00001"]
    assert tally["proposed"] == 1


def test_another_model_stops_the_run_at_once(tmp_path):
    tally, review = work(tmp_path, lambda ticket_id: bad(ticket_id, "wrong_model"))
    assert tally["stopped_by"] == "wrong_model"
    assert tally["tried"] == 1
    assert review.proposals() == {}


@pytest.fixture(scope="module")
def reader():
    if not ENV_FILE.is_file():
        pytest.skip(".env.triage-agent is not set up")
    store = Store(load_config(TOML_FILE, ENV_FILE).database)
    store.open()
    yield store
    store.close()


@pytest.mark.live
def test_the_queue_is_every_unresolved_ticket_newest_first(reader):
    rows = queue_rows(reader)
    with reader.pool.connection() as db:
        unresolved = db.execute("SELECT COUNT(*) AS n FROM tickets WHERE status IS DISTINCT FROM 'resolved'").fetchone()["n"]
        newest = db.execute("""SELECT ticket_id FROM tickets WHERE status IS DISTINCT FROM 'resolved'
                               ORDER BY created_at DESC NULLS LAST, ticket_id LIMIT 1""").fetchone()["ticket_id"]
    assert len(rows) == unresolved
    assert rows[0]["ticket_id"] == newest
    assert {"resolved"}.isdisjoint(row["status"] for row in rows)
    assert set(rows[0]) == {"ticket_id", "subject", "status", "category", "priority", "team"}


@pytest.mark.live
def test_the_agent_s_login_can_only_read(reader):
    require_read_only(reader)


@pytest.mark.live
def test_the_model_is_free_on_openrouter_now():
    if not ENV_FILE.is_file():
        pytest.skip(".env.triage-agent is not set up")
    require_free_model(load_config(TOML_FILE, ENV_FILE))


@pytest.mark.live
def test_the_owner_login_is_refused():
    from orion_api.settings import load_settings
    try:
        settings = load_settings()
    except RuntimeError as reason:
        pytest.skip(str(reason))
    store = Store(settings)
    store.open()
    try:
        with pytest.raises(SystemExit, match="read-only login"):
            require_read_only(store)
    finally:
        store.close()


@pytest.mark.live
def test_the_fingerprint_is_stable(reader):
    assert fingerprint(reader) == fingerprint(reader)
    assert len(fingerprint(reader)) == 64
