"""Plan increment 2's check against the real orion_desk (read-only). Skipped without PG_* settings."""
from fastapi.testclient import TestClient
import pytest

from orion_api.main import create_app
from orion_api.settings import load_settings

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
    assert {row["table"]: row["rows"] for row in body["tables"]} == ADR_COUNTS


def test_sessions_are_read_only(live):
    client, _ = live
    with client.app.state.store.pool.connection() as db:
        assert db.execute("SHOW transaction_read_only").fetchone()["transaction_read_only"] == "on"
