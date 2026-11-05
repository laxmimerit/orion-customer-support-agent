# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]==3.2.10", "certifi>=2025.1.31"]
# ///
"""Create mail_messages and mail_links, and the one login that may write to them.

Connects with the owner login (PG_USER) from .env, creates the two tables and a role that can log in and reach those
tables alone: read them and add rows. It has no UPDATE and no DELETE, so a stored mail can't be changed or removed, and
it can't read or write any migrated table or create anything. A mail's link to a ticket is a row of its own, because
this database has no column-level grants, and table-wide UPDATE would let this login rewrite a mail's text.
orion_desk_reader gets SELECT on both, because the deployed API reads them through that login.

It then logs in as the new role and checks both what works and what must be refused, with every write rolled back. Only
after that are PG_MAIL_WRITER_USER and PG_MAIL_WRITER_PASSWORD appended to .env. Nothing is printed except PASS/FAIL.

    uv run tools/create_mail_writer.py

A table added later is out of this login's reach until someone grants it, which is the point.
"""
import secrets
import sys

import psycopg
from psycopg import sql

from create_reader import ROLE as READER, refused
from orion_db import ROOT, load_env, redact, target

ROLE = "orion_desk_mail_writer"
TABLES = ("mail_messages", "mail_links")
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS mail_messages (
    mail_id VARCHAR(16) PRIMARY KEY,
    rfc_message_id VARCHAR(998) NOT NULL,
    replies_to TEXT NOT NULL,
    sender_name VARCHAR(200),
    subject VARCHAR(500),
    body TEXT,
    received_at TIMESTAMP,
    synced_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
)""",
    """CREATE TABLE IF NOT EXISTS mail_links (
    mail_id VARCHAR(16) PRIMARY KEY REFERENCES mail_messages (mail_id),
    ticket_id VARCHAR(64) NOT NULL REFERENCES tickets (ticket_id),
    linked_by VARCHAR(16) NOT NULL CHECK (linked_by IN ('subject', 'thread', 'manual')),
    linked_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
)""",
    "CREATE INDEX IF NOT EXISTS mail_links_ticket ON mail_links (ticket_id)",
)
PROBE = ("INSERT INTO mail_messages (mail_id, rfc_message_id, replies_to, subject) "
         "VALUES ('MLPROBE', '<probe@orion-desk.test>', '', 'probe')")


def main():
    env = load_env()
    if env.get("PG_MAIL_WRITER_USER"):
        sys.exit("PG_MAIL_WRITER_USER is already in .env; nothing changed.")
    password = secrets.token_urlsafe(32)
    database = env["PG_DATABASE"]
    # TiDB Cloud Starter logins carry the instance prefix ("<prefix>.<role>"); current_user shows the bare role.
    login = env["PG_USER"].rsplit(".", 1)[0] + "." + ROLE if "." in env["PG_USER"] else ROLE
    attributes = sql.SQL("LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(
        sql.Literal(password))
    role = sql.Identifier(ROLE)
    statements = [
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), role),
        sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role),
    ]
    for table in TABLES:
        statements += [
            sql.SQL("GRANT SELECT, INSERT ON {} TO {}").format(sql.Identifier(table), role),
            sql.SQL("GRANT SELECT ON {} TO {}").format(sql.Identifier(table), sql.Identifier(READER)),
        ]
    try:
        with target(env) as owner:
            owner.autocommit = True  # This database answers "internal error" to CREATE TABLE inside a transaction.
            for statement in SCHEMA:
                owner.execute(statement)
            # A rerun (say, after a failed check) gives the existing role a new password instead of failing.
            exists = owner.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,)).fetchone()
            owner.execute(sql.SQL("ALTER ROLE {} {}" if exists else "CREATE ROLE {} {}").format(role, attributes))
            for statement in statements:
                owner.execute(statement)
        with target({**env, "PG_USER": login, "PG_PASSWORD": password}) as writer:
            checks = check_writer(writer)
        reader_env = {**env, "PG_USER": env["PG_READONLY_USER"], "PG_PASSWORD": env["PG_READONLY_PASSWORD"]}
        with target(reader_env) as reader:
            checks += check_reader(reader)
    except psycopg.Error as error:
        sys.exit("FAIL " + redact(str(error).replace(password, "<password>"), {**env, "PG_MAIL_WRITER_PASSWORD": password}))
    for name, passed in checks:
        print(("PASS " if passed else "FAIL ") + name)
    if not all(passed for _, passed in checks):
        sys.exit("The role exists but did not pass; .env not changed.")
    path = ROOT / ".env"
    text = path.read_text()
    with path.open("a") as env_file:
        env_file.write(("" if text.endswith("\n") else "\n")
                       + "# The login that may add to the two mail tables and nothing else (tools/create_mail_writer.py)\n"
                       + f"PG_MAIL_WRITER_USER={login}\nPG_MAIL_WRITER_PASSWORD={password}\n")
    print("PASS login saved to .env as PG_MAIL_WRITER_USER and PG_MAIL_WRITER_PASSWORD")


def accepted(connection, *statements):
    """True when every statement runs. Everything is rolled back either way."""
    try:
        with connection.transaction():
            for statement in statements:
                connection.execute(statement)
            raise psycopg.Rollback()
    except psycopg.Error:
        return False
    return True


def check_writer(connection):
    connection.autocommit = True
    role = connection.execute(
        "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user").fetchone()
    denied = psycopg.errors.InsufficientPrivilege
    link = "INSERT INTO mail_links (mail_id, ticket_id, linked_by) VALUES ('MLPROBE', '{}', 'thread')"
    checks = [
        ("no superuser, CREATE DATABASE or CREATE ROLE", role == (False, False, False)),
        ("adds a mail and links it to a ticket", accepted(connection, PROBE, link.format("T00727"))),
        ("a link to a ticket that doesn't exist is refused", refused(connection, PROBE, link.format("T99999"))),
        ("UPDATE on mail_messages refused", refused(connection, PROBE,
            "UPDATE mail_messages SET body = 'changed' WHERE mail_id = 'MLPROBE'", error=denied)),
        ("UPDATE on mail_links refused", refused(connection, PROBE, link.format("T00727"),
            "UPDATE mail_links SET ticket_id = 'T00001' WHERE mail_id = 'MLPROBE'", error=denied)),
        ("DELETE on mail_messages refused", refused(connection, "DELETE FROM mail_messages", error=denied)),
        ("DELETE on mail_links refused", refused(connection, "DELETE FROM mail_links", error=denied)),
        ("CREATE TABLE refused", refused(connection, "CREATE TABLE public.writer_probe (id int)", error=denied)),
    ]
    for table in ("tickets", "messages", "customers", "lab_metadata"):
        checks += [
            (f"SELECT on {table} refused", refused(connection, f"SELECT 1 FROM {table} LIMIT 1", error=denied)),
            (f"DELETE on {table} refused", refused(connection, f"DELETE FROM {table}", error=denied)),
        ]
    return checks


def check_reader(connection):
    connection.autocommit = True
    return [
        ("orion_desk_reader reads both tables", accepted(connection, "SELECT count(*) FROM mail_messages",
                                                         "SELECT count(*) FROM mail_links")),
        ("orion_desk_reader can't write mail_messages, with read-only switched off", refused(connection,
            "SET LOCAL transaction_read_only = off", PROBE, error=psycopg.errors.InsufficientPrivilege)),
    ]


if __name__ == "__main__":
    main()
