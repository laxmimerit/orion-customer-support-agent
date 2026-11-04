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
from .models import (AccountDetails, ArticleSummary, ArticleText, ArticleTicket, Customer, Invoice, Message, Ticket,
                     TicketSummary)


def columns(model):
    # Column names come from the response models, never from a request.
    return sql.SQL(", ").join(sql.Identifier(name) for name in model.model_fields)


# Legacy orders (store.py:59, 81) run on MySQL, which puts NULLs last on DESC and
# first on ASC. PostgreSQL does the opposite, so say it explicitly.
TICKET_PAGE = sql.SQL(
    "SELECT {} FROM tickets ORDER BY created_at DESC NULLS LAST, ticket_id LIMIT %s OFFSET %s"
).format(columns(TicketSummary))
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

    def company(self):
        """Company documents and staff requests, each by ID."""
        with self.pool.connection() as db:
            return db.execute(COMPANY_SECTIONS).fetchall(), db.execute(STAFF_REQUESTS).fetchall()

    def exact_ticket(self, q):
        """The ticket whose ID is exactly q (case-sensitive, M01), as a search hit; None otherwise."""
        with self.pool.connection() as db:
            return db.execute(EXACT_ID, {"q": q}).fetchone()

    def nearest(self, vector, priority, limit):
        """The limit closest tickets and articles by cosine distance; only tickets when priority is given."""
        with self.pool.connection() as db:
            return db.execute(nearest_query(priority),
                              {"vector": as_vector(vector), "priority": priority, "limit": limit}).fetchall()

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
