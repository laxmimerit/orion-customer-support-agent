# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]==3.2.10", "certifi>=2025.1.31"]
# ///
"""Create the read-only orion_desk login the deployed API uses.

Connects with the owner login (PG_USER) from .env and creates a role that can
log in, read every table in orion_desk's public schema and do nothing else:
no superuser, no CREATE anywhere, and read-only transactions by default.
It then logs in as the new role and checks that a read works and that INSERT
and CREATE TABLE are refused. Only after that are PG_READONLY_USER and
PG_READONLY_PASSWORD appended to .env. Nothing is printed except PASS/FAIL.

    uv run tools/create_reader.py

Tables added later need their own GRANT SELECT; nothing is granted by default.
"""
import secrets
import sys

import psycopg
from psycopg import sql

from orion_db import ROOT, load_env, redact, target

ROLE = "orion_desk_reader"


def main():
    env = load_env()
    if env.get("PG_READONLY_USER"):
        sys.exit("PG_READONLY_USER is already in .env; nothing changed.")
    password = secrets.token_urlsafe(32)
    database = env["PG_DATABASE"]
    # TiDB Cloud Starter logins carry the instance prefix ("<prefix>.<role>"); current_user shows the bare role.
    login = env["PG_USER"].rsplit(".", 1)[0] + "." + ROLE if "." in env["PG_USER"] else ROLE
    attributes = sql.SQL("LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(
        sql.Literal(password))
    statements = [
        sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(sql.Identifier(ROLE)),
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(ROLE)),
        sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(ROLE)),
        sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(ROLE)),
    ]
    secret = {**env, "PG_READONLY_PASSWORD": password}
    try:
        with target(env) as owner:
            # A rerun (say, after a failed check) gives the existing role a new password instead of failing.
            exists = owner.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,)).fetchone()
            owner.execute(sql.SQL("ALTER ROLE {} {}" if exists else "CREATE ROLE {} {}").format(
                sql.Identifier(ROLE), attributes))
            for statement in statements:
                owner.execute(statement)
        reader_env = {**env, "PG_USER": login, "PG_PASSWORD": password}
        with target(reader_env) as reader:
            checks = check_reader(reader)
    except psycopg.Error as error:
        sys.exit("FAIL " + redact(str(error).replace(password, "<password>"), secret))
    for name, passed in checks:
        print(("PASS " if passed else "FAIL ") + name)
    if not all(passed for _, passed in checks):
        sys.exit("The role exists but did not pass; .env not changed.")
    path = ROOT / ".env"
    text = path.read_text()
    with path.open("a") as env_file:
        env_file.write(("" if text.endswith("\n") else "\n")
                       + "# Read-only orion_desk login for the deployment (tools/create_reader.py)\n"
                       + f"PG_READONLY_USER={login}\nPG_READONLY_PASSWORD={password}\n")
    print("PASS login saved to .env as PG_READONLY_USER and PG_READONLY_PASSWORD")


def refused(connection, *statements, error=psycopg.Error):
    """True when the last statement fails with `error`. Everything is rolled back either way."""
    outcome = False
    try:
        with connection.transaction():
            for statement in statements[:-1]:
                connection.execute(statement)
            try:
                connection.execute(statements[-1])
            except error:
                outcome = True
            raise psycopg.Rollback()
    except psycopg.Error:
        return False
    return outcome


def check_reader(connection):
    connection.autocommit = True
    role = connection.execute(
        "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user").fetchone()
    tickets = connection.execute("SELECT count(*) FROM tickets").fetchone()[0]
    return [
        ("no superuser, CREATE DATABASE or CREATE ROLE", role == (False, False, False)),
        ("reads tickets", tickets > 0),
        ("sessions start read-only", connection.execute("SHOW default_transaction_read_only").fetchone()[0] == "on"),
        ("INSERT refused", refused(connection, "INSERT INTO lab_metadata SELECT * FROM lab_metadata")),
        # The session default is only a default; the grants must refuse the write on their own.
        ("INSERT refused for lack of privilege, with read-only switched off", refused(connection,
            "SET LOCAL transaction_read_only = off", "INSERT INTO lab_metadata SELECT * FROM lab_metadata",
            error=psycopg.errors.InsufficientPrivilege)),
        ("CREATE TABLE refused for lack of privilege, with read-only switched off", refused(connection,
            "SET LOCAL transaction_read_only = off", "CREATE TABLE public.reader_probe (id int)",
            error=psycopg.errors.InsufficientPrivilege)),
    ]


if __name__ == "__main__":
    main()
