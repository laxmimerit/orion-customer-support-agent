"""Cross-platform MCP launcher: private .env -> child process environment.

No secrets in command arguments, MCP JSON, logs or OS-specific credential stores.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def load_env(path, base=None):
    env = dict(os.environ if base is None else base)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if not sep or not key.strip().replace("_", "").isalnum():
                raise ValueError("Invalid .env syntax")
            value = value.strip()
            if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            env.setdefault(key.strip(), value)
    return env


def main():
    root = Path(__file__).resolve().parents[1]
    env = load_env(root / ".env")
    keys = ("TIDB_HOST", "TIDB_USERNAME", "TIDB_PASSWORD", "TIDB_DATABASE")
    if any(not env.get(key) for key in keys):
        raise ValueError("Configure your private .env before starting TiDB MCP")
    uvx = shutil.which("uvx")
    if not uvx:
        raise ValueError("uvx is required for the configured TiDB MCP server")
    result = subprocess.run([uvx, "--with", "mcp==1.30.0", "--from", "pytidb[mcp]==0.0.14", "tidb-mcp-server"], env=env)
    return result.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError):
        print("TiDB MCP could not start. Check .env and uvx installation; credentials suppressed.", file=sys.stderr)
        sys.exit(1)
