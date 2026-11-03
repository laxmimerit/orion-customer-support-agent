# /// script
# requires-python = ">=3.12"
# dependencies = ["PyMySQL==1.1.2", "psycopg[binary]==3.2.10", "certifi>=2025.1.31"]
# ///
"""Run ADR 0001's 14 migration checks on orion_lab (source) and orion_desk (target).

Only SELECT/SHOW statements run against orion_lab. Output is PASS or FAIL per check
with a short reason; it never prints dates, hosts, users or passwords.

    uv run tools/reconcile.py
"""
from collections import Counter
import datetime
from decimal import Decimal
import hashlib
import ssl
import subprocess
import sys
import time

from migrate import TABLES, pg_type
from orion_db import ROOT, load_env, redact, source, target

MANIFEST = {
    "plans": 3, "agents": 9, "customers": 300, "subscriptions": 300, "tickets": 4000,
    "messages": 36694, "invoices": 1800, "ticket_events": 7525, "releases": 12, "incidents": 1,
    "sla_policy": 12, "knowledge_articles": 40, "company_documents": 5, "staff_requests": 4,
    "lab_metadata": 1,
}
IDENTIFIERS = (("tickets", "ticket_id"), ("customers", "customer_id"), ("agents", "agent_id"), ("messages", "message_id"))
SIXTY_SECONDS = 60
FREE_STORAGE_BYTES = 50 * 1024 ** 3
CHECKS = []


def check(title):
    def register(function):
        CHECKS.append((title, function))
        return function
    return register


class Side:
    """One database, with the same small query surface for MySQL and PostgreSQL."""

    def __init__(self, name, connection, quote):
        self.name, self.connection, self.quote = name, connection, quote

    def rows(self, sql, args=None):
        if self.name == "source":
            with self.connection.cursor() as cursor:
                cursor.execute(sql, args)
                return [tuple(row) for row in cursor.fetchall()]
        return [tuple(row) for row in self.connection.execute(sql, args).fetchall()]

    def execute(self, sql):
        if self.name == "source":
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
        else:
            self.connection.execute(sql)

    def one(self, sql, args=None):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def q(self, name):
        return self.quote + name + self.quote


def token(value):
    """A driver-independent form of a value that keeps type, scale and exact text."""
    if value is None:
        return None
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, Decimal):
        return ("decimal", str(value))
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return ("timestamp", value.isoformat(sep=" ", timespec="microseconds"))
    if isinstance(value, datetime.date):
        return ("date", value.isoformat())
    if isinstance(value, str):
        return ("text", value)
    return (type(value).__name__, repr(value))


def snapshot(side, schema):
    """Every row of every table, keyed by primary key, as tokens."""
    data = {}
    for table in TABLES:
        columns, primary = schema[table]["columns"], schema[table]["primary"]
        positions = [columns.index(c) for c in primary]
        rows = side.rows("SELECT " + ",".join(side.q(c) for c in columns) + " FROM " + side.q(table))
        data[table] = {}
        for row in rows:
            values = tuple(token(v) for v in row)
            data[table][tuple(values[p] for p in positions)] = values
    return data


def fingerprint(data):
    digest = hashlib.sha256()
    for table in TABLES:
        for key in sorted(data[table]):
            digest.update(repr(data[table][key]).encode("utf-8", "surrogatepass"))
    return digest.hexdigest()


def compare(source_data, target_data):
    """Cell-by-cell differences, grouped by what kind of value differs."""
    differences = Counter()
    for table in TABLES:
        left, right = source_data[table], target_data[table]
        differences["missing rows"] += len(left.keys() - right.keys())
        differences["extra rows"] += len(right.keys() - left.keys())
        for key in left.keys() & right.keys():
            for a, b in zip(left[key], right[key]):
                if a == b:
                    continue
                if a is None or b is None:
                    differences["null"] += 1
                else:
                    differences[a[0]] += 1
    return differences


def read_schema(side):
    schema = {}
    for table in TABLES:
        columns = side.rows(
            "SELECT column_name, column_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY ordinal_position", (table,))
        primary = side.rows(
            "SELECT column_name FROM information_schema.statistics WHERE table_schema = DATABASE() "
            "AND table_name = %s AND index_name = 'PRIMARY' ORDER BY seq_in_index", (table,))
        schema[table] = {
            "columns": [c[0] for c in columns],
            "types": {c[0]: c[1].lower() for c in columns},
            "nullable": {c[0]: c[2] == "YES" for c in columns},
            "primary": [p[0] for p in primary],
        }
    return schema


def target_types(side):
    rows = side.rows(
        "SELECT table_name, column_name, data_type, character_maximum_length, numeric_precision, "
        "numeric_scale, datetime_precision, is_nullable FROM information_schema.columns "
        "WHERE table_schema = 'public'")
    found = {}
    for table, column, kind, length, precision, scale, dt_precision, nullable in rows:
        kind = kind.lower()
        if kind == "character varying":
            text = f"VARCHAR({length})"
        elif kind == "character":
            text = f"CHAR({length})"
        elif kind == "numeric":
            text = f"NUMERIC({precision},{scale})"
        elif kind == "timestamp without time zone":
            text = f"TIMESTAMP({dt_precision}) WITHOUT TIME ZONE"
        else:
            text = kind.upper()
        found[(table, column)] = (text, nullable == "YES")
    return found


def both(context, sql_source, sql_target=None, args=None):
    return context["source"].rows(sql_source, args), context["target"].rows(sql_target or sql_source, args)


# 1 ---------------------------------------------------------------------------
@check("The source wasn't touched (SELECT-only reader)")
def source_untouched(c):
    grants = [row[0].split(" TO ")[0].upper() for row in c["source"].rows("SHOW GRANTS")]
    allowed = {"GRANT USAGE ON *.*", "GRANT SELECT ON `ORION_LAB`.*"}
    if not grants or set(grants) - allowed:
        return False, "reader account has more than SELECT on orion_lab"
    return True, "reader holds SELECT on orion_lab only; this run issued only SELECT/SHOW there"


# 2 ---------------------------------------------------------------------------
@check("Totals match for all 15 tables, plus the investigation subtotals")
def totals(c):
    problems = []
    source_tables = sorted(r[0] for r in c["source"].rows(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"))
    target_tables = sorted(r[0] for r in c["target"].rows(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    if source_tables != sorted(TABLES):
        problems.append("orion_lab does not hold exactly the 15 tables")
    if target_tables != sorted(TABLES):
        problems.append("orion_desk does not hold exactly the 15 tables")
    manifest_notes = []
    for table in TABLES:
        left = c["source"].one(f"SELECT COUNT(*) FROM `{table}`")[0]
        right = c["target"].one(f'SELECT COUNT(*) FROM "{table}"')[0]
        if left != right:
            problems.append(f"{table} {left} vs {right}")
        if left != MANIFEST[table]:
            manifest_notes.append(f"{table} differs from manifest")
    subtotal_sql = (
        "SELECT COUNT(*), "
        "SUM(CASE WHEN resolution_hours > sla_resolution_hours THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN resolution_hours > sla_resolution_hours AND first_response_hours > sla_response_hours THEN 1 ELSE 0 END) "
        "FROM tickets WHERE status = 'resolved'")
    for side in ("source", "target"):
        values = tuple(int(v) for v in c[side].one(subtotal_sql))
        if values != (3525, 483, 226):
            problems.append(f"{side} subtotals {values}")
    if problems:
        return False, "; ".join(problems)
    note = "; live counts match the manifest" if not manifest_notes else "; " + ", ".join(manifest_notes)
    return True, "15 tables on both sides, every count equal; 3525 / 483 / 226 on both" + note


# 3 ---------------------------------------------------------------------------
@check("Identifiers are unchanged")
def identifiers(c):
    problems = []
    for table, column in IDENTIFIERS:
        left = sorted(r[0] for r in c["source"].rows(f"SELECT {column} FROM {table}"))
        right = sorted(r[0] for r in c["target"].rows(f"SELECT {column} FROM {table}"))
        if left != right:
            problems.append(f"{column} values differ")
        if any(v != v.strip() for v in left + right):
            problems.append(f"{column} has padded values")
        a, b = both(c, f"SELECT SUM(OCTET_LENGTH({column})) FROM {table}")
        if int(a[0][0]) != int(b[0][0]):
            problems.append(f"{column} byte length differs")
    for side in ("source", "target"):
        exact = [r[0] for r in c[side].rows("SELECT ticket_id FROM tickets WHERE ticket_id = %s", ("T00727",))]
        lower = c[side].rows("SELECT ticket_id FROM tickets WHERE ticket_id = %s", ("t00727",))
        if exact != ["T00727"] or lower:
            problems.append(f"{side} lookup of T00727 is not exact")
    if problems:
        return False, "; ".join(problems)
    return True, "ticket, customer, agent and message IDs identical, unpadded; T00727 opens exactly T00727"


# 4 ---------------------------------------------------------------------------
@check("Relationships hold")
def relationships(c):
    sql = {
        "tickets without a customer": "SELECT COUNT(*) FROM tickets t LEFT JOIN customers c ON c.customer_id = t.customer_id WHERE c.customer_id IS NULL",
        "messages without a ticket": "SELECT COUNT(*) FROM messages m LEFT JOIN tickets t ON t.ticket_id = m.ticket_id WHERE t.ticket_id IS NULL",
        "tickets with an unknown agent": "SELECT COUNT(*) FROM tickets t LEFT JOIN agents a ON a.agent_id = t.agent_id WHERE t.agent_id IS NOT NULL AND a.agent_id IS NULL",
    }
    problems = []
    for side in ("source", "target"):
        for label, query in sql.items():
            if c[side].one(query)[0] != 0:
                problems.append(f"{side} has {label}")
        owner = c[side].one(
            "SELECT t.customer_id, t.agent_id, a.name FROM tickets t LEFT JOIN agents a ON a.agent_id = t.agent_id WHERE t.ticket_id = %s", ("T00727",))
        messages = [r[0] for r in c[side].rows(
            "SELECT message_id FROM messages WHERE ticket_id = %s ORDER BY created_at, message_id", ("T00727",))]
        if owner != ("C0086", "A03", "Clara"):
            problems.append(f"{side} T00727 owner differs")
        if messages != [f"M00{n}" for n in range(7386, 7391)]:
            problems.append(f"{side} T00727 messages differ")
    if problems:
        return False, "; ".join(problems)
    return True, "no orphans on either side; T00727 → C0086, Clara (A03), messages M007386–M007390"


# 5 ---------------------------------------------------------------------------
@check("Dates are the same UTC values to the second")
def dates(c):
    problems = []
    if c["diff"]["timestamp"] or c["diff"]["date"]:
        problems.append(f"{c['diff']['timestamp'] + c['diff']['date']} date/time cells differ")
    expected = (datetime.datetime(2026, 6, 28, 3, 34, 0), datetime.datetime(2026, 6, 28, 11, 31, 36), datetime.datetime(2026, 6, 29, 5, 8, 48))
    sql = "SELECT created_at, first_response_at, resolved_at FROM tickets WHERE ticket_id = %s"
    for side in ("source", "target"):
        values = tuple(token(v) for v in c[side].one(sql, ("T00727",)))
        if values != tuple(token(v) for v in expected):
            problems.append(f"{side} T00727 times differ")
    types = c["target_types"]
    for table in TABLES:
        for column, kind in c["schema"][table]["types"].items():
            if kind.startswith(("datetime", "date")) and types.get((table, column), ("",))[0] != pg_type(kind):
                problems.append(f"{table}.{column} type differs")
    # A session in another time zone must read the same values (no implicit shift).
    target = c["target"]
    try:
        target.execute("SET TimeZone = 'Asia/Kolkata'")
        shifted = tuple(token(v) for v in target.one(sql, ("T00727",)))
        if shifted != tuple(token(v) for v in expected):
            problems.append("target values move with the session time zone")
    finally:
        target.execute("SET TimeZone = 'UTC'")
    if problems:
        return False, "; ".join(problems)
    return True, "every date/time cell equal; T00727 times exact on both; no shift under another session time zone"


# 6 ---------------------------------------------------------------------------
@check("Nulls stay null")
def nulls(c):
    problems, columns = [], 0
    for table in TABLES:
        names = c["schema"][table]["columns"]
        types = c["schema"][table]["types"]
        parts = {"source": [], "target": []}
        for side in ("source", "target"):
            q = c[side].q
            for name in names:
                col = q(name)
                parts[side].append(f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END)")
                if types[name].startswith(("varchar", "char", "text")):
                    parts[side].append(f"SUM(CASE WHEN CHAR_LENGTH({col}) = 0 THEN 1 ELSE 0 END)")
                elif types[name].startswith(("int", "tinyint", "smallint", "bigint", "decimal")):
                    parts[side].append(f"SUM(CASE WHEN {col} = 0 THEN 1 ELSE 0 END)")
        left = [int(v or 0) for v in c["source"].one(f"SELECT {', '.join(parts['source'])} FROM `{table}`")]
        right = [int(v or 0) for v in c["target"].one(f"SELECT {', '.join(parts['target'])} FROM \"{table}\"")]
        columns += len(names)
        if left != right:
            problems.append(f"{table} null/empty/zero counts differ")
    if c["diff"]["null"]:
        problems.append(f"{c['diff']['null']} cells are null on one side only")
    for side in ("source", "target"):
        if c[side].one("SELECT csat FROM tickets WHERE ticket_id = %s", ("T01841",)) != (None,):
            problems.append(f"{side} T01841 satisfaction is not null")
    if problems:
        return False, "; ".join(problems)
    return True, f"{columns} columns: null, empty-text and zero counts equal; T01841 satisfaction still null"


# 7 ---------------------------------------------------------------------------
@check("Numbers keep their precision")
def numbers(c):
    problems = []
    if c["diff"]["decimal"] or c["diff"]["int"]:
        problems.append(f"{c['diff']['decimal'] + c['diff']['int']} numeric cells differ")
    for table in TABLES:
        for column, kind in c["schema"][table]["types"].items():
            if kind.startswith("decimal") and c["target_types"].get((table, column), ("",))[0] != pg_type(kind):
                problems.append(f"{table}.{column} precision differs")
    hours = ("first_response_hours", "resolution_hours", "sla_response_hours", "sla_resolution_hours")
    a = c["source"].one("SELECT " + ",".join(f"CAST({h} AS CHAR)" for h in hours) + " FROM tickets WHERE ticket_id = %s", ("T00727",))
    b = c["target"].one("SELECT " + ",".join(f"CAST({h} AS TEXT)" for h in hours) + " FROM tickets WHERE ticket_id = %s", ("T00727",))
    if a != ("7.9600", "25.5800", "3.0000", "24.0000") or b != a:
        problems.append("T00727 hours do not read back as 7.9600 / 25.5800 / 3.0000 / 24.0000")
    a = c["source"].one("SELECT CAST(SUM(unit_price_usd) AS CHAR), CAST(SUM(total_usd) AS CHAR) FROM invoices")
    b = c["target"].one("SELECT CAST(SUM(unit_price_usd) AS TEXT), CAST(SUM(total_usd) AS TEXT) FROM invoices")
    if a != b:
        problems.append("invoice money totals differ")
    duration = {
        "source": "ROUND(TIMESTAMPDIFF(SECOND, created_at, {end}) / 3600, 4)",
        "target": "ROUND(CAST(EXTRACT(EPOCH FROM ({end} - created_at)) AS NUMERIC) / 3600, 4)",
    }
    results = {}
    for side in ("source", "target"):
        first = duration[side].format(end="first_response_at")
        resolved = duration[side].format(end="resolved_at")
        results[side] = tuple(int(v or 0) for v in c[side].one(
            f"SELECT SUM(CASE WHEN {first} = first_response_hours THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN first_response_hours IS NOT NULL THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN {resolved} = resolution_hours THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN resolution_hours IS NOT NULL THEN 1 ELSE 0 END) FROM tickets"))
        t = c[side].one(f"SELECT {first} = first_response_hours, {resolved} = resolution_hours FROM tickets WHERE ticket_id = %s", ("T00727",))
        if not (t[0] and t[1]):
            problems.append(f"{side} T00727 durations do not equal stored hours")
    if results["source"] != results["target"]:
        problems.append("ported duration check gives different results")
    if problems:
        return False, "; ".join(problems)
    s = results["source"]
    return True, (f"all NUMERIC(12,4) scales kept, invoices exact; timestamp durations equal stored hours for "
                  f"{s[0]}/{s[1]} first responses and {s[2]}/{s[3]} resolutions on both sides")


# 8 ---------------------------------------------------------------------------
@check("Ordering matches")
def ordering(c):
    queries = {
        "queue (newest)": "SELECT ticket_id FROM tickets ORDER BY created_at DESC, ticket_id",
        "queue (oldest)": "SELECT ticket_id FROM tickets ORDER BY created_at, ticket_id",
        "priority sort": "SELECT ticket_id FROM tickets ORDER BY priority, created_at DESC, ticket_id",
        "queue page 2": "SELECT ticket_id FROM tickets ORDER BY created_at DESC, ticket_id LIMIT 40 OFFSET 40",
        "messages": "SELECT message_id FROM messages ORDER BY created_at, message_id",
        "agents": "SELECT agent_id FROM agents ORDER BY name",
    }
    problems = [label for label, sql in queries.items() if len(set(map(tuple, both(c, sql)))) != 1]
    customers = (
        "SELECT c.customer_id, c.company FROM customers c LEFT JOIN (SELECT customer_id, COUNT(*) AS case_count, "
        "SUM(CASE WHEN status <> 'resolved' THEN 1 ELSE 0 END) AS active_count FROM tickets GROUP BY customer_id) x "
        "ON x.customer_id = c.customer_id ORDER BY c.company LIMIT 300")
    a, b = both(c, customers)
    if [r[1] for r in a] != [r[1] for r in b]:
        problems.append("customer list (company order)")
    elif a != b:
        problems.append("customer list ties resolve differently; needs a tie-break key")
    for side, rows in (("source", a), ("target", b)):
        names = [r[1] for r in rows]
        if "Fern Platform 086" not in names or names.index("Fern Platform 086") + 1 != 163:
            problems.append(f"{side} Fern Platform 086 is not row 163")
    if problems:
        return False, "differs: " + ", ".join(problems)
    return True, "queue, priority sort, paging, messages, agents and customer list in the same order; Fern Platform 086 is row 163"


# 9 ---------------------------------------------------------------------------
@check("Filters and search behave the same")
def filters(c):
    problems = []
    for column in ("status", "priority", "agent_id"):
        a, b = both(c, f"SELECT {column}, COUNT(*) FROM tickets GROUP BY {column}")
        if sorted(a, key=repr) != sorted(b, key=repr):
            problems.append(f"{column} filter counts differ")
    for side in ("source", "target"):
        if c[side].one("SELECT COUNT(*) FROM tickets WHERE status = %s", ("Resolved",))[0] != 0:
            problems.append(f"{side} status match is not case-sensitive")
    search = "SELECT COUNT(*) FROM tickets t WHERE LOWER(t.subject) LIKE LOWER(%s) ESCAPE '!'"

    def pattern(query):
        return "%" + query.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"

    for term, expected in (("invite", 265), ("invitation", 0)):
        for side in ("source", "target"):
            if c[side].one(search, (pattern(term),))[0] != expected:
                problems.append(f"{side} search '{term}' is not {expected}")
    subjects = [row[c["schema"]["tickets"]["columns"].index("subject")] for row in c["source_data"]["tickets"].values()]
    for term in ("%", "_", "!"):
        literal = sum(1 for s in subjects if s and term in s[1])
        for side in ("source", "target"):
            if c[side].one(search, (pattern(term),))[0] != literal:
                problems.append(f"{side} escape of '{term}' is not literal")
    if problems:
        return False, "; ".join(problems)
    return True, "status/priority/owner counts equal, case-sensitive; 'invite' 265, 'invitation' 0; ! escape literal for % _ !"


# 10 --------------------------------------------------------------------------
@check("Types read back correctly")
def types(c):
    problems = []
    for table in TABLES:
        for column, kind in c["schema"][table]["types"].items():
            found = c["target_types"].get((table, column))
            if found != (pg_type(kind), c["schema"][table]["nullable"][column]):
                problems.append(f"{table}.{column}")
    if problems:
        return False, "column types differ: " + ", ".join(problems[:5])
    sql = "SELECT escalated, reopened_count FROM tickets WHERE ticket_id = %s"
    for side in ("source", "target"):
        escalated, reopened = c[side].one(sql, ("T00727",))
        if type(escalated) is not int or type(reopened) is not int:
            problems.append(f"{side} escalated/reopened not integers")
        elif ("Yes" if escalated else "No", str(reopened)) != ("No", "0"):
            problems.append(f"{side} T00727 renders differently")
    counts = (
        "SELECT c.customer_id, COALESCE(x.case_count, 0), COALESCE(x.active_count, 0) FROM customers c LEFT JOIN "
        "(SELECT customer_id, COUNT(*) AS case_count, SUM(CASE WHEN status <> 'resolved' THEN 1 ELSE 0 END) AS active_count "
        "FROM tickets GROUP BY customer_id) x ON x.customer_id = c.customer_id")
    a, b = both(c, counts)
    if sorted((i, str(n), str(m)) for i, n, m in a) != sorted((i, str(n), str(m)) for i, n, m in b):
        problems.append("SUM(CASE …) case counts render differently")
    a, b = both(c, "SELECT status, COUNT(*) FROM tickets GROUP BY status")
    if sorted((s, str(n)) for s, n in a) != sorted((s, str(n)) for s, n in b):
        problems.append("status totals render differently")
    if problems:
        return False, "; ".join(problems)
    return True, "every column has its mapped type and nullability; T00727 shows Escalated No, Reopened 0; counts render the same"


# 11 --------------------------------------------------------------------------
@check("Text is intact")
def text(c):
    problems = []
    if c["diff"]["text"]:
        problems.append(f"{c['diff']['text']} text cells differ")
    for side in ("source_data", "target_data"):
        for table in TABLES:
            for row in c[side][table].values():
                for value in row:
                    if value and value[0] == "text":
                        try:
                            value[1].encode("utf-8")
                        except UnicodeEncodeError:
                            problems.append(f"{side} {table} has invalid UTF-8")
                            break
    for table in TABLES:
        for column, kind in c["schema"][table]["types"].items():
            if kind.startswith(("varchar", "char", "text")):
                a = c["source"].one(f"SELECT SUM(OCTET_LENGTH(`{column}`)), SUM(CHAR_LENGTH(`{column}`)) FROM `{table}`")
                b = c["target"].one(f'SELECT SUM(OCTET_LENGTH("{column}")), SUM(CHAR_LENGTH("{column}")) FROM "{table}"')
                if [int(v or 0) for v in a] != [int(v or 0) for v in b]:
                    problems.append(f"{table}.{column} byte/char length differs")
    if problems:
        return False, "; ".join(sorted(set(problems))[:5])
    return True, "every text cell equal, valid UTF-8, same byte and character lengths per column"


# 12 --------------------------------------------------------------------------
@check("The connection is safe")
def connection_safety(c):
    problems = []
    src = c["source"].connection
    context = getattr(src, "ctx", None)
    cipher = c["source"].one("SHOW STATUS LIKE 'Ssl_cipher'")
    if not (context and context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname and cipher and cipher[1]):
        problems.append("source TLS is not verified")
    dst = c["target"].connection
    if not (dst.pgconn.ssl_in_use and dst.info.get_parameters().get("sslmode") == "verify-full"):
        problems.append("target TLS is not verified")
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"], cwd=ROOT, capture_output=True)
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT, capture_output=True)
    if tracked.returncode == 0 or ignored.returncode != 0:
        problems.append(".env is tracked or not ignored")
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split("\n")
    secrets = [c["env"][k].encode() for k in ("TIDB_PASSWORD", "PG_PASSWORD") if c["env"].get(k)]
    for name in filter(None, files):
        path = ROOT / name
        if path.is_file() and any(s in path.read_bytes() for s in secrets):
            problems.append("a repository file contains a database password")
            break
    if problems:
        return False, "; ".join(problems)
    return True, "both connections use TLS with certificate and host checks; credentials only in ignored .env"


# 13 --------------------------------------------------------------------------
@check("It fits the preview's limits")
def preview_limits(c):
    queries = [
        ("SELECT COUNT(*) AS total FROM tickets t WHERE 1=1", None),
        ("SELECT t.ticket_id,t.subject,t.status,t.priority,t.created_at,t.customer_id,t.category,t.component,t.channel,c.company,c.plan_id,a.name,a.team "
         "FROM tickets t JOIN customers c ON c.customer_id=t.customer_id LEFT JOIN agents a ON a.agent_id=t.agent_id WHERE LOWER(t.subject) LIKE LOWER(%s) ESCAPE '!' "
         "ORDER BY t.priority,t.created_at DESC,t.ticket_id LIMIT %s OFFSET %s", ("%invite%", 40, 0)),
        ("SELECT t.*,c.company,c.contact_email,c.seats,c.country,a.name AS agent_name,a.team AS agent_team FROM tickets t "
         "JOIN customers c ON c.customer_id=t.customer_id LEFT JOIN agents a ON a.agent_id=t.agent_id WHERE t.ticket_id=%s", ("T00727",)),
        ("SELECT * FROM messages WHERE ticket_id=%s ORDER BY created_at,message_id", ("T00727",)),
        ("SELECT c.*,COALESCE(x.case_count,0) AS case_count,COALESCE(x.active_count,0) AS active_count FROM customers c LEFT JOIN "
         "(SELECT customer_id,COUNT(*) AS case_count,SUM(CASE WHEN status <> 'resolved' THEN 1 ELSE 0 END) AS active_count FROM tickets GROUP BY customer_id) x "
         "ON x.customer_id=c.customer_id ORDER BY c.company LIMIT 300", None),
        ("SELECT t.ticket_id,t.subject,t.status,t.priority,t.created_at FROM tickets t WHERE t.customer_id=%s ORDER BY t.created_at DESC,t.ticket_id", ("C0086",)),
        ("SELECT month,seats,unit_price_usd,total_usd,status FROM invoices WHERE customer_id=%s ORDER BY month DESC", ("C0086",)),
        ("SELECT s.*,p.name AS plan_name FROM subscriptions s JOIN plans p ON p.plan_id=s.plan_id WHERE s.customer_id=%s", ("C0086",)),
        ("SELECT * FROM knowledge_articles ORDER BY article_id", None),
        ("SELECT status,COUNT(*) AS total FROM tickets GROUP BY status ORDER BY status", None),
        ("SELECT * FROM messages ORDER BY created_at,message_id", None),
    ]
    slowest = 0.0
    for sql, args in queries:
        start = time.perf_counter()
        c["target"].rows(sql, args)
        slowest = max(slowest, time.perf_counter() - start)
    size = 0
    for table in TABLES:
        for row in c["target_data"][table].values():
            size += sum(len(v[1].encode("utf-8")) if v and v[0] == "text" else 8 for v in row)
    problems = []
    if slowest >= SIXTY_SECONDS:
        problems.append("a replacement query reached the 60 s statement timeout")
    if size > FREE_STORAGE_BYTES / 2:
        problems.append("row data uses more than half the free storage quota")
    if problems:
        return False, "; ".join(problems)
    return True, (f"{len(queries)} replacement queries, slowest {slowest:.1f} s of 60 s; about {size / 1024 ** 2:.0f} MiB "
                  "of row data against 50 GiB (RU use is not visible from SQL: check the console)")


# 14 --------------------------------------------------------------------------
@check("It can be done again")
def repeatable(c):
    problems = []
    script = ROOT / "tools/migrate.py"
    body = script.read_text() if script.is_file() else ""
    if "# /// script" not in body or "--replace" not in body:
        problems.append("tools/migrate.py is missing or cannot rerun end to end")
    if c["source_fingerprint"] != c["source_fingerprint_end"]:
        problems.append("orion_lab changed while the checks ran")
    if c["source_fingerprint"] != c["target_fingerprint"]:
        problems.append("orion_desk does not equal a fresh read of orion_lab")
    if problems:
        return False, "; ".join(problems)
    return True, "migrate.py reruns with uv (--replace); orion_lab stable during the run; orion_desk equals a fresh read of it"


def main():
    env = load_env()
    source_connection = source(env)
    target_connection = target(env)
    target_connection.autocommit = True
    context = {
        "env": env,
        "source": Side("source", source_connection, "`"),
        "target": Side("target", target_connection, '"'),
    }
    try:
        context["schema"] = read_schema(context["source"])
        context["target_types"] = target_types(context["target"])
        context["source_data"] = snapshot(context["source"], context["schema"])
        context["target_data"] = snapshot(context["target"], context["schema"])
        context["source_fingerprint"] = fingerprint(context["source_data"])
        context["target_fingerprint"] = fingerprint(context["target_data"])
        context["diff"] = compare(context["source_data"], context["target_data"])
        results = []
        for number, (title, function) in enumerate(CHECKS[:13], 1):
            results.append(run(number, title, function, context))
        context["source_fingerprint_end"] = fingerprint(snapshot(context["source"], context["schema"]))
        title, function = CHECKS[13]
        results.append(run(14, title, function, context))
    finally:
        source_connection.close()
        target_connection.close()
    passed = sum(results)
    print(f"\n{passed} of {len(results)} checks passed")
    return 0 if passed == len(results) else 1


def run(number, title, function, context):
    try:
        ok, reason = function(context)
    except Exception as error:
        ok, reason = False, f"error {type(error).__name__}: {redact(str(error), context['env'])[:200]}"
    print(f"{number:>2}  {'PASS' if ok else 'FAIL'}  {title}\n      {reason}", flush=True)
    return ok


if __name__ == "__main__":
    print("ADR 0001 migration checks: orion_lab (source) vs orion_desk (target)\n")
    try:
        sys.exit(main())
    except Exception as error:
        print(f"reconcile could not start: {type(error).__name__}: {redact(str(error), load_env())[:200]}", file=sys.stderr)
        sys.exit(2)
