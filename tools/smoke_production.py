"""Read-only smoke test of the live desk. It only opens pages and sends /api/mcp a request with no valid token, so it never
sends mail or writes anything. Run from the repo root: python tools/smoke_production.py"""
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://orion-customer-support-agent.vercel.app"
ENV_NAME = "VERCEL_AUTOMATION_BYPASS_SECRET"


def bypass_secret():
    for line in Path(".env").read_text().splitlines():
        if line.startswith(f"{ENV_NAME}="):
            return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit(f"{ENV_NAME} is not in .env")


def call(path, secret, method="GET", headers=None):
    """Status and body. Script tags are dropped, so a check reads what the page shows and not its data payload."""
    request = urllib.request.Request(BASE + path, method=method, data=b"{}" if method == "POST" else None,
                                     headers={"x-vercel-protection-bypass": secret, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status, body = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read().decode(errors="replace")
    return status, re.sub(r"<script.*?</script>", "", body, flags=re.S)


def panel_connected(html, title):
    """True when the pill right after a Settings panel's title says Connected."""
    start = html.find(f">{title}<")
    words = re.sub(r"<[^>]+>", " ", html[start:start + 400]).split()
    return start >= 0 and words[len(title.split()):][:1] == ["Connected"]


def main():
    secret = bypass_secret()
    queue_status, queue = call("/", secret)
    report_status, report = call("/reports", secret)
    ticket_status, ticket = call("/tickets/T00727", secret)
    settings_status, settings = call("/settings", secret)
    no_token = call("/api/mcp", secret, "POST", {"Content-Type": "application/json"})
    bad_token = call("/api/mcp", secret, "POST", {"Content-Type": "application/json", "Authorization": "Bearer not-a-token"})

    checks = {
        "queue loads with tickets": queue_status == 200 and "Ticket queue" in queue and "/tickets/T" in queue,
        "report loads": report_status == 200 and "Team reports" in report and "<h2" in report,
        "T00727 shows five messages": ticket_status == 200 and ticket.count("conv-bubble") == 5,
        "Settings shows model connected": settings_status == 200 and panel_connected(settings, "Language models"),
        "Settings shows mail connected": settings_status == 200 and panel_connected(settings, "Customer mail"),
        # The API's own refusal, so a 401 from Vercel's protection can't pass for it.
        "/api/mcp refuses no token": no_token[0] == 401 and "missing_token" in no_token[1],
        "/api/mcp refuses a wrong token": bad_token[0] == 401 and "invalid_token" in bad_token[1],
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
