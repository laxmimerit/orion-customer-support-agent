"""Triage: the real SDK against a fake transport, so nothing reaches OpenRouter. test_live.py runs it on the real store."""
import asyncio
import json

import pytest

from orion_api.assistant import MAX_TURNS, MODEL, TRIAGE_ENFORCED, TRIAGE_FREE, TRIAGE_LAST_TURN, case_text
from orion_api.lookups import BlindStore, TriageLookups, intake
from orion_api.main import ApiError, unless_gone
from orion_api.models import REASON_LIMIT, Triage, TriageDecision

from .conftest import AGENT, C0086, MESSAGES, T00727, auth, private_keys
from .test_ask import KEY, api_error, client_for, message_stream, offline, scripted, tool_turn

ROUTE = "/api/tickets/T00727/triage"
CASE = {"ticket": T00727, "customer": C0086,
        "messages": [{**MESSAGES[0], "body": "Customer words"}, {**MESSAGES[1], "author_role": "agent", "body": "Agent words"}]}
FORM = {"category": "account access", "priority": "P2", "team": "Customer care", "reason": "Invitation trouble.",
        "record_ids": []}


def answer(**changes):
    return message_stream(("text", json.dumps({**FORM, **changes})))


@pytest.fixture
def triage(fake_store, fake_embedder):
    def run(*turns):
        handler = scripted(*turns)
        with client_for(offline(handler), fake_store, fake_embedder) as test_client:
            response = test_client.get(ROUTE, headers=auth(AGENT))
        response.seen = handler.seen
        return response
    return run


@pytest.fixture
def lookups(fake_store, fake_embedder):
    return TriageLookups(fake_store, fake_embedder, CASE)


def read(lookups, tool, **arguments):
    text, failed = lookups.run(tool, arguments)
    assert not failed
    return text


def test_the_route_returns_exactly_the_form(client):
    response = client.get(ROUTE, headers=auth(AGENT))
    assert response.status_code == 200
    assert response.json() == {"category": "account access", "priority": "P2", "team": "Customer care",
                               "reason": "Invitation trouble.", "record_ids": ["KB004"], "model": "test/model",
                               "dropped_ids": 1}
    assert private_keys(response.json()) == set()


@pytest.mark.parametrize("ticket_id", ["T99999", "t00727"])
def test_an_unknown_or_wrong_case_id_is_a_404(client, ticket_id):
    response = client.get(f"/api/tickets/{ticket_id}/triage", headers=auth(AGENT))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ticket_not_found"


def test_an_id_past_the_limit_is_refused(client):
    assert client.get(f"/api/tickets/{'T' * 33}/triage", headers=auth(AGENT)).status_code == 422
    assert client.get(f"/api/tickets/{'T' * 32}/triage", headers=auth(AGENT)).status_code == 404


def test_no_key_is_a_503(fake_store, fake_embedder):
    with client_for(offline(scripted(), key=None), fake_store, fake_embedder) as test_client:
        response = test_client.get(ROUTE, headers=auth(AGENT))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_not_configured"


def test_the_model_never_sees_the_ticket_s_own_labels(triage):
    prompt = triage(answer()).seen[0]["messages"][0]["content"]
    held_back = {"category": "account access", "priority": "P2", "component": "Identity", "agent_id": "A03",
                 "sla_response_hours": "3.0000", "sla_resolution_hours": "24.0000", "status": "resolved",
                 "first_response_hours": "7.9600", "resolution_hours": "25.5800", "sentiment": "neutral"}
    for value in held_back.values():
        assert f'"{value}"' not in prompt
    case = json.loads(prompt.removeprefix("<case>").split("</case>")[0])
    assert {name: case["ticket"][name] for name in held_back} == dict.fromkeys(held_back)
    assert (case["ticket"]["ticket_id"], case["ticket"]["subject"]) == ("T00727", "Invite link expired")


def test_intake_keeps_the_customer_s_messages_and_no_reply():
    case = json.loads(case_text(intake(CASE)))
    assert [message["body"] for message in case["messages"]] == ["Customer words"]


@pytest.mark.parametrize("query", ["invite link", "T00727"])
def test_a_search_cannot_find_the_open_ticket(lookups, query):
    hits = json.loads(read(lookups, "search_records", query=query))["items"]
    assert [hit["id"] for hit in hits] == ["KB004"]
    assert "T00727" not in lookups.seen


def test_reading_the_open_ticket_gives_the_held_back_case(lookups):
    case = json.loads(read(lookups, "read_ticket", ticket_id="T00727"))
    assert case["ticket"]["category"] is None and case["ticket"]["priority"] is None
    assert case["ticket"]["agent_id"] is None and case["ticket"]["component"] is None
    assert [message["body"] for message in case["messages"]] == ["Hi"] * 5
    assert "T00727" in lookups.seen  # A tool returned it, so the model may cite it.


def test_the_customer_s_history_leaves_the_open_ticket_out(lookups):
    history = json.loads(read(lookups, "read_customer", customer_id="C0086"))["support_history"]
    assert [ticket["ticket_id"] for ticket in history["items"]] == ["T00001"]
    assert history["total"] == 1


def test_an_article_s_related_tickets_leave_the_open_ticket_out(lookups):
    related = json.loads(read(lookups, "read_article", article_id="KB022"))["related_tickets"]
    assert related == {"total": 110, "items": []}


def test_the_customer_list_counts_leave_the_open_ticket_out(lookups):
    rows = json.loads(read(lookups, "find_customers", name="Fern"))["items"]
    assert (rows[0]["all_cases"], rows[0]["active_cases"]) == (17, 4)  # 18 and 4 stored. T00727 is resolved.


def test_an_unresolved_open_ticket_comes_off_the_active_count_too(fake_store, monkeypatch):
    unresolved = {"ticket": {**T00727, "status": "open"}, "customer": C0086, "messages": []}
    monkeypatch.setattr(fake_store, "ticket", lambda ticket_id: unresolved)
    row = BlindStore(fake_store, "T00727").customers()[0]
    assert (row["all_cases"], row["active_cases"]) == (17, 3)


def test_other_customers_keep_their_counts(fake_store):
    assert BlindStore(fake_store, "T00727").customers()[1]["all_cases"] == 0


def test_a_store_method_nobody_thought_through_is_not_forwarded(fake_store):
    with pytest.raises(AttributeError):
        BlindStore(fake_store, "T00727").similar_tickets("T00727")


def test_another_ticket_stays_whole(fake_store):
    store = BlindStore(fake_store, "T00001")
    assert store.ticket("T00727")["ticket"]["category"] == "account access"


def test_no_note_is_offered_or_kept(lookups):
    assert "keep_note" not in {schema["name"] for schema in lookups.schemas}
    assert lookups.run("keep_note", {"text": "x"}) == ("No tool has that name.", True)
    assert lookups.kept is None


def test_an_id_no_tool_returned_is_dropped(triage):
    response = triage(tool_turn(("search_records", {"query": "invite"})),
                      answer(record_ids=["KB004", "T99999", "KB004", "C0086", "T00727"]))
    assert response.status_code == 200
    # KB004 came back from the search. T99999 never existed, and the open case and its customer were not looked up.
    assert response.json()["record_ids"] == ["KB004"]
    assert response.json()["dropped_ids"] == 3


def test_with_no_lookup_every_id_is_dropped(triage):
    response = triage(answer(record_ids=["T00001"]))
    assert (response.json()["record_ids"], response.json()["dropped_ids"]) == ([], 1)


def test_an_id_no_tool_returned_is_taken_out_of_the_reason(triage):
    body = triage(tool_turn(("search_records", {"query": "invite"})),
                  answer(reason="Like KB004 and T99999, on T00727 for C0086.")).json()
    assert body["reason"] == "Like KB004 and [ID removed], on T00727 for C0086."
    assert body["dropped_ids"] == 1


@pytest.mark.parametrize("written", ["t00500", "T-00500", "T 00500", "T_00500", "c-0500", "kb-099", "KB 099", "A03", "DOC001"])
def test_an_id_written_another_way_is_taken_out_of_the_reason(triage, written):
    body = triage(answer(reason=f"As in {written}, again.")).json()
    assert (body["reason"], body["dropped_ids"]) == ("As in [ID removed], again.", 1)


@pytest.mark.parametrize("reason", ["The 12 seats are blocked for 30 days at P1.", "Plan with 18 seats since 2026."])
def test_plain_numbers_stay_in_the_reason(triage, reason):
    body = triage(answer(reason=reason)).json()
    assert (body["reason"], body["dropped_ids"]) == (reason, 0)


def test_a_full_reason_with_ids_taken_out_stays_a_result(triage):
    reason = ("T99999 " * 3 + "x" * REASON_LIMIT)[:REASON_LIMIT]
    response = triage(answer(reason=reason))
    assert response.status_code == 200
    assert len(response.json()["reason"]) == REASON_LIMIT


def test_one_id_in_both_places_counts_once(triage):
    body = triage(answer(reason="Like T99999.", record_ids=["T99999"])).json()
    assert (body["reason"], body["record_ids"], body["dropped_ids"]) == ("Like [ID removed].", [], 1)


@pytest.mark.parametrize("changes", [{"category": "billing "}, {"priority": "P5"}, {"priority": "p2"},
                                     {"team": "Engineering"}, {"reason": ""}, {"reason": "x" * 301},
                                     {"record_ids": "KB004"}, {"record_ids": ["K"] * 21}, {"extra": 1}])
def test_an_answer_outside_the_form_is_not_a_result(triage, changes):
    response = triage(answer(**changes))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "triage_invalid"


@pytest.mark.parametrize("text", ["It looks like billing.", "[]", '{"category": "billing"}', "<tool_call>x</tool_call>"])
def test_text_that_is_not_the_form_is_not_a_result(triage, text):
    response = triage(message_stream(("text", text)))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "triage_invalid"


def test_a_code_fence_around_the_form_is_accepted(triage):
    response = triage(message_stream(("text", f"```json\n{json.dumps(FORM)}\n```")))
    assert response.status_code == 200


def test_no_text_is_model_empty(triage):
    response = triage(message_stream(("thinking", "Hmm"), stop_reason="max_tokens"))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "model_empty"


def test_a_cut_off_answer_is_not_a_result(triage):
    response = triage(message_stream(("text", '{"category": "bil'), stop_reason="max_tokens"))
    assert response.json()["error"]["code"] == "triage_invalid"


def test_a_refused_call_keeps_its_status_and_hides_the_provider_s_words(triage):
    response = triage(api_error(429, "rate_limit_error"), api_error(429, "rate_limit_error"))
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "model_busy"
    assert KEY not in response.text


def test_the_last_turn_must_answer(triage):
    turns = [tool_turn(("list_articles", {})) for _ in range(MAX_TURNS - 1)]
    seen = triage(*turns, answer()).seen
    assert len(seen) == MAX_TURNS
    assert seen[-1]["tool_choice"] == {"type": "none"}
    assert seen[-1]["messages"][-1]["content"][-1] == {"type": "text", "text": TRIAGE_LAST_TURN}


def test_a_client_that_leaves_cancels_the_work():
    class Gone:
        async def is_disconnected(self):
            return True

    async def run():
        cancelled = asyncio.Event()

        async def work():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled.set()
                raise
        with pytest.raises(ApiError):
            await unless_gone(Gone(), work())
        await asyncio.wait_for(cancelled.wait(), 1)
    asyncio.run(run())


def test_the_desk_uses_the_free_model_and_sends_no_enforcement(triage):
    body = triage(answer()).seen[0]
    assert body["model"] == MODEL
    assert not {"output_config", "response_format", "provider"} & set(body)
    assert body["tools"] and "keep_note" not in {tool["name"] for tool in body["tools"]}


def test_the_enforced_model_sends_the_schema_and_high_effort(lookups):
    handler = scripted(message_stream(("text", json.dumps(FORM)), model=TRIAGE_ENFORCED.model))
    result = asyncio.run(offline(handler).triage("{}", lookups, TRIAGE_ENFORCED))
    body = handler.seen[0]
    assert body["model"] == "openai/gpt-6-luna" == result["model"]
    assert body["output_config"] == {"effort": "high", "format": {"type": "json_schema",
                                                                 "schema": TriageDecision.model_json_schema()}}
    assert body["provider"] == {"require_parameters": True}
    assert "response_format" not in body  # OpenRouter drops it on this route, with no error.


def test_the_schema_holds_every_field_and_closes_the_form():
    schema = TriageDecision.model_json_schema()
    assert set(schema["required"]) == {"category", "priority", "team", "reason", "record_ids"}
    assert schema["additionalProperties"] is False
    assert schema["properties"]["priority"]["enum"] == ["P1", "P2", "P3", "P4"]
    assert set(Triage.model_fields) == {*schema["required"], "model", "dropped_ids"}
    assert TRIAGE_FREE.options == {}
