"""Validate the user-specified TiDB MCP server without printing credentials."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("env_loader", ROOT / "tools/run_tidb_mcp.py")
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = loader.load_env(ROOT / ".env.vercel")
    server = StdioServerParameters(command=shutil.which("uvx"), args=["--with", "mcp==1.30.0", "--from", "pytidb[mcp]==0.0.14", "tidb-mcp-server"], env=env)
    # Keep third-party startup logs private, since tools may log connection details.
    logpath = ROOT / "review/mcp-private-stderr.log"
    fd = os.open(logpath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as errors:
        async with stdio_client(server, errlog=errors) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                schemas = [{"name": item.name, "inputSchema": item.inputSchema} for item in tools.tools]
                (ROOT / "review/mcp-tools.json").write_text(json.dumps(schemas, indent=2) + "\n")
                result = await session.call_tool("db_query", {"sql_stmt": "SELECT COUNT(*) AS ticket_count FROM tickets"})
                assert not result.isError
                raw = " ".join(item.text for item in result.content if hasattr(item, "text"))
                assert "4000" in raw
                import importlib.metadata
                versions = {name: importlib.metadata.version(name) for name in ("pytidb", "mcp")}
                report = {"mcp_initialized": True, "tool_names": [item.name for item in tools.tools], "query_ticket_count": 4000, "versions": versions}
                (ROOT / "review/mcp-live-check.json").write_text(json.dumps(report, indent=2) + "\n")
                print(json.dumps(report))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print("MCP check failed (" + type(error).__name__ + "); private details suppressed.", file=sys.stderr)
        sys.exit(1)
