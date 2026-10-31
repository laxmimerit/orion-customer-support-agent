"""Read real MySQL source and reconcile an isolated PostgreSQL target schema.

Instructor rehearsal, not a claim that the course migration was filmed.
"""
import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from live_database import connection, helper
from check_postgres import connect

SCHEMA = "orion_migration_validation"


def identifier(value):
    if not re.fullmatch(r"[a-z_]+", value):
        raise ValueError("Unexpected identifier")
    return '"' + value + '"'


def pg_type(mysql_type):
    value = mysql_type.lower()
    if value == "tinyint(1)":
        return "BOOLEAN"
    if value.startswith(("int", "bigint", "smallint")):
        return "BIGINT"
    if value.startswith("decimal"):
        return "NUMERIC(12,4)"
    if value.startswith("datetime"):
        return "TIMESTAMPTZ"
    if value == "date":
        return "DATE"
    if value.startswith(("varchar", "text", "char")):
        return "TEXT"
    raise ValueError("Unmapped source type: " + value)


def converted(value, destination_type):
    if value is None:
        return None
    if destination_type == "BOOLEAN":
        return bool(value)
    if destination_type == "TIMESTAMPTZ":
        return value.replace(tzinfo=datetime.timezone.utc) if value.tzinfo is None else value.astimezone(datetime.timezone.utc)
    return value


def canonical(value):
    if isinstance(value, datetime.datetime):
        value = value.replace(tzinfo=datetime.timezone.utc) if value.tzinfo is None else value.astimezone(datetime.timezone.utc)
        return value.isoformat(timespec="microseconds")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return value


def digest(rows):
    value = hashlib.sha256()
    for row in rows:
        value.update(json.dumps([canonical(item) for item in row], ensure_ascii=False, separators=(",", ":")).encode())
        value.update(b"\n")
    return value.hexdigest()


def main():
    env = helper.load_env(ROOT / ".env.vercel")
    manifest = json.loads((ROOT / "database/manifest.json").read_text())
    report = {"source": "actual TiDB MySQL-compatible database; SELECT-only account", "destination": "separate TiDB PostgreSQL-compatible instance", "target_schema": SCHEMA, "tables": {}, "original_reference_modified": False}
    with connection(env) as source, connect() as destination:
        exists = destination.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s", (SCHEMA,)).fetchone()
        if exists:
            raise ValueError("Validation schema already exists; refusing to overwrite")
        destination.execute("CREATE SCHEMA " + identifier(SCHEMA))
        for table in manifest["table_counts"]:
            with source.cursor() as cursor:
                cursor.execute("SHOW COLUMNS FROM `" + table + "`")
                fields = cursor.fetchall()
                cursor.execute("SHOW KEYS FROM `" + table + "` WHERE Key_name='PRIMARY'")
                primary = [row["Column_name"] for row in sorted(cursor.fetchall(), key=lambda row: row["Seq_in_index"])]
                names = [row["Field"] for row in fields]
                types = [pg_type(row["Type"]) for row in fields]
                definitions = [identifier(name) + " " + dtype for name, dtype in zip(names, types)]
                definitions.append("PRIMARY KEY (" + ",".join(identifier(name) for name in primary) + ")")
                target = identifier(SCHEMA) + "." + identifier(table)
                destination.execute("CREATE TABLE " + target + " (" + ",".join(definitions) + ")")
                cursor.execute("SELECT * FROM `" + table + "` ORDER BY " + ",".join("`" + name + "`" for name in primary))
                original = cursor.fetchall()
            rows = [tuple(converted(row[name], dtype) for name, dtype in zip(names, types)) for row in original]
            for offset in range(0, len(rows), 100):
                batch = rows[offset:offset+100]
                placeholders = "(" + ",".join(["%s"] * len(names)) + ")"
                destination.execute("INSERT INTO " + target + " (" + ",".join(identifier(name) for name in names) + ") VALUES " + ",".join([placeholders] * len(batch)), tuple(value for row in batch for value in row))
            loaded = destination.execute("SELECT " + ",".join(identifier(name) for name in names) + " FROM " + target + " ORDER BY " + ",".join(identifier(name) for name in primary)).fetchall()
            expected_hash, actual_hash = digest(rows), digest(loaded)
            if len(loaded) != len(rows) or expected_hash != actual_hash:
                raise ValueError("Migration reconciliation failed: " + table)
            report["tables"][table] = {"rows": len(rows), "all_columns_sha256": actual_hash, "source_target_equal": True}
            (ROOT / "review/migration-progress.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({"migrated_table": table, "rows": len(rows), "checksum": "match"}), flush=True)
        joined = destination.execute('SELECT t.customer_id,c.company,COUNT(m.message_id) FROM orion_migration_validation.tickets t JOIN orion_migration_validation.customers c ON c.customer_id=t.customer_id JOIN orion_migration_validation.messages m ON m.ticket_id=t.ticket_id WHERE t.ticket_id=%s GROUP BY t.customer_id,c.company', ("T00727",)).fetchone()
        assert joined == ("C0086", "Fern Platform 086", 5)
        assert destination.execute("SELECT csat FROM orion_migration_validation.tickets WHERE ticket_id=%s", ("T00001",)).fetchone()[0] is None
        report.update(status="pass", selected_relationship="T00727 → C0086 → 5 messages", missing_csat="null preserved")
        (ROOT / "review/migration-rehearsal.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"migration_rehearsal": "pass", "tables": len(report["tables"])}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"migration_rehearsal": "failed", "error_class": type(error).__name__, "sqlstate": getattr(error, "sqlstate", None)}), file=sys.stderr)
        sys.exit(1)
