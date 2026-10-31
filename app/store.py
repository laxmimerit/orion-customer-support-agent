"""Deliberately small legacy data layer. No generic SQL execution endpoint."""
import os
import ssl
from contextlib import contextmanager


@contextmanager
def database():
    import pymysql
    required = ("TIDB_HOST", "TIDB_USERNAME", "TIDB_PASSWORD", "TIDB_DATABASE")
    if any(not os.environ.get(key) for key in required):
        raise RuntimeError("Database configuration is incomplete")
    # TLS verification is enabled for TiDB Cloud. Local Docker can explicitly disable it.
    context = ssl.create_default_context(cafile=os.environ.get("TIDB_SSL_CA") or None)
    connection = pymysql.connect(
        host=os.environ["TIDB_HOST"], port=int(os.environ.get("TIDB_PORT", "4000")),
        user=os.environ["TIDB_USERNAME"], password=os.environ["TIDB_PASSWORD"],
        database=os.environ["TIDB_DATABASE"], charset="utf8mb4", autocommit=True,
        connect_timeout=10, read_timeout=15, write_timeout=15,
        ssl=None if os.environ.get("TIDB_TLS") == "off" else context,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield Store(connection)
    finally:
        connection.close()


class Store:
    def __init__(self, connection):
        self.connection = connection

    def query(self, sql, args=()):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, args)
            return list(cursor.fetchall())

    def one(self, sql, args=()):
        rows = self.query(sql, args)
        return rows[0] if rows else None

    def tickets(self, query="", status="", page=1):
        where, args = ["1=1"], []
        if query:
            # Literal, subject-only substring matching is the intended limitation.
            # Escape wildcard characters; use ! instead of mode-dependent backslashes.
            term = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            where.append("LOWER(t.subject) LIKE LOWER(%s) ESCAPE '!'")
            args.append("%" + term + "%")
        if status:
            where.append("t.status = %s")
            args.append(status)
        clause = " AND ".join(where)
        total = self.one("SELECT COUNT(*) AS total FROM tickets t WHERE " + clause, args)["total"]
        rows = self.query(
            "SELECT t.ticket_id,t.subject,t.status,t.priority,t.created_at,c.company,a.name "
            "FROM tickets t JOIN customers c ON c.customer_id=t.customer_id "
            "LEFT JOIN agents a ON a.agent_id=t.agent_id WHERE " + clause +
            " ORDER BY t.created_at DESC,t.ticket_id LIMIT %s OFFSET %s",
            args + [40, (page - 1) * 40],
        )
        return rows, total

    def ticket(self, ticket_id):
        return self.one(
            "SELECT t.*,c.company,a.name AS agent_name FROM tickets t "
            "JOIN customers c ON c.customer_id=t.customer_id "
            "LEFT JOIN agents a ON a.agent_id=t.agent_id WHERE t.ticket_id=%s", (ticket_id,))

    def messages(self, ticket_id):
        return self.query("SELECT * FROM messages WHERE ticket_id=%s ORDER BY created_at,message_id", (ticket_id,))

    def customers(self):
        return self.query("SELECT * FROM customers ORDER BY company LIMIT 300")

    def customer(self, customer_id):
        return self.one("SELECT * FROM customers WHERE customer_id=%s", (customer_id,))

    def customer_tickets(self, customer_id):
        return self.query("SELECT ticket_id,subject,status,created_at FROM tickets WHERE customer_id=%s ORDER BY created_at DESC,ticket_id", (customer_id,))

    def articles(self):
        return self.query("SELECT * FROM knowledge_articles ORDER BY article_id")

    def documents(self):
        return self.query("SELECT * FROM company_documents ORDER BY document_id")

    def requests(self):
        return self.query("SELECT * FROM staff_requests ORDER BY request_id")

    def counts(self):
        return self.query("SELECT status,COUNT(*) AS total FROM tickets GROUP BY status ORDER BY status")

    def metadata(self):
        return self.one("SELECT * FROM lab_metadata WHERE baseline_id=%s", ("orion-legacy-v1",))
