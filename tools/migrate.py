# /// script
# requires-python = ">=3.12"
# dependencies = ["PyMySQL==1.1.2", "psycopg[binary]==3.2.10", "certifi>=2025.1.31"]
# ///
"""Copy orion_lab (MySQL-compatible TiDB) into orion_desk (PostgreSQL-compatible TiDB).

ADR 0001. The source is read through the SELECT-only reader inside one
consistent-snapshot transaction. Every column keeps its type, length, scale and
nullability; DATETIME values are UTC and land in TIMESTAMP columns unchanged.

    uv run tools/migrate.py             # first load into a new orion_desk
    uv run tools/migrate.py --replace   # drop and reload the 15 tables in orion_desk
"""
import argparse
import re
import sys

from orion_db import load_env, redact, source, target

TABLES = (
    "plans", "agents", "customers", "subscriptions", "tickets", "messages", "invoices",
    "ticket_events", "releases", "incidents", "sla_policy", "knowledge_articles",
    "company_documents", "staff_requests", "lab_metadata",
)
CHUNK = 2000


def quoted(name):
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        raise ValueError("Unexpected identifier")
    return '"' + name + '"'


def pg_type(column_type):
    """Map the exact MySQL column type to its PostgreSQL equivalent."""
    value = column_type.lower()
    if m := re.fullmatch(r"varchar\((\d+)\)", value):
        return f"VARCHAR({m[1]})"
    if m := re.fullmatch(r"char\((\d+)\)", value):
        return f"CHAR({m[1]})"
    if value in ("text", "mediumtext", "longtext"):
        return "TEXT"
    if m := re.fullmatch(r"decimal\((\d+),(\d+)\)", value):
        return f"NUMERIC({m[1]},{m[2]})"
    if m := re.fullmatch(r"datetime(?:\((\d)\))?", value):
        return f"TIMESTAMP({m[1] or 0}) WITHOUT TIME ZONE"
    if value == "date":
        return "DATE"
    # tinyint(1) holds 0/1 today but is still an integer type; keep it one.
    if re.fullmatch(r"tinyint(\(\d+\))?|smallint(\(\d+\))?", value):
        return "SMALLINT"
    if re.fullmatch(r"int(\(\d+\))?", value):
        return "INTEGER"
    if re.fullmatch(r"bigint(\(\d+\))?", value):
        return "BIGINT"
    raise ValueError("Unmapped source type: " + value)


def check_reader(cursor):
    cursor.execute("SHOW GRANTS")
    grants = [row[0].split(" TO ")[0].upper() for row in cursor.fetchall()]
    allowed = {"GRANT USAGE ON *.*", "GRANT SELECT ON `ORION_LAB`.*"}
    if not grants or set(grants) - allowed:
        raise PermissionError("Source account is not SELECT-only; refusing to export")


def export(env):
    """Read schema and rows for all 15 tables from one consistent snapshot."""
    tables = {}
    with source(env) as connection, connection.cursor() as cursor:
        check_reader(cursor)
        # TiDB rejects READ ONLY transactions (noop function); the SELECT-only grant
        # checked above is what keeps the source untouched.
        cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
        cursor.execute("SELECT DATE_FORMAT(UTC_TIMESTAMP(), '%Y-%m-%d %H:%i:%s UTC')")
        exported_at = cursor.fetchone()[0]
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
        found = sorted(row[0] for row in cursor.fetchall())
        if found != sorted(TABLES):
            raise ValueError("orion_lab does not hold exactly the 15 expected tables")
        for table in TABLES:
            cursor.execute(
                "SELECT column_name, column_type, is_nullable FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY ordinal_position", (table,))
            columns = [(name, pg_type(kind), nullable == "YES") for name, kind, nullable in cursor.fetchall()]
            cursor.execute(
                "SELECT index_name, non_unique, column_name FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY index_name, seq_in_index", (table,))
            indexes = {}
            for index, non_unique, column in cursor.fetchall():
                indexes.setdefault(index, (int(non_unique) == 0, []))[1].append(column)
            primary = indexes.pop("PRIMARY")[1]
            names = ",".join("`" + name + "`" for name, _, _ in columns)
            cursor.execute(f"SELECT {names} FROM `{table}` ORDER BY " + ",".join("`" + c + "`" for c in primary))
            rows = cursor.fetchall()
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            if count != len(rows):
                raise ValueError("Row read does not match COUNT(*): " + table)
            tables[table] = {"columns": columns, "primary": primary, "indexes": indexes, "rows": rows}
        cursor.execute("COMMIT")
    return exported_at, tables


def prepare_database(env, replace):
    name = env["PG_DATABASE"]
    with target(env, "postgres") as admin:
        admin.autocommit = True
        if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            admin.execute("CREATE DATABASE " + quoted(name))
            print(f"created database {name}")
    with target(env) as db:
        existing = {row[0] for row in db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")}
        clash = existing & set(TABLES)
        if clash and not replace:
            raise FileExistsError(f"{name} already holds {len(clash)} of the tables; rerun with --replace to reload them")
        for table in sorted(clash):
            db.execute("DROP TABLE " + quoted(table))
        db.commit()


def load(env, tables):
    counts = {}
    with target(env) as db:
        for table, spec in tables.items():
            definitions = [quoted(n) + " " + t + ("" if nullable else " NOT NULL") for n, t, nullable in spec["columns"]]
            definitions.append("PRIMARY KEY (" + ",".join(quoted(c) for c in spec["primary"]) + ")")
            db.execute(f"CREATE TABLE {quoted(table)} ({', '.join(definitions)})")
            for index, (unique, columns) in spec["indexes"].items():
                db.execute(f"CREATE {'UNIQUE ' if unique else ''}INDEX {quoted(index)} ON {quoted(table)} "
                           "(" + ",".join(quoted(c) for c in columns) + ")")
            names = ",".join(quoted(n) for n, _, _ in spec["columns"])
            rows = spec["rows"]
            with db.cursor() as cursor:
                for start in range(0, len(rows), CHUNK):
                    with cursor.copy(f"COPY {quoted(table)} ({names}) FROM STDIN") as copy:
                        for row in rows[start:start + CHUNK]:
                            copy.write_row(row)
            db.commit()
            counts[table] = db.execute(f"SELECT COUNT(*) FROM {quoted(table)}").fetchone()[0]
            print(f"loaded {table:<20} {counts[table]:>7}", flush=True)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replace", action="store_true", help="drop and reload the 15 tables if orion_desk already has them")
    args = parser.parse_args()
    env = load_env()
    exported_at, tables = export(env)
    print(f"exported orion_lab (SELECT-only reader, one snapshot) at {exported_at}", flush=True)
    prepare_database(env, args.replace)
    counts = load(env, tables)
    print(f"\n{'table':<20} {'orion_lab':>9} {'orion_desk':>10}")
    for table in TABLES:
        print(f"{table:<20} {len(tables[table]['rows']):>9} {counts[table]:>10}")
    if any(counts[t] != len(tables[t]["rows"]) for t in TABLES):
        raise ValueError("Row counts differ after load")
    print("\nmigration complete; run `uv run tools/reconcile.py` for the ADR 0001 checks")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        env = load_env()
        print(f"migration failed: {type(error).__name__}: {redact(str(error), env)}", file=sys.stderr)
        sys.exit(1)
