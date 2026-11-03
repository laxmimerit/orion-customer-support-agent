"""Read-only queries on orion_desk, the PostgreSQL-compatible development database (ADR 0001).

Every session and transaction is READ ONLY, so a write is refused by the
database itself. TLS certificates are verified, as in tools/orion_db.py.
"""
import certifi
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .embedding import DIMENSIONS, as_vector
from .models import Customer, Message, Ticket, TicketSummary


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

    def exact_ticket(self, q):
        """The ticket whose ID is exactly q (case-sensitive, M01), as a search hit; None otherwise."""
        with self.pool.connection() as db:
            return db.execute(EXACT_ID, {"q": q}).fetchone()

    def nearest(self, vector, priority, limit):
        """The limit closest tickets and articles by cosine distance; only tickets when priority is given."""
        with self.pool.connection() as db:
            return db.execute(nearest_query(priority),
                              {"vector": as_vector(vector), "priority": priority, "limit": limit}).fetchall()

    def table_counts(self):
        with self.pool.connection() as db:
            names = [row["table_name"] for row in db.execute(TABLES).fetchall()]
            return [
                {"table": name, "rows": db.execute(
                    sql.SQL("SELECT COUNT(*) AS n FROM {}").format(sql.Identifier(name))).fetchone()["n"]}
                for name in names
            ]
