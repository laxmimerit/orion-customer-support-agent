"""Read-only queries on orion_desk, the PostgreSQL-compatible development database (ADR 0001).

Every session and transaction is READ ONLY, so a write is refused by the
database itself. TLS certificates are verified, as in tools/orion_db.py.
"""
from pathlib import Path

import certifi
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .embedding import DIMENSIONS, as_vector
from .models import (AccountDetails, ArticleSummary, ArticleText, ArticleTicket, Customer, Invoice, Message, Snapshot,
                     Ticket)


def columns(model):
    # Column names come from the response models, never from a request.
    return sql.SQL(", ").join(sql.Identifier(name) for name in model.model_fields)


# Legacy orders (store.py:59, 81) run on MySQL, which puts NULLs last on DESC and
# first on ASC. PostgreSQL does the opposite, so say it explicitly.
# Tickets are aged at the snapshot, as in reports/backlog.sql. The left join keeps every ticket, with a null age,
# if no snapshot is recorded. Four places are enough to tell whole seconds apart, so rounding can't move a ticket
# across its target.
TICKET_PAGE = """WITH snapshot AS (
    SELECT snapshot_utc::timestamptz AT TIME ZONE 'UTC' AS at FROM lab_metadata ORDER BY baseline_id LIMIT 1
)
SELECT t.ticket_id, t.subject, t.status, t.priority, t.channel, t.category, t.customer_id, t.agent_id, t.created_at,
       t.sla_response_hours, t.sla_resolution_hours, t.first_response_hours, t.resolution_hours,
       ROUND(EXTRACT(EPOCH FROM (s.at - t.created_at)) / 3600, 4) AS age_hours
FROM tickets t
LEFT JOIN snapshot s ON TRUE
ORDER BY t.created_at DESC NULLS LAST, t.ticket_id
LIMIT %s OFFSET %s"""
TICKET = sql.SQL("SELECT {} FROM tickets WHERE ticket_id = %s").format(columns(Ticket))
CUSTOMER = sql.SQL("SELECT {} FROM customers WHERE customer_id = %s").format(columns(Customer))
MESSAGES = sql.SQL(
    "SELECT {} FROM messages WHERE ticket_id = %s ORDER BY created_at ASC NULLS FIRST, message_id"
).format(columns(Message))
# Customers. Joined queries name their columns by hand; a live test checks they match the models.
# A ticket with no status counts as active, so IS DISTINCT FROM keeps it (<> would drop the null).
CUSTOMER_LIST = """SELECT c.customer_id, c.company, p.name AS plan, c.seats, c.region, c.industry,
       COUNT(t.ticket_id) FILTER (WHERE t.status IS DISTINCT FROM 'resolved') AS active_cases,
       COUNT(t.ticket_id) AS all_cases
FROM customers c
LEFT JOIN plans p ON p.plan_id = c.plan_id
LEFT JOIN tickets t ON t.customer_id = c.customer_id
GROUP BY c.customer_id, c.company, p.name, c.seats, c.region, c.industry
ORDER BY c.company NULLS LAST, c.customer_id"""
CUSTOMER_ACCOUNT = sql.SQL("SELECT customer_id, company, {} FROM customers WHERE customer_id = %s").format(
    columns(AccountDetails))
# Every customer has one subscription today; if that changes, the latest one started is shown.
CUSTOMER_SUBSCRIPTION = """SELECT s.subscription_id, p.name AS plan, s.seats, s.status
FROM subscriptions s
LEFT JOIN plans p ON p.plan_id = s.plan_id
WHERE s.customer_id = %s
ORDER BY s.started_at DESC NULLS LAST, s.subscription_id
LIMIT 1"""
CUSTOMER_TICKETS = """SELECT t.ticket_id, t.subject, t.component, t.channel, t.priority, t.status,
       a.name AS assigned_to, a.team
FROM tickets t
LEFT JOIN agents a ON a.agent_id = t.agent_id
WHERE t.customer_id = %s
ORDER BY t.created_at DESC NULLS LAST, t.ticket_id"""
CUSTOMER_INVOICES = sql.SQL("SELECT {} FROM invoices WHERE customer_id = %s ORDER BY month, invoice_id").format(
    columns(Invoice))
# Knowledge. A related ticket's subject equals the article title exactly.
ARTICLE_LIST = sql.SQL("SELECT {} FROM knowledge_articles ORDER BY article_id").format(columns(ArticleSummary))
ARTICLE = sql.SQL("SELECT {} FROM knowledge_articles WHERE article_id = %s").format(columns(ArticleText))
TICKET_SUBJECT = "SELECT subject FROM tickets WHERE ticket_id = %s"
TICKET_ARTICLES = sql.SQL("SELECT {} FROM knowledge_articles WHERE title = %s ORDER BY article_id").format(
    columns(ArticleSummary))
RELATED_TICKET_COUNT = "SELECT COUNT(*) AS n FROM tickets WHERE subject = %s"
RELATED_TICKETS = sql.SQL(
    "SELECT {} FROM tickets WHERE subject = %s "
    "ORDER BY status IS NOT DISTINCT FROM 'resolved', created_at DESC NULLS LAST, ticket_id LIMIT 5"
).format(columns(ArticleTicket))
MORE_IN_CATEGORY = sql.SQL(
    "SELECT {} FROM knowledge_articles WHERE category = %s AND article_id <> %s ORDER BY article_id"
).format(columns(ArticleSummary))
# Company. owner stays "Name · Team" here; main.py splits it.
COMPANY_SECTIONS = "SELECT document_id, title, owner, body FROM company_documents ORDER BY document_id"
STAFF_REQUESTS = "SELECT request_id, title, requester AS requested_by, body FROM staff_requests ORDER BY request_id"
# Mail. A mail has a link row only if it matched a ticket.
MAIL = """SELECT m.mail_id, l.ticket_id, l.linked_by, m.sender_name, m.subject, m.body
FROM mail_messages m
LEFT JOIN mail_links l ON l.mail_id = m.mail_id"""
TICKET_MAIL = MAIL + " WHERE l.ticket_id = %s ORDER BY m.received_at ASC NULLS FIRST, m.mail_id"
UNLINKED_MAIL = MAIL + " WHERE l.mail_id IS NULL ORDER BY m.received_at DESC NULLS LAST, m.mail_id LIMIT %s"
UNLINKED_COUNT = """SELECT COUNT(*) AS n FROM mail_messages m LEFT JOIN mail_links l ON l.mail_id = m.mail_id
WHERE l.mail_id IS NULL"""
ONE_MAIL = MAIL + " WHERE m.mail_id = %s"
# Notes stay out of TICKET and every model tool: only the notes routes read this table, so a note can't reach a draft.
CASE_NOTES = """SELECT note_id, author, handed_to, body, noted_at FROM case_notes WHERE ticket_id = %s
ORDER BY noted_at, note_id"""
# Late as in web/lib/sla.ts: an active case past a target, a stage still waiting being judged on its age at the snapshot.
LATE = """WITH snapshot AS (
    SELECT snapshot_utc::timestamptz AT TIME ZONE 'UTC' AS at FROM lab_metadata ORDER BY baseline_id LIMIT 1
), aged AS (
    SELECT t.*, ROUND(EXTRACT(EPOCH FROM (s.at - t.created_at)) / 3600, 4) AS age_hours
    FROM tickets t LEFT JOIN snapshot s ON TRUE
    WHERE t.status IS DISTINCT FROM 'resolved'
), late AS (
    SELECT *, COALESCE(first_response_hours, age_hours) > sla_response_hours AS late_reply,
           COALESCE(resolution_hours, age_hours) > sla_resolution_hours AS late_resolution
    FROM aged
)
"""
LATE_COUNT = LATE + "SELECT COUNT(*) AS n FROM late WHERE late_reply OR late_resolution"
LATE_CASES = LATE + """SELECT l.ticket_id, l.subject, l.status, l.priority, c.company, a.name AS approver, l.customer_id,
       l.late_reply IS TRUE AS late_reply, l.late_resolution IS TRUE AS late_resolution, l.age_hours,
       l.first_response_hours, l.sla_response_hours, l.sla_resolution_hours
FROM late l
LEFT JOIN customers c ON c.customer_id = l.customer_id
LEFT JOIN agents a ON a.agent_id = l.agent_id
WHERE l.late_reply OR l.late_resolution
ORDER BY l.age_hours DESC NULLS LAST, l.ticket_id
LIMIT %s"""
# One UTC day, from `start` up to but not including `end`. Late cases are counted now, by LATE_COUNT.
DAY_COUNTS = """SELECT
    (SELECT COUNT(*) FROM mail_messages WHERE synced_at >= %(start)s AND synced_at < %(end)s) AS mail,
    (SELECT COUNT(*) FROM mail_actions WHERE action = 'drafted' AND acted_at >= %(start)s AND acted_at < %(end)s) AS drafts,
    (SELECT COUNT(*) FROM mail_actions WHERE action = 'sent' AND acted_at >= %(start)s AND acted_at < %(end)s) AS sends,
    (SELECT COUNT(*) FROM mail_actions WHERE action = 'failed' AND acted_at >= %(start)s AND acted_at < %(end)s) AS failed,
    (SELECT COUNT(*) FROM case_notes WHERE handed_to IS NOT NULL AND noted_at >= %(start)s AND noted_at < %(end)s) AS handoffs"""
MAIL_INDEX = """SELECT m.mail_id, m.rfc_message_id, m.replies_to, l.ticket_id
FROM mail_messages m LEFT JOIN mail_links l ON l.mail_id = m.mail_id ORDER BY m.mail_id"""
THREAD_MAIL = """SELECT m.rfc_message_id, m.replies_to, m.sender_name, m.subject, m.body
FROM mail_messages m JOIN mail_links l ON l.mail_id = m.mail_id
WHERE m.mail_id = %s AND l.ticket_id = %s"""
APPROVERS = "SELECT name FROM agents WHERE name IS NOT NULL ORDER BY name, agent_id"
# Each row waits on the one before it, so the time alone puts them in order.
ACTION = "SELECT draft_id, action, ticket_id, actor, details, acted_at FROM mail_actions"
TICKET_ACTIONS = ACTION + " WHERE ticket_id = %s ORDER BY acted_at, draft_id, action"
DRAFT_ACTIONS = ACTION + " WHERE draft_id = %s"
# Search (plan increment 8). The inner query keeps the shape HNSW needs:
# ORDER BY embedding <=> vector LIMIT k on search_embeddings alone; titles are joined afterwards.
EXACT_ID = ("SELECT 'ticket' AS kind, ticket_id AS id, subject AS title, status, priority, category, "
            "NULL::float8 AS similarity FROM tickets WHERE ticket_id = %(q)s")
NEAREST = """WITH hits AS (
    SELECT doc_id, kind, source_id, embedding <=> %(vector)s::vector({dim}) AS distance
    FROM search_embeddings{where}
    ORDER BY embedding <=> %(vector)s::vector({dim})
    LIMIT %(limit)s
)
SELECT hits.kind, hits.source_id AS id, COALESCE(t.subject, a.title) AS title, t.status, t.priority,
       COALESCE(t.category, a.category) AS category, 1 - hits.distance AS similarity
FROM hits
LEFT JOIN tickets t ON hits.kind = 'ticket' AND t.ticket_id = hits.source_id
LEFT JOIN knowledge_articles a ON hits.kind = 'article' AND a.article_id = hits.source_id
ORDER BY hits.distance, hits.doc_id"""


def nearest_query(priority):
    where = "\n    WHERE priority = %(priority)s" if priority else ""
    return NEAREST.format(dim=DIMENSIONS, where=where)


# Similar tickets. The ticket's own stored vector is the query, so no model runs. hits keeps the HNSW shape, as in
# NEAREST, which is why articles and the ticket itself take places in the pool and are dropped afterwards.
SIMILAR_POOL = 51  # the ticket itself and its 50 nearest documents
SIMILAR_FIELDS = ("subject", "component", "priority", "plan_id", "channel")
SIMILAR_SOURCE = """SELECT t.subject, t.component, t.priority, t.plan_id, t.channel, e.embedding::text AS vector
FROM tickets t
LEFT JOIN search_embeddings e ON e.doc_id = 'ticket:' || t.ticket_id
WHERE t.ticket_id = %s"""
SIMILAR_TICKETS = f"""WITH hits AS (
    SELECT kind, source_id, embedding <=> %(vector)s::vector({DIMENSIONS}) AS distance
    FROM search_embeddings
    ORDER BY embedding <=> %(vector)s::vector({DIMENSIONS})
    LIMIT %(limit)s
)
SELECT t.ticket_id, t.subject, t.component, t.priority, t.plan_id, t.channel, t.agent_id, t.resolution_hours,
       t.sla_resolution_hours, t.first_response_hours, t.csat, t.reopened_count, t.escalated,
       1 - hits.distance AS similarity
FROM hits
JOIN tickets t ON hits.kind = 'ticket' AND t.ticket_id = hits.source_id
WHERE t.status = 'resolved' AND t.ticket_id <> %(ticket_id)s
ORDER BY hits.distance, t.ticket_id"""
SIMILAR_MESSAGES = """SELECT ticket_id, author_role, body FROM messages WHERE ticket_id = ANY(%s)
ORDER BY ticket_id, created_at ASC NULLS FIRST, message_id"""
# The title rule of TICKET_ARTICLES as well as the text: one reply is shared by articles on other subjects.
REPLY_ARTICLES = """SELECT article_id, title, category, body FROM knowledge_articles
WHERE title = %s AND position(%s in body) > 0 ORDER BY article_id"""


def shared_fields(source, ticket):
    """The fields two tickets have in common. A value missing from both is not a match (M07)."""
    return [name for name in SIMILAR_FIELDS if source[name] is not None and source[name] == ticket[name]]


def reply_summary(ticket_ids, messages):
    """How many different agent replies these tickets hold, and the one most of them used."""
    tickets_by_reply = {}
    for message in messages:
        if message["author_role"] == "agent" and message["body"] is not None:
            tickets_by_reply.setdefault(message["body"], set()).add(message["ticket_id"])
    # Most tickets first; the text settles a tie, so the answer never depends on row order.
    ranked = sorted(tickets_by_reply.items(), key=lambda item: (-len(item[1]), item[0]))
    answered = set().union(*tickets_by_reply.values())
    return {"distinct_replies": len(ranked), "top_reply": ranked[0][0] if ranked else None,
            "top_reply_tickets": len(ranked[0][1]) if ranked else 0,
            "tickets_without_reply": len(set(ticket_ids) - answered)}


def similar_result(source, tickets, messages, articles):
    """The response body, with every ticket found. Articles carry body only to compare them."""
    by_ticket = {}
    for message in messages:  # oldest first, so the last one kept is the last message
        count = by_ticket.get(message["ticket_id"], {}).get("message_count", 0)
        by_ticket[message["ticket_id"]] = {"message_count": count + 1, "last_author_role": message["author_role"],
                                           "last_body": message["body"]}
    no_messages = {"message_count": 0, "last_author_role": None, "last_body": None}
    items = [{**ticket, **by_ticket.get(ticket["ticket_id"], no_messages), "matched_on": shared_fields(source, ticket)}
             for ticket in tickets]
    return {
        "total": len(items),
        "items": items,
        "matched_on": [name for name in SIMILAR_FIELDS if items and all(name in item["matched_on"] for item in items)],
        "replies": reply_summary([ticket["ticket_id"] for ticket in tickets], messages),
        "articles": articles,
        "articles_read_same": len(articles) > 1 and len({article["body"] for article in articles}) == 1,
    }


# lab_metadata has one row today; the order keeps the answer stable if a second baseline is ever added.
SNAPSHOT = sql.SQL("SELECT {} FROM lab_metadata ORDER BY baseline_id LIMIT 1").format(columns(Snapshot))
# Reports: one checked SQL file each in api/reports, read once at import. No parameters are passed,
# so nothing from a request reaches the SQL.
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
REPORTS = {path.stem: path.read_text() for path in sorted(REPORTS_DIR.glob("*.sql"))}


def report_description(name):
    """The file's leading comment block, for the API docs."""
    lines = []
    for line in REPORTS[name].splitlines():
        if not line.startswith("--"):
            break
        lines.append(line[3:] if line.startswith("-- ") else line[2:])
    return "\n".join(lines)


TABLES = ("SELECT table_name FROM information_schema.tables "
          "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name")


class Store:
    def __init__(self, settings):
        self.database = settings.pg_database
        self.pool = ConnectionPool(
            kwargs=dict(
                host=settings.pg_host, port=settings.pg_port, user=settings.pg_user,
                password=settings.pg_password, dbname=settings.pg_database,
                sslmode="verify-full", sslrootcert=settings.pg_ssl_root_cert or certifi.where(),
                connect_timeout=10, row_factory=dict_row,
                options="-c TimeZone=UTC -c default_transaction_read_only=on",
            ),
            configure=self._read_only, check=ConnectionPool.check_connection,
            min_size=1, max_size=4, timeout=15, open=False, name="orion_desk",
        )

    @staticmethod
    def _read_only(connection):
        connection.read_only = True

    def open(self):
        # Don't wait: the API starts (and /docs works) even if the database is slow to answer.
        self.pool.open(wait=False)

    def close(self):
        self.pool.close()

    def ticket_page(self, limit, offset):
        with self.pool.connection() as db:
            total = db.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]
            return total, db.execute(TICKET_PAGE, (limit, offset)).fetchall()

    def ticket(self, ticket_id):
        """The ticket, its customer and its messages oldest first; None if the ID is unknown."""
        with self.pool.connection() as db:
            ticket = db.execute(TICKET, (ticket_id,)).fetchone()
            if ticket is None:
                return None
            customer = None
            if ticket["customer_id"] is not None:
                customer = db.execute(CUSTOMER, (ticket["customer_id"],)).fetchone()
            messages = db.execute(MESSAGES, (ticket_id,)).fetchall()
            return {"ticket": ticket, "customer": customer, "messages": messages}

    def ticket_mail(self, ticket_id):
        """Mail linked to the ticket, oldest first; None if the ticket ID is unknown."""
        with self.pool.connection() as db:
            if db.execute(TICKET_SUBJECT, (ticket_id,)).fetchone() is None:
                return None
            return db.execute(TICKET_MAIL, (ticket_id,)).fetchall()

    def unlinked_mail(self, limit):
        """How many mails matched no ticket, and the newest of them."""
        with self.pool.connection() as db:
            return db.execute(UNLINKED_COUNT).fetchone()["n"], db.execute(UNLINKED_MAIL, (limit,)).fetchall()

    def mail(self, mail_id):
        with self.pool.connection() as db:
            return db.execute(ONE_MAIL, (mail_id,)).fetchone()

    def case_notes(self, ticket_id):
        """The ticket's notes, oldest first; None if the ticket ID is unknown."""
        with self.pool.connection() as db:
            if db.execute(TICKET_SUBJECT, (ticket_id,)).fetchone() is None:
                return None
            return db.execute(CASE_NOTES, (ticket_id,)).fetchall()

    def late_cases(self, limit):
        """The full count, and the `limit` oldest late cases."""
        with self.pool.connection() as db:
            return db.execute(LATE_COUNT).fetchone()["n"], db.execute(LATE_CASES, (limit,)).fetchall()

    def day_counts(self, start, end):
        with self.pool.connection() as db:
            counts = db.execute(DAY_COUNTS, {"start": start, "end": end}).fetchone()
            return {**counts, "late": db.execute(LATE_COUNT).fetchone()["n"]}

    def mail_index(self):
        """What a sync needs to know about mail already stored."""
        with self.pool.connection() as db:
            return db.execute(MAIL_INDEX).fetchall()

    def existing_tickets(self, ticket_ids):
        with self.pool.connection() as db:
            rows = db.execute("SELECT ticket_id FROM tickets WHERE ticket_id = ANY(%s)", (list(ticket_ids),)).fetchall()
            return {row["ticket_id"] for row in rows}

    def customers(self):
        """Every customer with plan name and case counts, in one query, by company."""
        with self.pool.connection() as db:
            return db.execute(CUSTOMER_LIST).fetchall()

    def customer(self, customer_id):
        """The customer's account, subscription, tickets newest first and invoices oldest first; None if unknown."""
        with self.pool.connection() as db:
            account = db.execute(CUSTOMER_ACCOUNT, (customer_id,)).fetchone()
            if account is None:
                return None
            tickets = db.execute(CUSTOMER_TICKETS, (customer_id,)).fetchall()
            return {
                "customer_id": account["customer_id"],
                "company": account["company"],
                "account_details": account,
                "subscription": db.execute(CUSTOMER_SUBSCRIPTION, (customer_id,)).fetchone(),
                "support_history": {"total": len(tickets), "items": tickets},
                "invoice_history": db.execute(CUSTOMER_INVOICES, (customer_id,)).fetchall(),
            }

    def articles(self):
        with self.pool.connection() as db:
            return db.execute(ARTICLE_LIST).fetchall()

    def article(self, article_id):
        """The article, up to 5 related tickets (unresolved, then newest) and its category's others; None if unknown."""
        with self.pool.connection() as db:
            article = db.execute(ARTICLE, (article_id,)).fetchone()
            if article is None:
                return None
            title = (article["title"],)
            return {
                **article,
                "related_tickets": {"total": db.execute(RELATED_TICKET_COUNT, title).fetchone()["n"],
                                    "items": db.execute(RELATED_TICKETS, title).fetchall()},
                "more_in_category": db.execute(MORE_IN_CATEGORY, (article["category"], article_id)).fetchall(),
            }

    def ticket_articles(self, ticket_id):
        """Articles titled exactly as the ticket's subject, by ID; None if the ticket ID is unknown."""
        with self.pool.connection() as db:
            ticket = db.execute(TICKET_SUBJECT, (ticket_id,)).fetchone()
            if ticket is None:
                return None
            return db.execute(TICKET_ARTICLES, (ticket["subject"],)).fetchall()

    def similar_tickets(self, ticket_id):
        """Resolved tickets among the ticket's nearest documents, closest first; None if the ID is unknown."""
        with self.pool.connection() as db:
            source = db.execute(SIMILAR_SOURCE, (ticket_id,)).fetchone()
            if source is None:
                return None
            tickets, messages, articles = [], [], []
            if source["vector"] is not None:
                tickets = db.execute(SIMILAR_TICKETS, {"vector": source["vector"], "limit": SIMILAR_POOL,
                                                       "ticket_id": ticket_id}).fetchall()
            if tickets:
                messages = db.execute(SIMILAR_MESSAGES, ([ticket["ticket_id"] for ticket in tickets],)).fetchall()
            top_reply = reply_summary([], messages)["top_reply"]
            if top_reply is not None:
                articles = db.execute(REPLY_ARTICLES, (source["subject"], top_reply)).fetchall()
            return similar_result(source, tickets, messages, articles)

    def company(self):
        """Company documents and staff requests, each by ID."""
        with self.pool.connection() as db:
            return db.execute(COMPANY_SECTIONS).fetchall(), db.execute(STAFF_REQUESTS).fetchall()

    def snapshot(self):
        """When the lab data was taken; None if lab_metadata has no row."""
        with self.pool.connection() as db:
            return db.execute(SNAPSHOT).fetchone()

    def exact_ticket(self, q):
        """The ticket whose ID is exactly q (case-sensitive, M01), as a search hit; None otherwise."""
        with self.pool.connection() as db:
            return db.execute(EXACT_ID, {"q": q}).fetchone()

    def nearest(self, vector, priority, limit):
        """The limit closest tickets and articles by cosine distance; only tickets when priority is given."""
        with self.pool.connection() as db:
            return db.execute(nearest_query(priority),
                              {"vector": as_vector(vector), "priority": priority, "limit": limit}).fetchall()

    def thread_mail(self, ticket_id, mail_id):
        """One mail linked to this ticket, with the IDs a reply needs; None if it isn't."""
        with self.pool.connection() as db:
            return db.execute(THREAD_MAIL, (mail_id, ticket_id)).fetchone()

    def approvers(self):
        with self.pool.connection() as db:
            return [row["name"] for row in db.execute(APPROVERS).fetchall()]

    def ticket_actions(self, ticket_id):
        """The ticket's log, oldest first; None if the ticket ID is unknown."""
        with self.pool.connection() as db:
            if db.execute(TICKET_SUBJECT, (ticket_id,)).fetchone() is None:
                return None
            return db.execute(TICKET_ACTIONS, (ticket_id,)).fetchall()

    def draft_actions(self, draft_id):
        """The draft's rows by action; None if the draft ID is unknown."""
        with self.pool.connection() as db:
            rows = db.execute(DRAFT_ACTIONS, (draft_id,)).fetchall()
        return {row["action"]: row for row in rows} or None

    def report(self, name):
        """Rows of api/reports/<name>.sql, in the order the file sorts them."""
        with self.pool.connection() as db:
            return db.execute(REPORTS[name]).fetchall()

    def table_counts(self):
        with self.pool.connection() as db:
            names = [row["table_name"] for row in db.execute(TABLES).fetchall()]
            return [
                {"table": name, "rows": db.execute(
                    sql.SQL("SELECT COUNT(*) AS n FROM {}").format(sql.Identifier(name))).fetchone()["n"]}
                for name in names
            ]
