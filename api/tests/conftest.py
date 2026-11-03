from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from orion_api.main import create_app
from orion_api.settings import Settings

AGENT = "agent-test-token"
ADMIN = "admin-test-token"
SETTINGS = Settings(pg_host="db.invalid", pg_port=5432, pg_user="nobody", pg_password="unused",
                    pg_database="orion_desk", agent_token=AGENT, admin_token=ADMIN)

# Rows shaped like orion_desk. IDs, dates and hours follow ADR 0001 checks 4, 5 and 7;
# the other values are placeholders.
T00727 = {
    "ticket_id": "T00727", "customer_id": "C0086", "agent_id": "A03",
    "created_at": datetime(2026, 6, 28, 3, 34), "first_response_at": datetime(2026, 6, 28, 11, 31, 36),
    "resolved_at": datetime(2026, 6, 29, 5, 8, 48), "category": "account access", "priority": "P2",
    "status": "resolved", "channel": "web", "component": "Identity", "subject": "Invite link expired",
    "body": "Body", "sla_response_hours": Decimal("3.0000"), "sla_resolution_hours": Decimal("24.0000"),
    "first_response_hours": Decimal("7.9600"), "resolution_hours": Decimal("25.5800"), "csat": None,
    "reopened_count": 0, "escalated": 0, "sentiment": "neutral", "plan_id": "growth",
    "industry": "SaaS", "region": "EMEA", "company_size": "51-200",
}
C0086 = {
    "customer_id": "C0086", "company": "Fern Platform 086", "industry": "SaaS", "country": "DE",
    "region": "EMEA", "company_size": "51-200", "plan_id": "growth", "seats": 12,
    "signup_date": date(2025, 1, 2), "contact_email": "contact086@example.com", "acquisition_source": None,
}
MESSAGES = [
    {"message_id": f"M00738{n}", "ticket_id": "T00727", "created_at": datetime(2026, 6, 28, n), "author_role": "customer", "body": "Hi"}
    for n in range(6, 11)
]


# Report rows shaped like the SQL output. Numbers are from orion_desk (first_reply's All row; B12 evidence).
FIRST_REPLY_ALL = {
    "priority": "All", "tickets": 4000, "met": 2451, "missed": 1525, "no_first_reply": 24, "no_target": 0,
    "avg_csat_met": Decimal("4.40"), "csat_met_counted": 1426, "csat_met_missing": 727,
    "avg_csat_missed": Decimal("2.90"), "csat_missed_counted": 903, "csat_missed_missing": 469,
}
# A group with nothing rated: the average is null, not 0 (M07).
FIRST_REPLY_UNRATED = {
    "priority": None, "tickets": 2, "met": 1, "missed": 0, "no_first_reply": 1, "no_target": 0,
    "avg_csat_met": None, "csat_met_counted": 0, "csat_met_missing": 1,
    "avg_csat_missed": None, "csat_missed_counted": 0, "csat_missed_missing": 0,
}
BACKLOG_ALL = {
    "status": "All", "tickets": 475, "no_first_reply": 24, "no_first_reply_past_target": 16,
    "oldest_created_at": datetime(2026, 1, 1, 1, 53), "avg_age_hours": Decimal("1953.37"),
    "age_counted": 475, "age_missing": 0,
}
REPORT_ROWS = {"first_reply": [FIRST_REPLY_UNRATED, FIRST_REPLY_ALL], "backlog": [BACKLOG_ALL]}


class FakeStore:
    database = "orion_desk"

    def __init__(self):
        self.calls = []

    def report(self, name):
        self.calls.append(("report", name))
        return REPORT_ROWS.get(name, [])

    def ticket_page(self, limit, offset):
        self.calls.append(("ticket_page", limit, offset))
        summary = {key: T00727[key] for key in ("ticket_id", "subject", "status", "priority", "channel",
                                               "category", "customer_id", "agent_id", "created_at")}
        return 4000, [summary] if offset < 4000 else []

    def ticket(self, ticket_id):
        if ticket_id != "T00727":
            return None
        return {"ticket": T00727, "customer": C0086, "messages": MESSAGES}

    def table_counts(self):
        return [{"table": "messages", "rows": 36694}, {"table": "tickets", "rows": 4000}]

    def exact_ticket(self, q):
        self.calls.append(("exact_ticket", q))
        if q != "T00727":
            return None
        return {"kind": "ticket", "id": "T00727", "title": T00727["subject"], "status": "resolved",
                "priority": "P2", "category": "account access", "similarity": None}

    def nearest(self, vector, priority, limit):
        self.calls.append(("nearest", vector, priority, limit))
        hits = [
            {"kind": "ticket", "id": "T00727", "title": T00727["subject"], "status": "resolved",
             "priority": "P2", "category": "account access", "similarity": 0.81},
            {"kind": "article", "id": "KB004", "title": "Resend an invitation", "status": None,
             "priority": None, "category": "account access", "similarity": 0.74},
        ]
        return [hit for hit in hits if priority in (None, hit["priority"])][:limit]


class FakeEmbedder:
    """Stands in for fastembed: no model download, a fixed 768-value vector."""

    def __init__(self):
        self.queries = []

    def query(self, text):
        self.queries.append(text)
        return [0.0] * 767 + [1.0]


@pytest.fixture
def fake_store():
    return FakeStore()


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def client(fake_store, fake_embedder):
    with TestClient(create_app(SETTINGS, fake_store, fake_embedder), raise_server_exceptions=False) as test_client:
        yield test_client


def auth(token):
    return {"Authorization": f"Bearer {token}"}
