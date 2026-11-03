"""API behaviour against a fake store: no network, no database."""
import pytest

from orion_api.main import create_app
from orion_api.settings import load_settings

from .conftest import ADMIN, AGENT, SETTINGS, auth


def test_every_route_is_under_api_apart_from_docs(client):
    docs = {"/", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
    paths = {route.path for route in client.app.routes} - docs
    assert paths == {"/api/tickets", "/api/tickets/{ticket_id}", "/api/search", "/api/admin/status"}


def test_every_route_is_get_only(client):
    methods = {method for route in client.app.routes if route.path.startswith("/api") for method in route.methods}
    assert methods <= {"GET", "HEAD"}
    response = client.post("/api/tickets", headers=auth(AGENT))
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_root_opens_the_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize("path", ["/api/tickets", "/api/tickets/T00727", "/api/search?q=T00727", "/api/admin/status"])
def test_a_token_is_required(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"error": {"status": 401, "code": "missing_token",
                                         "message": "Send Authorization: Bearer <token>."}}


def test_a_wrong_token_is_refused(client):
    response = client.get("/api/tickets", headers=auth("not-a-token"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_basic_auth_is_not_a_token(client):
    response = client.get("/api/tickets", headers={"Authorization": "Basic " + AGENT})
    assert response.status_code == 401


def test_ticket_list_is_paged(client, fake_store):
    response = client.get("/api/tickets?page=3&page_size=10", headers=auth(AGENT))
    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["page_size"], body["total"]) == (3, 10, 4000)
    assert body["items"][0]["ticket_id"] == "T00727"
    assert "body" not in body["items"][0]
    assert fake_store.calls == [("ticket_page", 10, 20)]


def test_ticket_list_defaults(client, fake_store):
    body = client.get("/api/tickets", headers=auth(AGENT)).json()
    assert (body["page"], body["page_size"]) == (1, 25)
    assert fake_store.calls == [("ticket_page", 25, 0)]


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101", "page=abc"])
def test_bad_paging_is_a_json_error(client, query):
    response = client.get("/api/tickets?" + query, headers=auth(AGENT))
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert error["details"][0]["field"].startswith("query.")


def test_ticket_with_customer_and_messages_oldest_first(client):
    response = client.get("/api/tickets/T00727", headers=auth(AGENT))
    assert response.status_code == 200
    body = response.json()
    assert body["ticket"]["ticket_id"] == "T00727"
    assert body["ticket"]["agent_id"] == "A03"
    assert body["customer"]["customer_id"] == "C0086"
    assert [m["message_id"] for m in body["messages"]] == [f"M00738{n}" for n in range(6, 11)]


def test_values_keep_utc_precision_and_nulls(client):
    ticket = client.get("/api/tickets/T00727", headers=auth(AGENT)).json()["ticket"]
    assert ticket["created_at"] == "2026-06-28T03:34:00Z"
    assert ticket["first_response_at"] == "2026-06-28T11:31:36Z"
    assert ticket["first_response_hours"] == "7.9600"
    assert ticket["sla_response_hours"] == "3.0000"
    assert ticket["csat"] is None  # not recorded stays null, never 0 (M07)
    assert ticket["escalated"] == 0


@pytest.mark.parametrize("ticket_id", ["T99999", "t00727", "T00727 "])
def test_unknown_or_inexact_id_is_404(client, ticket_id):
    response = client.get(f"/api/tickets/{ticket_id}", headers=auth(AGENT))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ticket_not_found"


def test_admin_token_reads_tickets_too(client):
    assert client.get("/api/tickets/T00727", headers=auth(ADMIN)).status_code == 200


def test_agent_token_cannot_open_admin_status(client):
    response = client.get("/api/admin/status", headers=auth(AGENT))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "admin_only"


def test_admin_status_counts_each_table(client):
    response = client.get("/api/admin/status", headers=auth(ADMIN))
    assert response.status_code == 200
    assert response.json() == {"database": "orion_desk", "tables": [
        {"table": "messages", "rows": 36694}, {"table": "tickets", "rows": 4000}]}


def test_unknown_route_is_a_json_404(client):
    response = client.get("/api/nothing", headers=auth(AGENT))
    assert response.status_code == 404
    assert response.json() == {"error": {"status": 404, "code": "not_found", "message": "Not Found."}}


def test_server_errors_are_json_and_hide_details(client, fake_store):
    def broken(*args):
        raise RuntimeError("password=secret host=db.example")
    fake_store.ticket = broken
    response = client.get("/api/tickets/T00727", headers=auth(AGENT))
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret" not in response.text


def test_database_outage_is_503(client, fake_store):
    from psycopg_pool import PoolTimeout

    def down(*args):
        raise PoolTimeout("couldn't get a connection to db.example")
    fake_store.ticket_page = down
    response = client.get("/api/tickets", headers=auth(AGENT))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert "db.example" not in response.text


def test_settings_read_tokens_and_ignore_legacy_database(tmp_path, monkeypatch):
    for key in ("PG_HOST", "PG_USER", "PG_PASSWORD", "PG_DATABASE", "PG_PORT", "ORION_AGENT_TOKEN", "ORION_ADMIN_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text("TIDB_HOST=legacy\nPG_HOST=h\nPG_USER=u\nPG_PASSWORD=p\nPG_DATABASE=orion_desk\n"
                   "ORION_AGENT_TOKEN='agent'\nORION_ADMIN_TOKEN=\"admin\"\n")
    settings = load_settings(env)
    assert (settings.agent_token, settings.admin_token, settings.pg_port) == ("agent", "admin", 5432)
    assert not hasattr(settings, "tidb_host")
    assert "admin" not in repr(settings)


def test_settings_refuse_missing_or_shared_tokens(tmp_path, monkeypatch):
    for key in ("ORION_AGENT_TOKEN", "ORION_ADMIN_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text("PG_HOST=h\nPG_USER=u\nPG_PASSWORD=p\nPG_DATABASE=d\nORION_AGENT_TOKEN=same\n")
    with pytest.raises(RuntimeError, match="ORION_ADMIN_TOKEN"):
        load_settings(env)
    env.write_text(env.read_text() + "ORION_ADMIN_TOKEN=same\n")
    with pytest.raises(RuntimeError, match="must differ"):
        load_settings(env)


def test_openapi_documents_bearer_auth(client):
    schema = client.get("/openapi.json").json()
    assert "HTTPBearer" in schema["components"]["securitySchemes"]
    assert create_app(SETTINGS).title == "Orion desk API"
