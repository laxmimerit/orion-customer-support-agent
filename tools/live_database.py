"""Instructor-only live baseline preparation. Never prints connection values."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import sys

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT.parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("private_env", ROOT / "tools/run_tidb_mcp.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def connection(env, select=True):
    import pymysql
    return pymysql.connect(host=env["TIDB_HOST"], port=int(env.get("TIDB_PORT", "4000")),
        user=env["TIDB_USERNAME"], password=env["TIDB_PASSWORD"],
        database=env["TIDB_DATABASE"] if select else None,
        ssl=ssl.create_default_context(), charset="utf8mb4", autocommit=True,
        connect_timeout=15, read_timeout=90, write_timeout=90,
        cursorclass=pymysql.cursors.DictCursor)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("connect", "restore", "verify", "reader", "context"))
    args = p.parse_args()
    env = helper.load_env(ROOT / ".env")
    name = env["TIDB_DATABASE"]
    if not re.fullmatch(r"orion_[a-z0-9_]+", name):
        raise ValueError("Dedicated Orion database name required")
    db = connection(env, select=False)
    with db.cursor() as cur:
        cur.execute("SELECT VERSION() AS version")
        version = cur.fetchone()["version"]
        print(json.dumps({"connected": True, "mysql_compatible_version": version}), flush=True)
        if args.action == "connect":
            return
        if args.action == "restore":
            cur.execute("CREATE DATABASE IF NOT EXISTS `" + name + "` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
        cur.execute("USE `" + name + "`")
        if args.action == "context":
            from package_database import DOCUMENTS
            for document in DOCUMENTS:
                cur.execute("UPDATE company_documents SET title=%s,owner=%s,body=%s WHERE document_id=%s", (document["title"], document["owner"], document["body"], document["document_id"]))
            print("Company handbook presentation updated; ticket/customer/message records unchanged.", flush=True)
        if args.action == "restore":
            cur.execute("SHOW TABLES")
            if cur.fetchall():
                raise ValueError("Target is not empty; no tables overwritten")
            seed = ROOT / "database/orion-baseline.sql"
            text = re.sub(r"^--.*$", "", seed.read_text(), flags=re.M)
            for number, statement in enumerate(text.split(";")):
                if statement.strip():
                    cur.execute(statement)
                    if number % 50 == 0:
                        print(json.dumps({"restore_statement": number}), flush=True)
        if args.action in ("restore", "verify"):
            manifest = json.loads((ROOT / "database/manifest.json").read_text())
            counts = {}
            for table, expected in manifest["table_counts"].items():
                cur.execute("SELECT COUNT(*) AS n FROM `" + table + "`")
                actual = cur.fetchone()["n"]
                if actual != expected:
                    raise ValueError("Record count mismatch: " + table)
                counts[table] = actual
            cur.execute("SELECT COUNT(*) AS n FROM messages m LEFT JOIN tickets t ON t.ticket_id=m.ticket_id WHERE t.ticket_id IS NULL")
            assert cur.fetchone()["n"] == 0
            cur.execute("SELECT csat FROM tickets WHERE ticket_id='T00001'")
            assert cur.fetchone()["csat"] is None
            cur.execute("SELECT COUNT(*) AS n FROM messages WHERE ticket_id='T00727'")
            assert cur.fetchone()["n"] == 5
            result = {"engine": version, "table_counts": counts, "message_relationships": "pass", "missing_score": "null preserved", "selected_conversation": 5, "seed_sha256": manifest["sql_sha256"]}
            (ROOT / "review/live-database.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps({"live_restore_and_checks": "pass", "tables": len(counts)}), flush=True)
        if args.action == "reader":
            # The deployed read-only reference must not use the supplied root account.
            prefix = env["TIDB_USERNAME"].split(".")[0]
            user = prefix + ".orion_reference"
            password = secrets.token_urlsafe(30)
            cur.execute("SELECT COUNT(*) AS n FROM mysql.user WHERE User=%s", (user,))
            if cur.fetchone()["n"]:
                raise ValueError("Reference reader already exists; refusing to rotate silently")
            cur.execute("CREATE USER %s IDENTIFIED BY %s", (user, password))
            cur.execute("GRANT SELECT ON `" + name + "`.* TO %s", (user,))
            values = dict(env, TIDB_USERNAME=user, TIDB_PASSWORD=password)
            path = ROOT / ".env.vercel"
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as output:
                for key in ("TIDB_HOST", "TIDB_PORT", "TIDB_USERNAME", "TIDB_PASSWORD", "TIDB_DATABASE"):
                    output.write(key + "=" + values[key] + "\n")
            with connection(values) as reader:
                with reader.cursor() as check:
                    check.execute("SELECT COUNT(*) AS n FROM tickets")
                    assert check.fetchone()["n"] == 4000
                    try:
                        check.execute("DELETE FROM lab_metadata WHERE 1=0")
                    except Exception as permission_error:
                        assert permission_error.args[0] in (1142, 1143, 1227)
                    else:
                        raise ValueError("Reference account unexpectedly permits writes")
            print("Read-only reference account created and checked; values saved privately.")
    db.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # SQL errors can include usernames, hosts or password fragments. Keep them private.
        print("Live operation failed (" + type(error).__name__ + "); connection values and SQL error details suppressed.", file=sys.stderr)
        sys.exit(1)
