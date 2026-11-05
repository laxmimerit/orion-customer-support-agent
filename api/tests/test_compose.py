"""Compose, Approve, Send and the Action history, offline, with one short test per route."""
from datetime import datetime
import json

from fastapi.testclient import TestClient
import pytest

from orion_api.assistant import ModelFailed, checked_draft
from orion_api.mail import MailProblem
from orion_api.mail_sender import MailSender, desk_address
from orion_api.main import create_app
from orion_api.settings import Settings

from .conftest import AGENT, KB022_DETAIL, SETTINGS, FakeAssistant, FakeEmbedder, FakeStore, auth

FORM = {"mail_id": "ML1", "template": "Answer", "tone": "Warm", "language": "Spanish"}
DRAFT = {"recipient": "desk+fern@test.example", "subject": "Re: Slow [T00727]", "body": "Hola", "in_reply_to": "<one@test>",
         "references": "<one@test>", "article_id": "KB022"}


def action(name, actor="Clara", details=None):
    return {"draft_id": "DR1", "action": name, "ticket_id": "T00727", "actor": actor, "details": details,
            "acted_at": datetime(2026, 11, 5, 10)}


class Desk(FakeStore):
    rows = None

    def thread_mail(self, ticket_id, mail_id):
        if (ticket_id, mail_id) == ("T00727", "ML1"):
            return {"rfc_message_id": "<one@test>", "replies_to": "", "sender_name": "Fern", "subject": "Re: Slow", "body": "Hi"}

    def approvers(self):
        return ["Clara"]

    def article(self, article_id):
        return KB022_DETAIL

    def ticket_actions(self, ticket_id):
        return list((self.rows or {}).values()) if ticket_id == "T00727" else None

    def draft_actions(self, draft_id):
        return self.rows if draft_id == "DR1" else None


class Model(FakeAssistant):
    answer_with = {"article_id": "KB022", "reply": "Hola", "english": "Hello"}

    async def compose(self, case, mail, template, tone, language, lookups):
        if self.answer_with is None:
            raise ModelFailed({"status": 422, "code": "insufficient_evidence", "message": "No article."})
        return self.answer_with


class Box:
    address = "desk+fern@test.example"

    def reply_address(self, rfc_message_id):
        return self.address


class Sender:
    sent = None
    problem = None

    def allowed(self, address):
        return desk_address(address, "desk@test.example")

    def send(self, draft):
        if self.problem:
            raise MailProblem(self.problem)
        self.sent = draft
        return "<sent@test>"


class Writer:
    configured = True

    def __init__(self, store):
        self.store, self.added = store, []

    def add_action(self, row):
        self.added.append(row["action"])
        rows = self.store.rows = self.store.rows or {}
        if row["action"] in rows:
            return False
        rows[row["action"]] = {**row, "acted_at": datetime(2026, 11, 5, 10)}
        return True


@pytest.fixture
def desk():
    store = Desk()
    model, box, writer, sender = Model(), Box(), Writer(store), Sender()
    with TestClient(create_app(SETTINGS, store, FakeEmbedder(), model, box, writer, sender)) as client:
        client.store, client.model, client.box, client.writer, client.sender = store, model, box, writer, sender
        client.headers.update(auth(AGENT))
        yield client


def drafted(store, *names):
    store.rows = {"drafted": action("drafted", "GPT-6 Luna", json.dumps(DRAFT))}
    store.rows.update({name: action(name) for name in names})


def test_compose_stores_a_cited_draft_and_refuses_without_evidence_or_a_desk_address(desk):
    answer = desk.post("/api/tickets/T00727/drafts", json=FORM).json()
    cited = "\n\nHelp article: KB022 · Role change not applied"
    assert answer == {"draft_id": answer["draft_id"], "status": "drafted", "recipient": "desk+fern@test.example",
                      "subject": "Re: Slow [T00727]", "body": "Hola" + cited, "english": "Hello" + cited, "language": "Spanish",
                      "article_id": "KB022", "article_title": "Role change not applied", "approvers": ["Clara"]}
    desk.writer.added.clear()
    desk.model.answer_with = None
    assert desk.post("/api/tickets/T00727/drafts", json=FORM).json()["error"]["code"] == "insufficient_evidence"
    desk.box.address = "someone@else.example"
    assert desk.post("/api/tickets/T00727/drafts", json=FORM).json()["error"]["code"] == "recipient_not_allowed"
    assert desk.writer.added == []


def test_approve_needs_a_known_name_and_happens_once(desk):
    drafted(desk.store)
    assert desk.post("/api/drafts/DR1/approve", json={"approved_by": "Nobody"}).json()["error"]["code"] == "unknown_approver"
    assert desk.post("/api/drafts/DR1/approve", json={"approved_by": "Clara"}).json() == {
        "draft_id": "DR1", "status": "approved", "approved_by": "Clara"}
    assert desk.post("/api/drafts/DR1/approve", json={"approved_by": "Clara"}).status_code == 409


def test_send_needs_approval_goes_once_and_logs_a_failure(desk):
    drafted(desk.store)
    assert desk.post("/api/drafts/DR1/send").json()["error"]["code"] == "not_approved"
    drafted(desk.store, "approved")
    assert desk.post("/api/drafts/DR1/send").json()["status"] == "sent"
    assert desk.sender.sent == DRAFT
    assert desk.post("/api/drafts/DR1/send").json()["error"]["code"] == "already_sent"
    drafted(desk.store, "approved")
    desk.sender.problem = "unavailable"
    assert desk.post("/api/drafts/DR1/send").status_code == 503
    assert "failed" in desk.store.rows


def test_action_history_names_who_did_what(desk):
    drafted(desk.store, "approved")
    answer = desk.get("/api/tickets/T00727/actions").json()
    assert answer["total"] == 2 and answer["items"][1] == {
        "draft_id": "DR1", "action": "approved", "actor": "Clara", "acted_at": "2026-11-05T10:00:00Z",
        "recipient": "desk+fern@test.example", "subject": "Re: Slow [T00727]", "article_id": "KB022"}
    assert desk.get("/api/tickets/T99999/actions").status_code == 404


@pytest.mark.parametrize("address, allowed", [("desk@test.example", True), ("DESK+a.b@test.example", True),
                                              ("desk+a@other.example", False), ("desk2@test.example", False),
                                              ("x@y, desk@test.example", False), ("", False), (None, False)])
def test_only_the_desk_and_its_plus_forms_pass(address, allowed):
    assert desk_address(address, "desk@test.example") is allowed


def test_the_sender_replies_in_thread_and_refuses_any_other_address_itself():
    class Smtp:
        auth_plain = None

        def ehlo_or_helo_if_needed(self):
            pass

        def auth(self, *args):
            pass

        def quit(self):
            pass

        def send_message(self, message, from_addr, to_addrs):
            self.message, self.to = message, to_addrs

    smtp = Smtp()
    settings = Settings(**{**SETTINGS.__dict__, "mail_user": "desk@test.example", "mail_app_password": "x"})
    sender = MailSender(settings, open_smtp=lambda: smtp)
    with pytest.raises(MailProblem):
        sender.send({**DRAFT, "recipient": "someone@else.example"})
    sender.send(DRAFT)
    assert smtp.to == ["desk+fern@test.example"]
    assert (smtp.message["In-Reply-To"], smtp.message["References"]) == ("<one@test>", "<one@test>")


def test_only_an_article_the_model_read_counts_as_evidence():
    class Read:
        read = {"KB022"}

    text = json.dumps({"article_id": "KB004", "reply": "Hi", "english": "Hi"})
    with pytest.raises(ModelFailed) as refused:
        checked_draft(text, Read(), "luna")
    assert refused.value.body["code"] == "insufficient_evidence"
