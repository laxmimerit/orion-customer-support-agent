"""Plan increment 2's check against the real orion_desk (read-only). Skipped without PG_* settings."""
from fastapi.testclient import TestClient
import pytest

from orion_api.main import create_app
from orion_api.settings import load_settings

from orion_api.embedding import MODEL, as_vector
from orion_api.store import nearest_query

from .conftest import auth

pytestmark = pytest.mark.live

# ADR 0001, check 2: the new-database column.
ADR_COUNTS = {
    "plans": 3, "agents": 9, "customers": 300, "subscriptions": 300, "tickets": 4000,
    "messages": 36694, "invoices": 1800, "ticket_events": 7525, "releases": 12, "incidents": 1,
    "sla_policy": 12, "knowledge_articles": 40, "company_documents": 5, "staff_requests": 4,
    "lab_metadata": 1,
}


@pytest.fixture(scope="module")
def live():
    try:
        settings = load_settings()
    except RuntimeError as reason:
        pytest.skip(str(reason))
    with TestClient(create_app(settings)) as client:
        yield client, settings


def test_t00727_with_customer_agent_and_messages_in_order(live):
    client, settings = live
    response = client.get("/api/tickets/T00727", headers=auth(settings.agent_token))
    assert response.status_code == 200
    body = response.json()
    ticket = body["ticket"]
    assert (ticket["ticket_id"], ticket["customer_id"], ticket["agent_id"]) == ("T00727", "C0086", "A03")
    assert (ticket["created_at"], ticket["first_response_at"], ticket["resolved_at"]) == (
        "2026-06-28T03:34:00Z", "2026-06-28T11:31:36Z", "2026-06-29T05:08:48Z")
    assert (ticket["first_response_hours"], ticket["resolution_hours"]) == ("7.9600", "25.5800")
    assert body["customer"]["company"] == "Fern Platform 086"
    assert [m["message_id"] for m in body["messages"]] == ["M007386", "M007387", "M007388", "M007389", "M007390"]


def test_exact_id_only(live):
    client, settings = live
    assert client.get("/api/tickets/t00727", headers=auth(settings.agent_token)).status_code == 404


def test_first_page_is_newest_first(live):
    client, settings = live
    body = client.get("/api/tickets?page_size=50", headers=auth(settings.agent_token)).json()
    assert body["total"] == 4000 and len(body["items"]) == 50
    keys = [(item["created_at"], item["ticket_id"]) for item in body["items"]]
    assert [k[0] for k in keys] == sorted((k[0] for k in keys), reverse=True)


def test_admin_status_matches_adr_counts(live):
    client, settings = live
    assert client.get("/api/admin/status", headers=auth(settings.agent_token)).status_code == 403
    body = client.get("/api/admin/status", headers=auth(settings.admin_token)).json()
    assert body["database"] == settings.pg_database
    # The 15 migrated tables, plus increment 8's search_embeddings (one row per ticket and article).
    assert {row["table"]: row["rows"] for row in body["tables"]} == {**ADR_COUNTS, "search_embeddings": 4040}


def test_sessions_are_read_only(live):
    client, _ = live
    with client.app.state.store.pool.connection() as db:
        assert db.execute("SHOW transaction_read_only").fetchone()["transaction_read_only"] == "on"


# Plan increment 8: search. These load the local embedding model (cached after the first run).

def test_search_exact_id_returns_only_that_ticket(live):
    client, settings = live
    body = client.get("/api/search?q=T00727", headers=auth(settings.agent_token)).json()
    assert body["match"] == "exact_id"
    assert [(item["kind"], item["id"]) for item in body["items"]] == [("ticket", "T00727")]


def test_search_finds_other_wording(live):
    # B04: "invitation" finds the tickets the legacy "invite" search finds, T00727 among them.
    client, settings = live
    body = client.get("/api/search?q=invitation", headers=auth(settings.agent_token)).json()
    assert body["match"] == "semantic" and len(body["items"]) == 10
    assert "T00727" in [item["id"] for item in body["items"]]


def test_search_priority_filter_returns_only_those_tickets(live):
    client, settings = live
    body = client.get("/api/search?q=invitation%20link%20expired&priority=P1",
                      headers=auth(settings.agent_token)).json()
    assert len(body["items"]) == 10
    assert {(item["kind"], item["priority"]) for item in body["items"]} == {("ticket", "P1")}


def test_every_ticket_and_article_is_embedded_with_one_model(live):
    client, _ = live
    with client.app.state.store.pool.connection() as db:
        rows = db.execute("SELECT kind, COUNT(*) AS n FROM search_embeddings GROUP BY kind").fetchall()
        assert {row["kind"]: row["n"] for row in rows} == {"ticket": 4000, "article": 40}
        assert db.execute("SELECT array_agg(DISTINCT model) AS m FROM search_embeddings").fetchone()["m"] == [MODEL]
        indexes = {r["indexname"]: r["indexdef"] for r in db.execute(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'search_embeddings'").fetchall()}
        assert "USING hnsw (embedding vector_cosine_ops)" in indexes["search_embeddings_hnsw"]


def test_search_plans_use_hnsw_unfiltered_and_the_priority_index_filtered(live):
    client, _ = live
    vector = as_vector(client.app.state.embedder.query("invitation link expired"))
    with client.app.state.store.pool.connection() as db:
        def plan(priority):
            rows = db.execute("EXPLAIN " + nearest_query(priority),
                              {"vector": vector, "priority": priority, "limit": 10}).fetchall()
            return "\n".join(row["QUERY PLAN"] for row in rows)
        assert "HNSW Scan using search_embeddings_hnsw" in plan(None)
        assert "Index Scan using search_embeddings_priority" in plan("P1")
