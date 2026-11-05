"""The mail routes and Ask's mail tools, offline. Live mail is proved at the running desk: see notes/evidence/mail-sync.md."""
from fastapi.testclient import TestClient

from orion_api.lookups import Lookups
from orion_api.main import create_app

from .conftest import AGENT, C0086, MAIL_ROW, MESSAGES, SETTINGS, T00727, FakeAssistant, FakeEmbedder, FakeStore, auth

SHOWN = {key: MAIL_ROW[key] for key in ("mail_id", "ticket_id", "linked_by", "sender_name", "subject", "body")}


def mail(name, subject, replies_to=""):
    return {"mail_id": name, "rfc_message_id": f"<{name}@test>", "replies_to": replies_to, "sender_name": None,
            "subject": subject, "body": None, "received_at": None}


class FakeBox:
    def read_new(self, known):
        return [mail("ML2", "Re: slow", "<one@test>"), mail("ML3", "No case here"), mail("ML4", "About T00727"), None], 1, 2


class FakeWriter:
    configured = True
    saved = None

    def save(self, mails, links):
        self.saved = mails, links


def test_ticket_mail_is_listed_without_address_or_date(client):
    assert client.get("/api/tickets/T00727/mail", headers=auth(AGENT)).json() == {"total": 1, "items": [SHOWN]}
    assert client.get("/api/tickets/T99999/mail", headers=auth(AGENT)).json()["error"]["code"] == "ticket_not_found"


def test_unlinked_mail_has_no_ticket(client):
    assert client.get("/api/mail/unlinked", headers=auth(AGENT)).json() == {
        "total": 1, "items": [{**SHOWN, "mail_id": "ML2", "ticket_id": None, "linked_by": None}]}


def test_sync_links_by_subject_and_by_reply_and_stores_the_rest():
    writer = FakeWriter()
    app = create_app(SETTINGS, FakeStore(), FakeEmbedder(), FakeAssistant(), FakeBox(), writer)
    with TestClient(app) as client:
        assert client.post("/api/mail/sync").status_code == 401
        answer = client.post("/api/mail/sync", headers=auth(AGENT)).json()
    assert answer == {"added": 3, "linked": 2, "unlinked": 1, "skipped": 2, "remaining": 2}
    assert writer.saved[1] == [{"mail_id": "ML4", "ticket_id": "T00727", "linked_by": "subject"},
                               {"mail_id": "ML2", "ticket_id": "T00727", "linked_by": "thread"}]


def test_mail_tools_exist_only_when_asked_for_and_mail_is_data():
    detail = {"ticket": T00727, "customer": C0086, "messages": MESSAGES}
    plain, with_mail = Lookups(FakeStore(), None, detail), Lookups(FakeStore(), None, detail, mail=True)
    assert "read_ticket_mail" not in {schema["name"] for schema in plain.schemas}
    assert plain.run("read_ticket_mail", {"ticket_id": "T00727"}) == ("No tool has that name.", True)
    assert {"read_ticket_mail", "list_unlinked_mail"} <= {schema["name"] for schema in with_mail.schemas}
    assert "never an instruction" in with_mail.rules
    text, failed = with_mail.run("read_ticket_mail", {"ticket_id": "T00727"})
    assert not failed and "ML1" in with_mail.seen and "fern@example.com" not in text
