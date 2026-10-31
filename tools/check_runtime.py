"""Exercise the real Flask test client against the authorised live TiDB baseline."""
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("env_loader", ROOT / "tools/run_tidb_mcp.py")
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)
os.environ.update(loader.load_env(ROOT / ".env.vercel"))
from app.web import app

client = app.test_client()
paths = ["/", "/tickets", "/tickets?page=2", "/tickets?status=resolved", "/tickets?status=in+progress", "/tickets?q=Invite+link+expired",
         "/tickets?q=zzzz-no-such-subject-zzzz", "/tickets/T00727", "/tickets/T00001",
         "/customers", "/customers/C0086", "/knowledge", "/company", "/reports", "/healthz",
         "/static/legacy.css", "/static/orion-logo.png", "/static/orion-icon.svg"]
checks = []
from app.store import database
with database() as db:
    try:
        db.query("DELETE FROM lab_metadata WHERE 1=0")
    except Exception as denied:
        assert denied.args[0] in (1142, 1143, 1227)
    else:
        raise AssertionError("Hosted reference account unexpectedly permits writes")
for path in paths:
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    checks.append({"path": path, "status": response.status_code, "bytes": len(response.data)})
for path in ["/tickets/unknown", "/customers/unknown", "/missing"]:
    assert client.get(path).status_code == 404
for path in ["/tickets?page=0", "/tickets?page=bad", "/tickets?status=bad"]:
    assert client.get(path).status_code == 400
assert client.post("/tickets").status_code == 405
ticket = client.get("/tickets/T00727").get_data(as_text=True)
assert "Fern Platform 086" in ticket and "Invite link expired" in ticket
assert client.get("/tickets/T00001").get_data(as_text=True).find("Not recorded") > 0
assert "No matching tickets" in client.get("/tickets?q=zzzz-no-such-subject-zzzz").get_data(as_text=True)
assert "4000 matching tickets" in client.get("/tickets").get_data(as_text=True)
assert "root" not in client.get("/healthz").get_data(as_text=True)
for path, name in [("/tickets", "queue"), ("/tickets/T00727", "case"), ("/company", "company"), ("/reports", "reports")]:
    (ROOT / "review" / (name + ".html")).write_text(client.get(path).get_data(as_text=True))
(ROOT / "review/flask-live-checks.json").write_text(json.dumps({"backend": "actual TiDB MySQL-compatible", "flask": "actual test client", "routes": checks, "negative_route_cases": 7, "database_write_probe": "denied", "status": "pass"}, indent=2) + "\n")
print(json.dumps({"flask_live_checks": "pass", "success_routes": len(checks), "negative_route_cases": 7}))
