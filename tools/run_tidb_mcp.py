# /// script
# requires-python = ">=3.12"
# dependencies = ["certifi>=2025.1.31"]
# ///
"""Start the TiDB MCP server on orion_lab as the SELECT-only orion_reader login.

.mcp.json runs this file. The login comes from TIDB_USERNAME and TIDB_PASSWORD
in .env, so no secret sits in the repository, in command arguments or in logs.
Error messages name settings, never their values.

The server falls back to root when TIDB_USERNAME is unset, and it prefers
TIDB_DATABASE_URL over the username. So this launcher refuses to start unless
the login is orion_reader, and it drops the URL.

    uv run tools/run_tidb_mcp.py
"""
import os
import shutil
import subprocess
import sys

from orion_db import load_env

READER_ROLE = "orion_reader"
REQUIRED = ("TIDB_HOST", "TIDB_DATABASE", "TIDB_USERNAME", "TIDB_PASSWORD")
SERVER = ("--with", "mcp==1.30.0", "--from", "pytidb[mcp]==0.0.14", "tidb-mcp-server")


def server_env(values, base):
    """The server's environment: the caller's, plus only the lab settings it needs."""
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise ValueError("add to .env: " + ", ".join(missing))
    # TiDB Cloud Starter logins carry the instance prefix ("<prefix>.<role>").
    if values["TIDB_USERNAME"].rsplit(".", 1)[-1] != READER_ROLE:
        raise ValueError(f"TIDB_USERNAME is not the {READER_ROLE} login")
    env = {key: value for key, value in base.items() if key != "TIDB_DATABASE_URL"}
    env.update({key: values[key] for key in REQUIRED}, TIDB_PORT=values.get("TIDB_PORT", "4000"))
    return env


def main():
    try:
        env = server_env(load_env(), os.environ)
    except FileNotFoundError:
        sys.exit("TiDB MCP not started: no .env at the repository root")
    except ValueError as error:
        sys.exit(f"TiDB MCP not started: {error}")
    uvx = shutil.which("uvx")
    if not uvx:
        sys.exit("TiDB MCP not started: uvx is not on PATH")
    return subprocess.run([uvx, *SERVER], env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
