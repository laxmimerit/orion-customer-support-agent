"""Read-only queries on orion_desk, the PostgreSQL-compatible development database (ADR 0001).

Every session and transaction is READ ONLY, so a write is refused by the
database itself. TLS certificates are verified, as in tools/orion_db.py.
"""
import certifi
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

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

    def table_counts(self):
        with self.pool.connection() as db:
            names = [row["table_name"] for row in db.execute(TABLES).fetchall()]
            return [
                {"table": name, "rows": db.execute(
                    sql.SQL("SELECT COUNT(*) AS n FROM {}").format(sql.Identifier(name))).fetchone()["n"]}
                for name in names
            ]
