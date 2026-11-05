"""The agent's settings, kept apart from the person running it.

Settings come from two files and nothing else. The environment is not read, unlike the desk's settings, so a shell
set up for someone's own Claude Code cannot redirect the agent, and the agent's settings never reach that shell.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import tomllib

from orion_api.settings import Settings, read_env_file

ROOT = Path(__file__).resolve().parents[2]
# The key goes to this address and no other, so a changed agent.toml can't send it elsewhere.
BASE_URL = "https://openrouter.ai/api"
TOML_FILE = Path(__file__).resolve().parent / "agent.toml"
ENV_FILE = ROOT / ".env.triage-agent"
REVIEW_FILE = ROOT / ".triage-agent" / "review.jsonl"
REQUIRED = ("OPENROUTER_API_KEY", "PG_HOST", "PG_USER", "PG_PASSWORD", "PG_DATABASE")
# The desk's MCP token goes over TLS, or stays on this machine.
MCP_URL = re.compile(r"https://|http://127\.0\.0\.1[:/]")
# All the CLI needs from the parent. The SDK starts the CLI with the whole of os.environ, so anything else would reach it.
KEPT_ENVIRONMENT = ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TZ")
# Every name the CLI turns into a model. Left unset, a background call would go to a paid Claude model on this key.
MODEL_SLOTS = ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
               "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_SMALL_FAST_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL")


@dataclass(frozen=True)
class Limits:
    max_turns: int
    estimated_usd_per_ticket: float
    estimated_usd_per_run: float
    real_usd_per_run: float
    tickets_per_run: int
    seconds_per_ticket: float
    failures_in_a_row: int
    busy_wait_seconds: float
    workers: int


@dataclass(frozen=True)
class AgentConfig:
    model: str
    base_url: str
    limits: Limits
    openrouter_key: str
    database: Settings | None
    mcp_url: str | None = None  # Only `draft` needs these two, so a triage run works without them.
    mcp_token: str | None = None
    vercel_bypass: str | None = None  # Gets past the login wall on a protected deployment. The route's token still applies.

    def __repr__(self):
        return "AgentConfig(<redacted>)"


def load_config(toml_file=TOML_FILE, env_file=ENV_FILE, needs_database=True):
    """`draft` reads through the route, so a machine that only drafts holds no database login."""
    with open(toml_file, "rb") as file:
        values = tomllib.load(file)
    secrets = read_env_file(env_file)
    missing = [key for key in (REQUIRED if needs_database else REQUIRED[:1]) if not secrets.get(key)]
    if missing:
        raise SystemExit(f"Missing in {Path(env_file).name}: " + ", ".join(missing))
    model = values["model"]["name"]
    if not model.endswith(":free"):
        raise SystemExit(f"The agent runs only on a free model, and {model} is not one.")
    if values["model"]["base_url"] != BASE_URL:
        raise SystemExit(f"The agent's key goes only to {BASE_URL}.")
    mcp_url = secrets.get("ORION_MCP_URL") or None
    if mcp_url and not MCP_URL.match(mcp_url):
        raise SystemExit("ORION_MCP_URL must be https, or http on 127.0.0.1.")
    database = None if not needs_database else Settings(
        pg_host=secrets["PG_HOST"], pg_port=int(secrets.get("PG_PORT") or "5432"), pg_user=secrets["PG_USER"],
        pg_password=secrets["PG_PASSWORD"], pg_database=secrets["PG_DATABASE"],
        pg_ssl_root_cert=secrets.get("PG_SSL_ROOT_CERT") or None, agent_token="", admin_token="")
    return AgentConfig(model=model, base_url=values["model"]["base_url"], limits=Limits(**values["limits"]),
                       openrouter_key=secrets["OPENROUTER_API_KEY"], database=database, mcp_url=mcp_url,
                       mcp_token=secrets.get("ORION_MCP_TOKEN") or None,
                       vercel_bypass=secrets.get("VERCEL_AUTOMATION_BYPASS_SECRET") or None)


def cli_environment(config, home):
    """What the CLI runs with, over KEPT_ENVIRONMENT. `home` is an empty folder, so it finds no one's config or login."""
    return {
        "HOME": str(home),
        "CLAUDE_CONFIG_DIR": str(home),
        "ANTHROPIC_BASE_URL": config.base_url,
        "ANTHROPIC_AUTH_TOKEN": config.openrouter_key,
        "ANTHROPIC_API_KEY": "",  # In print mode a key wins over the token, so one from anywhere else must not get in.
        **dict.fromkeys(MODEL_SLOTS, config.model),
        "ENABLE_TOOL_SEARCH": "false",  # Otherwise the CLI adds a placeholder tool beside the desk's.
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_TELEMETRY": "1",
        "DISABLE_ERROR_REPORTING": "1",
        "DISABLE_AUTOUPDATER": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        "CLAUDE_CODE_MAX_RETRIES": "2",
    }


@contextmanager
def bare_environment():
    """Leave only KEPT_ENVIRONMENT in os.environ while the agent runs, then put everything back."""
    saved = dict(os.environ)
    for name in saved:
        if name not in KEPT_ENVIRONMENT:
            del os.environ[name]
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)
