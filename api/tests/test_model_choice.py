"""The allow-list and what happens when a model fails: the real SDK against a fake transport, so nothing leaves here.

The 400 and the 404 below are what OpenRouter answered for a broken ID and for a `:free` model that is gone.
"""
import asyncio
import json
from pathlib import Path
import re

import httpx2
import pytest

from orion_api import assistant
from orion_api.assistant import DEFAULT_MODEL, LOOKUP_SECONDS, LUNA, MODEL, MODEL_DEADLINE, MODELS, TRIAGE_ENFORCED
from orion_api.lookups import Lookups
from orion_api.models import TriageDecision
from orion_api.server_tools import ServerTools

from .conftest import AGENT, C0086, MESSAGES, T00727, FakeEmbedder, FakeStore, auth
from .test_ask import ASK, KEY, client_for, events, message_stream, offline, scripted, tool_turn

TRIAGE = "/api/tickets/T00727/triage"
ANSWER = ("text", "Yes.")
FORM = {"category": "bug", "priority": "P3", "team": "Technical support", "reason": "Why.", "record_ids": []}
PAID_FREE_MODEL = MODEL.removesuffix(":free")


def not_valid(request):
    return httpx2.Response(400, json={"type": "error", "error": {
        "type": "invalid_request_error", "message": f"{json.loads(request.content)['model']} is not a valid model ID",
        "error_type": "invalid_request"}})


def gone_for_free(request):
    return httpx2.Response(404, json={"type": "error", "error": {"type": "not_found_error", "error_type": "not_found",
        "message": f"This model is unavailable for free. The paid version is available now - use this slug instead: {PAID_FREE_MODEL}"}})


def counted(handler):
    def run(request):
        run.seen.append(json.loads(request.content))
        return handler(request)
    run.seen = []
    return run


class Stalled(httpx2.AsyncByteStream):
    """A model that says `first`, then nothing more, for as long as anyone waits."""

    def __init__(self, first=b""):
        self.first = first

    async def __aiter__(self):
        yield self.first
        await asyncio.Event().wait()


class KeptAlive(httpx2.AsyncByteStream):
    """Comment lines for ever, which reset a read limit and which the SDK passes on to nobody."""

    async def __aiter__(self):
        while True:
            yield b": OPENROUTER PROCESSING\n\n"
            await asyncio.sleep(0.01)


def stalls(stream):
    return counted(lambda request: httpx2.Response(200, headers={"content-type": "text/event-stream"}, stream=stream))


def get(handler, fake_store, fake_embedder, path):
    with client_for(offline(handler), fake_store, fake_embedder) as test_client:
        return test_client.get(path, headers=auth(AGENT))


@pytest.fixture
def short_deadline(monkeypatch):
    monkeypatch.setattr(assistant, "MODEL_DEADLINE", 0.2)


def test_the_allow_list_lists_every_line_with_the_default_first(client):
    response = client.get("/api/language-models/allow-list", headers=auth(AGENT))
    assert response.status_code == 200
    assert response.json() == {"total": 4, "items": [
        {"id": "free", "label": "Nemotron 3 Ultra", "provider": "OpenRouter", "model": MODEL, "paid": False, "run": True, "mail": False},
        {"id": "luna-high", "label": "GPT-6 Luna, high effort", "provider": "OpenRouter", "model": LUNA, "paid": True, "run": True, "mail": True},
        {"id": "anthropic", "label": "Claude Sonnet 5.5", "provider": "Anthropic", "model": "claude-sonnet-5-5", "paid": True, "run": False, "mail": False},
        {"id": "openai", "label": "GPT-6 Luna, direct", "provider": "OpenAI", "model": "gpt-6-luna", "paid": True, "run": False, "mail": False},
    ]}


def test_the_default_is_the_free_line_and_only_a_free_model_may_say_it_is_free():
    assert not MODELS[DEFAULT_MODEL].paid and next(iter(MODELS)) == DEFAULT_MODEL
    assert all(line.paid != line.model.endswith(":free") for line in MODELS.values())


def test_a_line_that_has_not_been_run_holds_nothing_to_call_it_with():
    for line in (MODELS["anthropic"], MODELS["openai"]):
        assert (line.ask, line.triage, line.run) == (None, None, False)
    assert all(line.provider == "OpenRouter" for line in MODELS.values() if line.run)


def test_no_key_is_read_for_a_provider_that_has_not_been_run():
    source = Path(assistant.__file__).read_text() + (Path(assistant.__file__).parent / "settings.py").read_text()
    assert "ANTHROPIC_API_KEY" not in source and "OPENAI_API_KEY" not in source
    assert source.count("base_url=BASE_URL") == 1  # One client, and it only ever goes to OpenRouter.


@pytest.mark.parametrize("path", [ASK, TRIAGE + "?"])
@pytest.mark.parametrize("line", ["anthropic", "openai"])
def test_a_line_not_run_is_refused_and_nothing_is_called(fake_store, fake_embedder, path, line):
    def handler(request):
        raise AssertionError("a Not run line must never reach a provider")

    response = get(handler, fake_store, fake_embedder, f"{path}&model={line}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "model_not_run"
    assert MODELS[line].label in response.json()["error"]["message"]


@pytest.mark.parametrize("path", [ASK, TRIAGE + "?"])
@pytest.mark.parametrize("name", [MODEL, LUNA, PAID_FREE_MODEL, "FREE", "free ", "claude-sonnet-5-5"])
def test_a_request_can_only_name_a_line_and_never_a_provider_s_model(fake_store, fake_embedder, path, name):
    def handler(request):
        raise AssertionError("a name off the list must never reach a provider")

    response = get(handler, fake_store, fake_embedder, f"{path}&model={name}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "model_not_allowed"


def test_a_model_name_past_the_limit_is_refused(client):
    assert client.get(f"{ASK}&model={'x' * 65}", headers=auth(AGENT)).json()["error"]["code"] == "invalid_request"


def test_a_token_comes_before_the_model_check(client):
    assert client.get(f"{ASK}&model=anthropic").status_code == 401


def test_with_no_model_named_the_free_model_answers(fake_store, fake_embedder):
    handler = scripted(message_stream(ANSWER))
    get(handler, fake_store, fake_embedder, ASK)
    assert handler.seen[0]["model"] == MODEL
    assert not {"output_config", "provider"} & set(handler.seen[0])


def test_luna_at_high_effort_answers_when_it_is_chosen(fake_store, fake_embedder):
    handler = scripted(tool_turn(("list_articles", {}), model=LUNA), message_stream(ANSWER, model=LUNA))
    assert events(get(handler, fake_store, fake_embedder, f"{ASK}&model=luna-high").text)[-1][0] == "done"
    assert [body["model"] for body in handler.seen] == [LUNA, LUNA]
    assert [body["output_config"] for body in handler.seen] == [{"effort": "high"}] * 2
    assert [body["provider"] for body in handler.seen] == [{"require_parameters": True}] * 2


def test_luna_triages_with_the_schema_when_it_is_chosen(fake_store, fake_embedder):
    handler = scripted(message_stream(("text", json.dumps(FORM)), model=LUNA))
    response = get(handler, fake_store, fake_embedder, f"{TRIAGE}?model=luna-high")
    assert response.json()["model"] == LUNA
    assert handler.seen[0]["output_config"]["format"]["schema"] == TriageDecision.model_json_schema()
    assert MODELS["luna-high"].triage is TRIAGE_ENFORCED


def test_a_broken_id_is_named_and_no_other_model_is_tried(fake_store, fake_embedder):
    handler = counted(not_valid)
    response = get(handler, fake_store, fake_embedder, ASK)
    [(name, data)] = events(response.text)
    assert name == "error"
    assert data["error"] == {"status": 502, "code": "model_not_found",
                             "message": f"OpenRouter does not offer {MODEL}. The desk did not switch to another model."}
    assert [body["model"] for body in handler.seen] == [MODEL]  # One call: a 400 is not retried, and nothing replaces it.


def test_any_other_400_is_not_called_a_missing_model(fake_store, fake_embedder):
    def handler(request):
        return httpx2.Response(400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "too long"}})

    assert events(get(handler, fake_store, fake_embedder, ASK).text)[0][1]["error"]["code"] == "model_unavailable"


def test_a_free_model_that_is_gone_never_takes_up_openrouter_s_paid_suggestion(fake_store, fake_embedder):
    handler = counted(gone_for_free)
    response = get(handler, fake_store, fake_embedder, ASK)
    assert events(response.text)[0][1]["error"]["code"] == "model_not_found"
    assert [body["model"] for body in handler.seen] == [MODEL]
    assert PAID_FREE_MODEL + " " not in response.text and "slug" not in response.text


def test_a_broken_id_is_a_502_from_triage_with_no_other_model_tried(fake_store, fake_embedder):
    handler = counted(not_valid)
    response = get(handler, fake_store, fake_embedder, TRIAGE)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "model_not_found"
    assert [body["model"] for body in handler.seen] == [MODEL]


@pytest.mark.parametrize("status, code", [(429, "model_busy"), (503, "model_unavailable")])
def test_a_retry_stays_on_the_same_model(fake_store, fake_embedder, status, code):
    handler = counted(lambda request: httpx2.Response(status, json={"type": "error", "error": {"type": "x", "message": "x"}}))
    assert events(get(handler, fake_store, fake_embedder, ASK).text)[0][1]["error"]["code"] == code
    assert [body["model"] for body in handler.seen] == [MODEL, MODEL]


def test_busy_names_the_model_and_does_not_assume_it_is_free(fake_store, fake_embedder):
    handler = lambda request: httpx2.Response(429, json={"type": "error", "error": {"type": "x", "message": "x"}})  # noqa: E731
    message = events(get(handler, fake_store, fake_embedder, f"{ASK}&model=luna-high").text)[0][1]["error"]["message"]
    assert message == f"{LUNA} is busy or rate limited. Try again in a minute."


def test_an_answer_from_a_model_nobody_asked_for_stops_before_any_text(fake_store, fake_embedder):
    handler = scripted(message_stream(ANSWER, model=PAID_FREE_MODEL))
    [(name, data)] = events(get(handler, fake_store, fake_embedder, ASK).text)
    assert name == "error"
    assert data["error"]["code"] == "wrong_model"
    assert len(handler.seen) == 1


def test_a_triage_from_a_model_nobody_asked_for_is_no_result(fake_store, fake_embedder):
    handler = scripted(message_stream(("text", json.dumps(FORM)), model=PAID_FREE_MODEL))
    response = get(handler, fake_store, fake_embedder, TRIAGE)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "wrong_model"


@pytest.mark.parametrize("stream", [Stalled(), KeptAlive()], ids=["silent", "keep-alive only"])
def test_a_stalled_model_ends_in_its_own_error(fake_store, fake_embedder, short_deadline, stream):
    handler = stalls(stream)
    [(name, data)] = events(get(handler, fake_store, fake_embedder, ASK).text)
    assert name == "error"
    assert data["error"] == {"status": 504, "code": "model_timeout", "message":
                             f"{MODEL} did not finish within 0 seconds. The desk stopped waiting and did not switch to another model."}
    assert [body["model"] for body in handler.seen] == [MODEL]


def test_text_already_written_stays_and_the_error_follows_it(fake_store, fake_embedder, short_deadline):
    start = message_stream(("text", "Half an")).content.split(b"event: content_block_stop")[0]
    found = events(get(stalls(Stalled(start)), fake_store, fake_embedder, ASK).text)
    assert [name for name, _ in found] == ["delta", "error"]
    assert found[-1][1]["error"]["code"] == "model_timeout"


def test_a_model_that_stalls_after_a_lookup_ends_in_the_same_error(fake_store, fake_embedder, short_deadline):
    turns = [tool_turn(("list_articles", {}))]

    def handler(request):
        if turns:
            return turns.pop()
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, stream=Stalled())

    found = events(get(handler, fake_store, fake_embedder, ASK).text)
    assert found[-1][1]["error"]["code"] == "model_timeout"


def test_a_stalled_triage_is_a_504_naming_the_model(fake_store, fake_embedder, short_deadline):
    response = get(stalls(Stalled()), fake_store, fake_embedder, f"{TRIAGE}?model=luna-high")
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "model_timeout"
    assert LUNA in response.json()["error"]["message"]


def test_a_stalled_answer_still_leaves_a_trace(fake_store, fake_embedder, short_deadline, capsys):
    start = message_stream(("text", "Half an")).content.split(b"event: content_block_stop")[0]
    get(stalls(Stalled(start)), fake_store, fake_embedder, ASK)
    assert "ask-trace ticket=T00727" in capsys.readouterr().out


def test_leaving_during_a_stall_ends_the_wait_with_no_error_event():
    async def leave():
        lookups = Lookups(FakeStore(), FakeEmbedder(), {"ticket": T00727, "customer": C0086, "messages": MESSAGES})
        start = message_stream(("text", "Yes")).content.split(b"event: content_block_stop")[0]
        answer = offline(stalls(Stalled(start))).answer("{}", "Why?", lookups, ServerTools())
        await anext(answer)
        await answer.aclose()
        return [item async for item in answer]

    assert asyncio.run(leave()) == []


def test_the_model_limit_comes_before_the_web_route_gives_up():
    source = (Path(__file__).parents[2] / "web" / "lib" / "api.ts").read_text()
    web_limit = int(re.search(r"ANSWER_LIMIT_MS = ([\d_]+)", source)[1].replace("_", "")) / 1000
    assert LOOKUP_SECONDS < MODEL_DEADLINE < web_limit
    assert web_limit - MODEL_DEADLINE >= 20  # Room for the case to load and the error to get back through the web server.
    assert assistant.ANSWER_TIMEOUT * 2 >= web_limit  # Why the read limit alone was not enough. Drop this if it changes.


def test_settings_checks_the_lines_that_have_run_and_never_the_others(fake_store, fake_embedder):
    asked = []

    def handler(request):
        asked.append(request.url.path)
        if request.url.path == "/api/v1/key":
            return httpx2.Response(200, json={"data": {"label": "desk"}})
        if MODEL in request.url.path:
            return httpx2.Response(404, json={"type": "error", "error": {"type": "not_found_error", "message": "gone"}})
        return httpx2.Response(200, json={"data": {"endpoints": [{"provider_name": "OpenAI"}]}})

    body = get(handler, fake_store, fake_embedder, "/api/language-models").json()
    assert body["connection"]["state"] == "model_unavailable"
    assert {option["id"]: option["state"] for option in body["options"]} == {
        "free": "model_unavailable", "luna-high": "connected", "anthropic": "not_run", "openai": "not_run"}
    assert not [path for path in asked if "claude" in path or path.endswith("/gpt-6-luna/endpoints") and "openai/" not in path]
    assert KEY not in json.dumps(body)
