"""Plan increment 2's check against the real orion_desk (read-only). Skipped without PG_* settings."""
from fastapi.testclient import TestClient
import pytest

from orion_api.main import REPORT_ROUTES, create_app
from orion_api.settings import load_settings

from orion_api.embedding import MODEL, as_vector
from orion_api.models import CustomerListItem, CustomerSubscription, CustomerTicket, StaffRequest
from orion_api.store import (CUSTOMER_LIST, CUSTOMER_SUBSCRIPTION, CUSTOMER_TICKETS, REPORTS, STAFF_REQUESTS,
                             nearest_query)

from .conftest import auth, private_keys

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


# Customers, knowledge and company pages.

def page(client, settings, path):
    response = client.get(path, headers=auth(settings.agent_token))
    assert response.status_code == 200
    body = response.json()
    assert private_keys(body) == set()
    return body


def test_hand_written_queries_return_exactly_their_model_columns(live):
    client, _ = live
    with client.app.state.store.pool.connection() as db:
        for query, params, model in ((CUSTOMER_LIST, (), CustomerListItem),
                                     (CUSTOMER_SUBSCRIPTION, ("C0086",), CustomerSubscription),
                                     (CUSTOMER_TICKETS, ("C0086",), CustomerTicket),
                                     (STAFF_REQUESTS, (), StaffRequest)):
            cursor = db.execute(query, params)
            assert [column.name for column in cursor.description] == list(model.model_fields)


def test_customer_list_counts_every_ticket_once(live):
    client, settings = live
    body = page(client, settings, "/api/customers")
    assert body["total"] == len(body["items"]) == 300
    assert sum(item["all_cases"] for item in body["items"]) == 4000
    assert sum(item["active_cases"] for item in body["items"]) == 475  # the backlog report's total
    keys = [(item["company"], item["customer_id"]) for item in body["items"]]
    assert keys == sorted(keys)
    fern = next(item for item in body["items"] if item["customer_id"] == "C0086")
    assert (fern["company"], fern["active_cases"], fern["all_cases"]) == ("Fern Platform 086", 4, 18)
    assert fern["plan"] is not None


def test_customer_profile_tickets_are_newest_first(live):
    client, settings = live
    body = page(client, settings, "/api/customers/C0086")
    assert body["company"] == "Fern Platform 086"
    assert body["subscription"]["plan"] is not None
    history = body["support_history"]
    assert history["total"] == len(history["items"]) == 18
    assert all(item["assigned_to"] and item["team"] for item in history["items"])
    ids = [item["ticket_id"] for item in history["items"]]
    with client.app.state.store.pool.connection() as db:
        created = {row["ticket_id"]: row["created_at"] for row in db.execute(
            "SELECT ticket_id, created_at FROM tickets WHERE ticket_id = ANY(%s)", (ids,)).fetchall()}
        totals = db.execute("SELECT total_usd FROM invoices WHERE customer_id = 'C0086' ORDER BY month").fetchall()
    assert [created[ticket_id] for ticket_id in ids] == sorted(created.values(), reverse=True)
    assert [invoice["total_usd"] for invoice in body["invoice_history"]] == [str(row["total_usd"]) for row in totals]
    assert client.get("/api/customers/c0086", headers=auth(settings.agent_token)).status_code == 404


def test_knowledge_list_is_by_id(live):
    client, settings = live
    body = page(client, settings, "/api/knowledge")
    assert body["total"] == len(body["items"]) == 40
    ids = [item["article_id"] for item in body["items"]]
    assert ids == sorted(ids)


def test_article_has_its_tickets_and_the_rest_of_its_category(live):
    client, settings = live
    body = page(client, settings, "/api/knowledge/KB022")
    assert (body["title"], body["category"]) == ("Role change not applied", "account access")
    assert body["body"]
    related = body["related_tickets"]
    assert related["total"] == 111 and len(related["items"]) == 5
    resolved = [item["status"] == "resolved" for item in related["items"]]
    assert resolved == sorted(resolved)  # unresolved first
    others = [item["article_id"] for item in body["more_in_category"]]
    assert others == sorted(others) and "KB022" not in others
    assert {item["category"] for item in body["more_in_category"]} == {"account access"}


def test_ticket_articles_match_the_subject_exactly(live):
    client, settings = live
    # Two articles share T00727's subject, and nothing records which applies (backlog B03): both are listed.
    assert page(client, settings, "/api/tickets/T00727/knowledge") == {"total": 2, "items": [
        {"article_id": "KB004", "title": "Invite link expired", "category": "account access"},
        {"article_id": "KB034", "title": "Invite link expired", "category": "account access"},
    ]}
    with client.app.state.store.pool.connection() as db:
        one_match = db.execute("SELECT MIN(ticket_id) AS id FROM tickets WHERE subject = 'Role change not applied'"
                               ).fetchone()["id"]
    assert [item["article_id"] for item in page(client, settings, f"/api/tickets/{one_match}/knowledge")["items"]] == ["KB022"]
    # T00201 is "CSV download ends early": no article has that title.
    assert page(client, settings, "/api/tickets/T00201/knowledge") == {"total": 0, "items": []}
    assert client.get("/api/tickets/t00727/knowledge", headers=auth(settings.agent_token)).status_code == 404


def test_company_splits_owners_and_keeps_every_row(live):
    client, settings = live
    body = page(client, settings, "/api/company")
    assert [row["document_id"] for row in body["sections"]] == [f"DOC00{n}" for n in range(1, 6)]
    assert [row["request_id"] for row in body["staff_requests"]] == [f"REQ00{n}" for n in range(1, 5)]
    assert (body["sections"][0]["owner"], body["sections"][0]["team"]) == ("Maya", "Product")
    assert all(row["requested_by"] for row in body["staff_requests"])


# Reports (api/reports). Expected numbers are from the B12 evidence file and investigation.md.

def report(client, settings, path):
    response = client.get(f"/api/reports/{path}", headers=auth(settings.agent_token))
    assert response.status_code == 200
    return response.json()["rows"]


def test_each_report_returns_exactly_its_model_columns(live):
    client, _ = live
    with client.app.state.store.pool.connection() as db:
        for _, name, row, _ in REPORT_ROUTES:
            cursor = db.execute(REPORTS[name])
            assert [column.name for column in cursor.description] == list(row.model_fields), name


def test_every_average_counts_what_it_leaves_out(live):
    client, settings = live
    averages = {"priority": ("first_response", "resolution"), "category": ("first_response", "resolution"),
                "backlog": ("age",)}
    for path, names in averages.items():
        for row in report(client, settings, path):
            for name in names:
                assert row[f"{name}_counted"] + row[f"{name}_missing"] == row["tickets"], (path, name, row)
    # Unresolved tickets can't be rated yet, so satisfaction counts resolved tickets only.
    for path in ("priority", "category"):
        for row in report(client, settings, path):
            assert row["csat_counted"] + row["csat_missing"] == row["resolved"], (path, row)
        assert report(client, settings, path)[-1]["csat_missing"] == 1196, path
    for row in report(client, settings, "first-reply"):
        assert row["met"] + row["missed"] + row["no_first_reply"] + row["no_target"] == row["tickets"]
        # Unresolved tickets can't be rated yet, so they are neither counted nor missing.
        assert row["csat_met_counted"] + row["csat_met_missing"] <= row["met"]
        assert row["csat_missed_counted"] + row["csat_missed_missing"] <= row["missed"]


def test_totals_match_the_ticket_table(live):
    client, settings = live
    for path in ("volume", "priority", "category"):
        rows = report(client, settings, path)
        total, groups = rows[-1], rows[:-1]
        assert (total["tickets"], total["resolved"], total["unresolved"], total["status_missing"]) == (4000, 3525, 475, 0)
        assert sum(row["tickets"] for row in groups) == 4000, path
    assert [row["month"] for row in report(client, settings, "volume")] == [
        "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "All"]
    backlog = report(client, settings, "backlog")[-1]
    assert (backlog["status"], backlog["tickets"], backlog["no_first_reply"]) == ("All", 475, 24)


def test_first_reply_report_matches_the_b12_evidence(live):
    client, settings = live
    rows = {row["priority"]: row for row in report(client, settings, "first-reply")}
    evidence = {  # priority: rated met n, avg, rated missed n, avg
        "P1": (140, "4.09", 73, "2.68"), "P2": (320, "4.28", 213, "2.85"), "P3": (703, "4.46", 447, "2.97"),
        "P4": (263, "4.52", 170, "2.90"), "All": (1426, "4.40", 903, "2.90"),
    }
    resolved_unrated = {"P1": 107, "P2": 297, "P3": 586, "P4": 206, "All": 1196}
    for priority, expected in evidence.items():
        row = rows[priority]
        assert (row["csat_met_counted"], row["avg_csat_met"], row["csat_missed_counted"], row["avg_csat_missed"]) == expected
        assert row["csat_met_missing"] + row["csat_missed_missing"] == resolved_unrated[priority]
    assert (rows["All"]["csat_met_missing"], rows["All"]["csat_missed_missing"]) == (727, 469)
    assert (rows["All"]["no_first_reply"], rows["All"]["no_target"]) == (24, 0)


def test_b12_headline_rated_and_unrated(live):
    # B12 evidence: met 1,426 at 4.40, missed 903 at 2.90; 2,329 rated of 3,525 resolved; 1,196 resolved unrated.
    client, settings = live
    first_reply = report(client, settings, "first-reply")[-1]
    resolved = report(client, settings, "priority")[-1]["resolved"]
    assert (first_reply["csat_met_counted"], first_reply["avg_csat_met"]) == (1426, "4.40")
    assert (first_reply["csat_missed_counted"], first_reply["avg_csat_missed"]) == (903, "2.90")
    rated = first_reply["csat_met_counted"] + first_reply["csat_missed_counted"]
    unrated = first_reply["csat_met_missing"] + first_reply["csat_missed_missing"]
    assert (rated, resolved, unrated) == (2329, 3525, 1196)
    assert rated + unrated == resolved


def test_category_report_matches_the_design_stat_strip(live):
    # DESIGN.md: 526 account access tickets; 17.65 h average first reply; 522 with a first reply; 4 with none.
    client, settings = live
    row = next(row for row in report(client, settings, "category") if row["category"] == "account access")
    assert (row["tickets"], row["avg_first_response_hours"], row["first_response_counted"],
            row["first_response_missing"]) == (526, "17.65", 522, 4)
