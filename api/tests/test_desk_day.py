"""Triage and match on unlinked mail, the hand link, follow-ups, notes and the daily summary, offline."""
from datetime import datetime
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from orion_api.assistant import MODELS
from orion_api.main import create_app

from .conftest import AGENT, SETTINGS, FakeAssistant, FakeEmbedder, FakeStore, auth
from .test_compose import FORM, Box, Desk, Model, Sender, Writer

MAIL = {"mail_id": "ML9", "ticket_id": None, "linked_by": None, "sender_name": "Fern", "subject": "Slow", "body": "Help"}
SECRET = "Refund is off the table"
LATE = {"ticket_id": "T00727", "subject": "Slow", "status": "open", "priority": "high", "company": "Acme", "approver": "Clara",
        "customer_id": "C0086", "late_reply": True, "late_resolution": True, "age_hours": Decimal("90.5000"),
        "first_response_hours": None, "sla_response_hours": Decimal("3.00"), "sla_resolution_hours": Decimal("24.00")}


class Day(Desk):
    notes = ()

    def mail(self, mail_id):
        return MAIL if mail_id == "ML9" else None

    def existing_tickets(self, ticket_ids):
        return set(ticket_ids) & {"T00727"}

    def nearest(self, vector, priority, limit):
        return [{"kind": "article", "id": "KB022", "title": "Guide", "status": None, "similarity": 0.9},
                {"kind": "ticket", "id": "T00001", "title": "Old", "status": "resolved", "similarity": 0.8},
                {"kind": "ticket", "id": "T00727", "title": "Slow", "status": "open", "similarity": 0.7}]

    def late_cases(self, limit):
        return 7, [LATE]

    def case_notes(self, ticket_id):
        return list(self.notes) if ticket_id == "T00727" else None


class DayWriter(Writer):
    links = ()

    def add_link(self, mail_id, ticket_id):
        fresh = mail_id not in self.links
        self.links = (*self.links, mail_id)
        return fresh

    def add_note(self, row):
        self.store.notes = (*self.store.notes, {**row, "noted_at": datetime(2026, 11, 5, 10)})
        return datetime(2026, 11, 5, 10)


class DayModel(Model):
    seen = None

    async def triage(self, case, lookups, choice=None, **form):
        self.seen = case, choice
        return {"category": "bug", "priority": "P2", "team": "Technical support", "reason": "Slow.", "record_ids": [],
                "model": "luna", "dropped_ids": 0}

    async def compose(self, case, mail, template, tone, language, lookups):
        self.seen = case, mail
        return await super().compose(case, mail, template, tone, language, lookups)


@pytest.fixture
def desk():
    store = Day()
    model, writer = DayModel(), DayWriter(store)
    with TestClient(create_app(SETTINGS, store, FakeEmbedder(), model, Box(), writer, Sender())) as client:
        client.store, client.model, client.writer = store, model, writer
        client.headers.update(auth(AGENT))
        yield client


def test_mail_triage_always_runs_on_the_mail_line(desk):
    assert desk.get("/api/mail/ML9/triage").json()["team"] == "Technical support"
    case, choice = desk.model.seen
    assert "Help" in case and choice == MODELS["luna-high"].triage and MODELS["luna-high"].mail
    assert desk.get("/api/mail/ML0/triage").json()["error"]["code"] == "mail_not_found"


def test_match_is_the_nearest_active_ticket(desk):
    assert desk.get("/api/mail/ML9/match").json() == {
        "match": {"ticket_id": "T00727", "subject": "Slow", "status": "open", "similarity": 0.7}}


def test_a_mail_links_by_hand_once(desk):
    assert desk.post("/api/mail/ML9/link", json={"ticket_id": "T99999"}).json()["error"]["code"] == "ticket_not_found"
    assert desk.post("/api/mail/ML9/link", json={"ticket_id": "T00727"}).json() == {
        **MAIL, "ticket_id": "T00727", "linked_by": "manual"}
    assert desk.post("/api/mail/ML9/link", json={"ticket_id": "T00727"}).json()["error"]["code"] == "mail_already_linked"


def test_follow_ups_carry_an_unsent_draft_from_the_ticket(desk):
    answer = desk.get("/api/follow-ups").json()
    assert answer["total"] == 7
    draft = answer["items"][0]["draft"]
    assert draft.startswith("DRAFT. NOT SENT. Awaiting approval by: Clara")
    assert "Subject: Re: T00727, Slow" in draft and "No first response is recorded yet, against our 3 hour target." in draft


def test_notes_list_and_handoff(desk):
    note = {"author": "Clara", "body": " Over to you ", "handed_to": "Clara"}
    assert desk.post("/api/tickets/T00727/notes", json=note).json()["error"]["code"] == "same_agent"
    assert desk.post("/api/tickets/T00727/notes", json={**note, "handed_to": "Nobody"}).json()["error"]["code"] == "unknown_agent"
    assert desk.post("/api/tickets/T00727/notes", json={**note, "body": "  ", "handed_to": None}).status_code == 422
    assert desk.post("/api/tickets/T99999/notes", json={**note, "handed_to": None}).status_code == 404
    assert desk.post("/api/tickets/T00727/notes", json={**note, "handed_to": None}).json()["body"] == "Over to you"
    listed = desk.get("/api/tickets/T00727/notes").json()
    assert (listed["total"], listed["agents"]) == (1, ["Clara"])
    assert desk.get("/api/tickets/T99999/notes").status_code == 404


def test_a_note_never_reaches_a_draft(desk):
    desk.post("/api/tickets/T00727/notes", json={"author": "Clara", "body": SECRET})
    answer = desk.post("/api/tickets/T00727/drafts", json=FORM)
    assert answer.status_code == 200 and SECRET not in answer.text
    assert SECRET not in str(desk.model.seen)


def test_daily_summary_has_one_line_for_each_count():
    spec = spec_from_file_location("daily_summary", Path(__file__).parents[2] / "tools" / "daily_summary.py")
    tool = module_from_spec(spec)
    spec.loader.exec_module(tool)
    counts = {"mail": 6, "drafts": 2, "sends": 1, "failed": 0, "late": 430, "handoffs": 3}
    assert tool.summary("2026-11-05", counts).splitlines()[1:] == [
        "Mail: 6 received", "Drafts: 2", "Sends: 1 sent, 0 failed", "Late cases: 430 now", "Handoffs: 3"]
