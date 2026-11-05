"""/api/mcp: who it opens for, what it answers, and that it only ever reads."""
import dataclasses
import json

from fastapi.testclient import TestClient
import pytest

from orion_api.main import MCP_BODY_LIMIT, create_app
from orion_api.settings import load_settings

from .conftest import ADMIN, AGENT, SETTINGS, auth

PATH = "/api/mcp"
TOKEN = "mcp-test-token"
LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


def call(ticket_id="T00727", name="read_ticket", request_id=2):
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": name, "arguments": {"ticket_id": ticket_id}}}


@pytest.fixture
def mcp(fake_store, fake_embedder, fake_assistant):
    app = create_app(dataclasses.replace(SETTINGS, mcp_token=TOKEN), fake_store, fake_embedder, fake_assistant)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def post(client, message, token=TOKEN):
    return client.post(PATH, json=message, headers=auth(token))


def test_no_token_is_refused_and_reads_nothing(mcp, fake_store):
    fake_store.ticket = lambda *_: pytest.fail("the store was read without a token")
    response = mcp.post(PATH, json=call())
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"error": {"status": 401, "code": "missing_token",
                                         "message": "Send Authorization: Bearer <token>."}}


@pytest.mark.parametrize("token", ["not-a-token", AGENT, ADMIN])
def test_only_the_mcp_token_opens_it(mcp, token):
    response = post(mcp, call(), token)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_the_mcp_token_opens_no_other_route(mcp):
    assert mcp.get("/api/tickets/T00727", headers=auth(TOKEN)).status_code == 401
    assert mcp.get("/api/admin/status", headers=auth(TOKEN)).status_code == 401


def test_with_no_token_configured_nothing_opens_it(client):
    for headers in ({}, auth(""), auth("None"), auth(AGENT), auth(ADMIN)):
        assert client.post(PATH, json=call(), headers=headers).status_code == 401


def test_a_bad_body_with_no_token_says_nothing_about_the_body(mcp):
    response = mcp.post(PATH, content=b"{not json", headers={"content-type": "application/json"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_token"


def test_it_says_hello_in_the_client_s_version(mcp):
    message = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}
    response = post(mcp, message)
    assert response.status_code == 200
    assert response.json() == {"jsonrpc": "2.0", "id": 0, "result": {
        "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
        "serverInfo": {"name": "orion-desk", "version": "0.1.0"}}}


def test_a_version_it_does_not_know_gets_its_newest(mcp):
    message = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}}
    assert post(mcp, message).json()["result"]["protocolVersion"] == "2025-11-25"


def test_a_notification_gets_an_empty_202(mcp):
    response = post(mcp, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert response.status_code == 202
    assert response.content == b""


def test_the_one_tool_on_offer_says_it_only_reads(mcp):
    tools = post(mcp, LIST).json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["read_ticket"]
    assert tools[0]["annotations"]["readOnlyHint"] is True


def test_a_ticket_comes_back_as_the_desk_s_model_sees_it(mcp):
    body = post(mcp, call()).json()
    assert body["id"] == 2
    assert body["result"]["isError"] is False
    case = json.loads(body["result"]["content"][0]["text"])
    assert case["ticket"]["ticket_id"] == "T00727"
    assert case["ticket"]["customer_id"] == "C0086"
    assert case["customer"]["company"] == "Fern Platform 086"
    assert case["messages"][0] == {"author_role": "customer", "body": "Hi"}


def test_no_email_or_date_comes_back(mcp):
    text = post(mcp, call()).json()["result"]["content"][0]["text"]
    assert "@" not in text
    assert "contact_email" not in text
    assert "created_at" not in text
    assert "2026-06-28" not in text


@pytest.mark.parametrize("ticket_id", ["T99999", "t00727", "T00727 "])
def test_an_unknown_id_is_a_tool_error_and_not_a_ticket(mcp, ticket_id):
    result = post(mcp, call(ticket_id)).json()["result"]
    assert result["isError"] is True
    assert result["content"][0]["text"] == "No record has that ID. IDs are exact and case-sensitive."


@pytest.mark.parametrize("arguments", [{}, {"ticket_id": "T" * 33}, {"ticket_id": 727}])
def test_bad_arguments_are_a_tool_error(mcp, arguments):
    message = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "read_ticket", "arguments": arguments}}
    result = post(mcp, message).json()["result"]
    assert result["isError"] is True
    assert result["content"][0]["text"] == "Those arguments are not valid for this tool."


@pytest.mark.parametrize("name", ["keep_note", "search_records", "read_customer", "update_ticket"])
def test_no_other_tool_runs_whatever_the_desk_has(mcp, name):
    assert post(mcp, call(name=name)).json()["error"]["code"] == -32602


@pytest.mark.parametrize("method", ["resources/list", "prompts/list", "tools/write", "sampling/createMessage"])
def test_any_other_method_is_refused(mcp, method):
    assert post(mcp, {"jsonrpc": "2.0", "id": 4, "method": method}).json()["error"]["code"] == -32601


@pytest.mark.parametrize("message", [[], "text", 7, {"id": 1}, {"jsonrpc": "1.0", "id": 1, "method": "ping"},
                                     {"jsonrpc": "2.0", "id": 1, "method": 7}])
def test_anything_else_is_an_invalid_request(mcp, message):
    assert post(mcp, message).json()["error"]["code"] == -32600


def test_a_body_that_is_not_json_is_a_parse_error(mcp):
    response = mcp.post(PATH, content=b"{not json", headers=auth(TOKEN))
    assert response.json()["error"]["code"] == -32700


def test_nothing_but_brackets_is_a_parse_error_and_not_a_500(mcp):
    response = mcp.post(PATH, content=b"[" * (MCP_BODY_LIMIT - 1), headers=auth(TOKEN))
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32700


def test_an_oversized_body_is_not_read(mcp):
    response = mcp.post(PATH, content=b" " * (MCP_BODY_LIMIT + 1), headers=auth(TOKEN))
    assert response.json()["error"]["code"] == -32700


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_only_post_reaches_it(mcp, method):
    assert getattr(mcp, method)(PATH, headers=auth(TOKEN)).status_code == 405


@pytest.mark.parametrize("name", ["ORION_AGENT_TOKEN", "ORION_ADMIN_TOKEN"])
def test_settings_refuse_a_token_reused_from_the_desk(tmp_path, monkeypatch, name):
    for key in ("PG_HOST", "PG_USER", "PG_PASSWORD", "PG_DATABASE", "ORION_AGENT_TOKEN", "ORION_ADMIN_TOKEN", "ORION_MCP_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    tokens = {"ORION_AGENT_TOKEN": "a", "ORION_ADMIN_TOKEN": "b"}
    env.write_text("PG_HOST=h\nPG_USER=u\nPG_PASSWORD=p\nPG_DATABASE=d\nORION_AGENT_TOKEN=a\nORION_ADMIN_TOKEN=b\n"
                   f"ORION_MCP_TOKEN={tokens[name]}\n")
    with pytest.raises(RuntimeError, match="ORION_MCP_TOKEN must differ"):
        load_settings(env)


def test_settings_refuse_a_short_token(tmp_path, monkeypatch):
    for key in ("PG_HOST", "PG_USER", "PG_PASSWORD", "PG_DATABASE", "ORION_AGENT_TOKEN", "ORION_ADMIN_TOKEN", "ORION_MCP_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    base = "PG_HOST=h\nPG_USER=u\nPG_PASSWORD=p\nPG_DATABASE=d\nORION_AGENT_TOKEN=a\nORION_ADMIN_TOKEN=b\n"
    env.write_text(f"{base}ORION_MCP_TOKEN={'x' * 31}\n")
    with pytest.raises(RuntimeError, match="at least 32"):
        load_settings(env)
    env.write_text(f"{base}ORION_MCP_TOKEN={'x' * 32}\n")
    assert load_settings(env).mcp_token == "x" * 32
    env.write_text(base)
    assert load_settings(env).mcp_token is None


def test_the_token_stays_out_of_the_settings_repr():
    assert TOKEN not in repr(dataclasses.replace(SETTINGS, mcp_token=TOKEN))
