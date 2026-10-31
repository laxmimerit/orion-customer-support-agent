"""Build a deterministic MySQL/TiDB SQL seed from the existing synthetic data.

This is an instructor tool. It never connects to a database or overwrites source data.
"""
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

COURSE = Path(__file__).resolve().parents[2]
SOURCE = COURSE / "orion-course-resources"
TARGET = COURSE / "orion-environment/database"
FILES = ("plans", "agents", "customers", "subscriptions", "tickets", "messages",
         "invoices", "ticket_events", "releases", "incidents", "sla_policy")
KEYS = {"plans": ["plan_id"], "agents": ["agent_id"], "customers": ["customer_id"],
        "subscriptions": ["subscription_id"], "tickets": ["ticket_id"],
        "messages": ["message_id"], "invoices": ["invoice_id"],
        "ticket_events": ["ticket_id", "event_at", "event_type"],
        "releases": ["release_id"], "incidents": ["incident_id"],
        "sla_policy": ["priority", "plan_id"]}
INTEGER = {"seats", "csat", "reopened_count"}
NUMERIC = {"monthly_seat_usd", "unit_price_usd", "total_usd", "sla_response_hours",
           "sla_resolution_hours", "first_response_hours", "resolution_hours",
           "response_hours", "resolution_hours"}
TIMESTAMPS = {"created_at", "first_response_at", "resolved_at", "event_at", "start", "end"}
LONG = {"body", "change", "description"}

# Authored company context replaces the old pre-launch narrative. These are fictional
# workplace documents, not statements about real customers or an actual company.
DOCUMENTS = [
    {"document_id": "DOC001", "title": "Joining Orion engineering", "owner": "Maya · Product",
     "body": "Orion operates a support desk for software teams. Support staff use the Classic desk to look up tickets, customers and conversations. Maya owns product decisions, Arun owns engineering and Leena coordinates customer operations. You are joining engineering to build an improved replacement. The original application source is outside your access; the hosted desk and your development database are your starting evidence."},
    {"document_id": "DOC002", "title": "Support workflow", "owner": "Leena · Customer operations",
     "body": "A customer reports a problem and a support case receives a ticket identifier. Its customer identifier links the account; conversation messages link back to the ticket identifier. Agents read the thread and find relevant guidance before composing a response. The Classic desk provides access to existing support cases. The replacement must preserve these relationships. No outgoing reply may be sent automatically: a person must review and approve it."},
    {"document_id": "DOC003", "title": "Existing brand and interface", "owner": "Maya · Product",
     "body": "Keep the original Orion orbit mark and company identity. The Classic desk uses a compact header, grey navigation, basic forms and dense tables. Staff need clearer hierarchy, fewer page changes and readable status cues. A redesign must preserve ticket identities and actual records. A different colour or chart is not evidence that the underlying result is correct."},
    {"document_id": "DOC004", "title": "Reading our development snapshot", "owner": "Arun · Engineering",
     "body": "The reporting snapshot preserves the existing support history. All stored timestamps are UTC. A missing satisfaction score means no response was recorded, not zero. An absent first-response time means the response was not observed. Do not substitute zero. Service measures must state which records and observations they include. Plan list prices and recorded historical invoice prices are different facts."},
    {"document_id": "DOC005", "title": "Changes and responsibilities", "owner": "Arun · Engineering",
     "body": "Inspect the Classic desk and your database copy, record observed behaviour, identify open questions and propose acceptance checks before building the replacement. Changing a backend framework or database needs a reason, a migration plan and checks of identifiers, relationships, dates, nulls and record totals. Use a separate development database for engineering changes and preserve the existing operational records. New functionality and generated documents must be verified against evidence."},
]
REQUESTS = [
    {"request_id": "REQ001", "title": "Find related cases", "requester": "Leena",
     "body": "Subject search misses cases when customers describe the same issue in different words. Investigate a better retrieval experience and show why each proposed related case is relevant. Keep exact ticket lookup available."},
    {"request_id": "REQ002", "title": "Understand service performance", "requester": "Maya",
     "body": "The status report cannot answer how response times vary by channel, plan and period. Propose useful measures and explicit definitions. Check missing values and denominators against the underlying records."},
    {"request_id": "REQ003", "title": "Reduce navigation overhead", "requester": "Leena",
     "body": "Staff repeatedly move between the queue, customer page and conversation. Design a clearer workspace while preserving record identity, keyboard access and readable text."},
    {"request_id": "REQ004", "title": "Assist reply drafting", "requester": "Arun",
     "body": "Explore evidence-grounded draft replies using relevant tickets and knowledge articles. Show sources, handle insufficient evidence and retain human approval. Do not add automatic sending."},
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tables():
    tables, sources = {}, {}
    for name in FILES:
        path = SOURCE / "data" / (name + ".csv")
        with path.open(newline="", encoding="utf-8") as handle:
            tables[name] = list(csv.DictReader(handle))
        sources[str(path.relative_to(COURSE))] = sha(path)
    kb_path = SOURCE / "data/knowledge-base.json"
    tables["knowledge_articles"] = json.loads(kb_path.read_text())
    sources[str(kb_path.relative_to(COURSE))] = sha(kb_path)
    tables["company_documents"] = DOCUMENTS
    tables["staff_requests"] = REQUESTS
    tables["lab_metadata"] = [{"baseline_id": "orion-legacy-v1", "snapshot_utc": "2026-06-30T23:59:59Z", "fictional": "True", "scenario": "Inherited running support desk; replacement built from observable behaviour and data"}]
    return tables, sources


def validate(tables):
    for name, fields in KEYS.items():
        keys = [tuple(row[f] for f in fields) for row in tables[name]]
        assert len(keys) == len(set(keys)), (name, "duplicate key")
    for child, field, parent, target in [
        ("tickets", "customer_id", "customers", "customer_id"),
        ("tickets", "agent_id", "agents", "agent_id"),
        ("tickets", "plan_id", "plans", "plan_id"),
        ("messages", "ticket_id", "tickets", "ticket_id"),
        ("invoices", "customer_id", "customers", "customer_id"),
        ("subscriptions", "customer_id", "customers", "customer_id"),
        ("subscriptions", "plan_id", "plans", "plan_id"),
        ("ticket_events", "ticket_id", "tickets", "ticket_id"),
    ]:
        valid = {r[target] for r in tables[parent]}
        assert all(not r[field] or r[field] in valid for r in tables[child]), (child, field)
    ticket = next(r for r in tables["tickets"] if r["ticket_id"] == "T00727")
    assert ticket["customer_id"] == "C0086"
    assert sum(r["ticket_id"] == "T00727" for r in tables["messages"]) == 5
    assert next(r for r in tables["tickets"] if r["ticket_id"] == "T00001")["csat"] == ""


def kind(field):
    if field in INTEGER:
        return "INTEGER"
    if field in NUMERIC:
        return "DECIMAL(12,4)"
    if field in TIMESTAMPS:
        return "DATETIME(6)"
    if field in ("signup_date", "started_at", "date"):
        return "DATE"
    if field in ("escalated", "fictional"):
        return "BOOLEAN"
    return "TEXT" if field in LONG else "VARCHAR(512)"


def value(field, raw):
    if raw == "" or raw is None:
        return "NULL"
    if field in INTEGER:
        return str(int(raw))
    if field in NUMERIC:
        return str(Decimal(raw))
    if field in ("escalated", "fictional"):
        return "1" if str(raw).lower() == "true" else "0"
    if field in TIMESTAMPS:
        raw = raw.replace("T", " ").removesuffix("Z")
    # UTF-8 hex literals are independent of NO_BACKSLASH_ESCAPES and quote modes.
    return "CONVERT(X'" + str(raw).encode("utf-8").hex() + "' USING utf8mb4)"


def write_package():
    tables, sources = load_tables()
    validate(tables)
    keys = dict(KEYS, knowledge_articles=["article_id"], company_documents=["document_id"],
                staff_requests=["request_id"], lab_metadata=["baseline_id"])
    lines = ["-- Orion fictional legacy baseline. Restore only to an empty personal lab database.",
             "-- No credentials, evaluation answers, security fixtures or original application source.",
             "SET NAMES utf8mb4;", "SET time_zone = '+00:00';"]
    for name, rows in tables.items():
        fields = list(rows[0])
        definitions = ["`" + field + "` " + ("VARCHAR(64)" if field in keys[name] and kind(field) == "VARCHAR(512)" else kind(field)) for field in fields]
        definitions.append("PRIMARY KEY (" + ",".join("`" + f + "`" for f in keys[name]) + ")")
        lines.append("CREATE TABLE `" + name + "` (\n  " + ",\n  ".join(definitions) + "\n) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;")
        columns = ",".join("`" + field + "`" for field in fields)
        for start in range(0, len(rows), 100):
            tuples = ["(" + ",".join(value(f, r[f]) for f in fields) + ")" for r in rows[start:start+100]]
            lines.append("INSERT INTO `" + name + "` (" + columns + ") VALUES\n" + ",\n".join(tuples) + ";")
    for table, column in [("tickets", "customer_id"), ("tickets", "created_at"), ("tickets", "status"), ("messages", "ticket_id")]:
        lines.append(f"CREATE INDEX `{table}_{column}_idx` ON `{table}` (`{column}`);")
    lines.append("-- Logical foreign-key relationships are validated by the packaging tool; this baseline does not claim database-enforced foreign keys.")
    TARGET.mkdir(parents=True, exist_ok=True)
    sql = TARGET / "orion-baseline.sql"
    sql.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    manifest = {"baseline": "orion-legacy-v1", "fictional": True,
                "dialect": "MySQL-compatible; TiDB MySQL Starter tested separately", "sql_sha256": sha(sql),
                "source_sha256": sources, "table_counts": {name: len(rows) for name, rows in tables.items()},
                "authored_context": "company_documents and staff_requests are new fictional operating-company context; original pre-launch brief is preserved as history",
                "excluded": ["evaluation_inputs", "evaluation_labels", "security-fixtures", "private credentials", "original application source"],
                "runtime_status": "Run tools/lab.py check after every personal restore; instructor runtime evidence is recorded separately"}
    (TARGET / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"sql_bytes": sql.stat().st_size, "tables": manifest["table_counts"], "sha256": manifest["sql_sha256"]}, indent=2))


if __name__ == "__main__":
    write_package()
