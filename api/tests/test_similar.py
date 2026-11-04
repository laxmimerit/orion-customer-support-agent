"""/api/tickets/{ticket_id}/similar against a fake store, and the helpers that build its answer."""
import pytest

from orion_api.embedding import DIMENSIONS
from orion_api.store import SIMILAR_TICKETS, reply_summary, shared_fields, similar_result

from .conftest import AGENT, auth

ARTICLES = [{"article_id": "KB004", "title": "Invite link expired", "category": "account access"},
            {"article_id": "KB034", "title": "Invite link expired", "category": "account access"}]
REPLIES = {"distinct_replies": 1, "top_reply": "Reply", "top_reply_tickets": 1, "tickets_without_reply": 1}
SOURCE = {"subject": "Invite link expired", "component": "Identity", "priority": "P2", "plan_id": "scale",
          "channel": "web", "vector": "[0]"}


def similar(client, path="T00727", query=""):
    return client.get(f"/api/tickets/{path}/similar{query}", headers=auth(AGENT))


def ticket(ticket_id, **values):
    return {"ticket_id": ticket_id, **{name: SOURCE[name] for name in ("subject", "component")},
            "priority": "P3", "plan_id": "growth", "channel": "chat", **values}


def message(ticket_id, role, body):
    return {"ticket_id": ticket_id, "author_role": role, "body": body}


def test_similar_tickets_keep_only_the_model_fields_and_nulls_stay_null(client):
    response = similar(client)
    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "items": [
            {"ticket_id": "T02576", "priority": "P2", "similarity": 0.99, "resolution_hours": "9.9100",
             "sla_resolution_hours": "24.0000", "first_response_hours": "2.3400", "csat": None, "reopened_count": 0,
             "escalated": 0, "message_count": 10, "agent_id": "A01", "plan_id": "scale", "channel": "chat",
             "last_author_role": "agent", "last_body": "Reply",
             "matched_on": ["subject", "component", "priority", "plan_id"]},
            {"ticket_id": "T00002", "priority": None, "similarity": 0.91, "resolution_hours": None,
             "sla_resolution_hours": None, "first_response_hours": None, "csat": None, "reopened_count": None,
             "escalated": None, "message_count": 0, "agent_id": None, "plan_id": None, "channel": None,
             "last_author_role": None, "last_body": None, "matched_on": []},
        ],
        "matched_on": [],
        "replies": REPLIES,
        "articles": ARTICLES,
        "articles_read_same": True,
    }


def test_limit_caps_the_items_but_not_the_total(client):
    body = similar(client, query="?limit=1").json()
    assert (body["total"], [item["ticket_id"] for item in body["items"]]) == (2, ["T02576"])
    assert body["replies"] == REPLIES


def test_a_ticket_with_nothing_close_has_an_empty_answer(client):
    assert similar(client, "T00201").json() == {
        "total": 0, "items": [], "matched_on": [], "articles": [], "articles_read_same": False,
        "replies": {"distinct_replies": 0, "top_reply": None, "top_reply_tickets": 0, "tickets_without_reply": 0}}


@pytest.mark.parametrize("ticket_id", ["T99999", "t00727", "T00727%20", "X" * 32])
def test_an_unknown_or_inexact_id_is_404(client, ticket_id):
    response = similar(client, ticket_id)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ticket_not_found"


@pytest.mark.parametrize("path, query", [("X" * 33, ""), ("T00727", "?limit=0"), ("T00727", "?limit=51"),
                                         ("T00727", "?limit=many")])
def test_bad_similar_requests_are_422(client, path, query):
    response = similar(client, path, query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_a_field_missing_from_both_tickets_is_not_a_match():
    source = {**SOURCE, "subject": None, "channel": None}
    assert shared_fields(source, {**source, "plan_id": "growth"}) == ["component", "priority"]


def test_the_most_used_reply_counts_each_ticket_once():
    messages = [message("T1", "agent", "Common"), message("T1", "agent", "Common"), message("T2", "agent", "Common"),
                message("T3", "agent", "Rare"), message("T3", "customer", "Most words"), message("T4", "agent", None)]
    assert reply_summary(["T1", "T2", "T3", "T4"], messages) == {
        "distinct_replies": 2, "top_reply": "Common", "top_reply_tickets": 2, "tickets_without_reply": 1}


def test_tied_replies_are_settled_by_their_text():
    messages = [message("T1", "agent", "Beta"), message("T2", "agent", "Alpha")]
    assert reply_summary(["T1", "T2"], messages)["top_reply"] == "Alpha"


def test_no_replies_are_counted_as_missing_not_zero_tickets_answered():
    assert reply_summary(["T1"], []) == {"distinct_replies": 0, "top_reply": None, "top_reply_tickets": 0,
                                         "tickets_without_reply": 1}


def test_each_ticket_gets_its_own_reason_and_last_message():
    tickets = [ticket("T1", priority="P2"), ticket("T2", channel="web"), ticket("T3")]
    messages = [message("T1", "customer", "First"), message("T1", "agent", "Last"), message("T2", "customer", "Only")]
    result = similar_result(SOURCE, tickets, messages, [])
    first, second, third = result["items"]
    assert (first["matched_on"], first["message_count"], first["last_author_role"], first["last_body"]) == (
        ["subject", "component", "priority"], 2, "agent", "Last")
    assert second["matched_on"] == ["subject", "component", "channel"]
    assert (third["message_count"], third["last_author_role"], third["last_body"]) == (0, None, None)
    assert result["matched_on"] == ["subject", "component"]  # only what all three share
    assert result["total"] == 3


def test_articles_read_the_same_only_when_two_or_more_have_one_text():
    same, other = {"article_id": "KB1", "body": "Text"}, {"article_id": "KB2", "body": "Other"}
    assert similar_result(SOURCE, [], [], [same, {**same, "article_id": "KB3"}])["articles_read_same"] is True
    assert similar_result(SOURCE, [], [], [same, other])["articles_read_same"] is False
    assert similar_result(SOURCE, [], [], [same])["articles_read_same"] is False


def test_nothing_found_shares_no_fields():
    assert similar_result(SOURCE, [], [], [])["matched_on"] == []


def test_similar_query_keeps_the_hnsw_shape():
    assert f"ORDER BY embedding <=> %(vector)s::vector({DIMENSIONS})\n    LIMIT %(limit)s" in SIMILAR_TICKETS
    assert "WHERE" not in SIMILAR_TICKETS.split("LIMIT")[0]
