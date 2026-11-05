"""Settings from the repository's .env (never committed). Values already in the environment win.

Only the new database (PG_*), the two access tokens, the optional OPENROUTER_API_KEY, the optional
ORION_MCP_TOKEN and the optional ORION_MAIL_* are read. The legacy TIDB_* settings are ignored, so this API cannot
reach orion_lab.
"""
from dataclasses import dataclass
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
MCP_TOKEN_LENGTH = 32  # This token is the only thing between the internet and every ticket.
REQUIRED = ("PG_HOST", "PG_USER", "PG_PASSWORD", "PG_DATABASE", "ORION_AGENT_TOKEN", "ORION_ADMIN_TOKEN")
OPTIONAL = ("PG_PORT", "PG_SSL_ROOT_CERT", "OPENROUTER_API_KEY", "ORION_MCP_TOKEN", "ORION_MAIL_USER",
            "ORION_MAIL_APP_PASSWORD", "ORION_MAIL_LABEL")


@dataclass(frozen=True)
class Settings:
    pg_host: str
    pg_port: int
    pg_user: str
    pg_password: str
    pg_database: str
    agent_token: str
    admin_token: str
    pg_ssl_root_cert: str | None = None
    openrouter_api_key: str | None = None
    mcp_token: str | None = None  # Opens /api/mcp and nothing else. Left unset, nothing opens that route.
    mail_user: str | None = None  # With any of the three mail settings missing, the desk reports mail as not set up.
    mail_app_password: str | None = None
    mail_label: str | None = None

    def __repr__(self):
        # Never show hosts, users, passwords, tokens or keys in logs or tracebacks.
        return "Settings(<redacted>)"


def read_env_file(path):
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(path=ENV_FILE):
    values = read_env_file(path)
    values.update({key: os.environ[key] for key in (*REQUIRED, *OPTIONAL) if key in os.environ})
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise RuntimeError("Missing settings in .env: " + ", ".join(missing))
    if values["ORION_AGENT_TOKEN"] == values["ORION_ADMIN_TOKEN"]:
        raise RuntimeError("ORION_AGENT_TOKEN and ORION_ADMIN_TOKEN must differ")
    if values.get("ORION_MCP_TOKEN") in (values["ORION_AGENT_TOKEN"], values["ORION_ADMIN_TOKEN"]):
        raise RuntimeError("ORION_MCP_TOKEN must differ from ORION_AGENT_TOKEN and ORION_ADMIN_TOKEN")
    if 0 < len(values.get("ORION_MCP_TOKEN", "")) < MCP_TOKEN_LENGTH:
        raise RuntimeError(f"ORION_MCP_TOKEN must be at least {MCP_TOKEN_LENGTH} characters")
    return Settings(
        pg_host=values["PG_HOST"], pg_port=int(values.get("PG_PORT") or "5432"),
        pg_user=values["PG_USER"], pg_password=values["PG_PASSWORD"], pg_database=values["PG_DATABASE"],
        pg_ssl_root_cert=values.get("PG_SSL_ROOT_CERT") or None,
        agent_token=values["ORION_AGENT_TOKEN"], admin_token=values["ORION_ADMIN_TOKEN"],
        openrouter_api_key=values.get("OPENROUTER_API_KEY") or None,
        mcp_token=values.get("ORION_MCP_TOKEN") or None,
        mail_user=values.get("ORION_MAIL_USER") or None,
        mail_app_password=values.get("ORION_MAIL_APP_PASSWORD") or None,
        mail_label=values.get("ORION_MAIL_LABEL") or None,
    )
