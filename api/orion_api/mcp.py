"""A small read-only MCP server: one tool, read_ticket, over MCP's Streamable HTTP transport.

MCP sends every message as a POST, so this is the one route that isn't GET. It still changes nothing: the only tool reads
through Store, and the answer is case_text, the named fields the desk's own model sees, so no email or date leaves here.
It answers plain JSON and keeps no session, which a Vercel Function needs, as it holds nothing between requests.
"""
from pydantic import ValidationError

from .assistant import case_text
from .lookups import TOOLS, ReadTicket

# Newest first. A client asking for another version gets the newest, and decides for itself whether to carry on.
VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
TOOL = {"name": "read_ticket", "title": "Read a ticket", "description": TOOLS["read_ticket"].description,
        "inputSchema": ReadTicket.model_json_schema(), "annotations": {"readOnlyHint": True, "openWorldHint": False}}
PARSE_ERROR, INVALID_REQUEST, NO_METHOD, INVALID_PARAMS = -32700, -32600, -32601, -32602


def failure(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def tool_text(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def call_tool(params, db):
    if params.get("name") != TOOL["name"]:
        return None
    try:
        request = ReadTicket.model_validate(params.get("arguments") or {})
    except ValidationError:
        return tool_text("Those arguments are not valid for this tool.", True)
    detail = db.ticket(request.ticket_id)
    if detail is None:
        return tool_text("No record has that ID. IDs are exact and case-sensitive.", True)
    return tool_text(case_text(detail))


def answer(message, db):
    """The reply to one JSON-RPC message, or None for a notification, which gets no reply."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return failure(None, INVALID_REQUEST, "Send one JSON-RPC 2.0 message.")
    if "id" not in message:
        return None
    request_id, method = message["id"], message["method"]
    params = message.get("params")
    params = params if isinstance(params, dict) else {}
    if method == "initialize":
        asked = params.get("protocolVersion")
        result = {"protocolVersion": asked if asked in VERSIONS else VERSIONS[0], "capabilities": {"tools": {}},
                  "serverInfo": {"name": "orion-desk", "version": "0.1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        result = call_tool(params, db)
        if result is None:
            return failure(request_id, INVALID_PARAMS, "No tool has that name.")
    else:
        return failure(request_id, NO_METHOD, "This server has no such method.")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}
