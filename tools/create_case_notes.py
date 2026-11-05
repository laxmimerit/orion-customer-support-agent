# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]==3.2.10", "certifi>=2025.1.31"]
# ///
"""Create case_notes, and let a person link a mail by hand.

Connects with the owner login (PG_USER). case_notes holds internal notes; a row with `handed_to` is a handoff. The mail
writer login gets SELECT and INSERT and nothing else, so a note can't be changed or removed. orion_desk_reader gets
SELECT. mail_links.linked_by also accepts 'manual'.

Then it logs in as the writer and checks what works and what must be refused, with every write rolled back.

    uv run tools/create_case_notes.py
"""
import sys

import psycopg
from psycopg import sql

from create_mail_writer import PROBE, ROLE, accepted
from create_reader import ROLE as READER, refused
from orion_db import load_env, redact, target

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS case_notes (
    note_id VARCHAR(16) PRIMARY KEY,
    ticket_id VARCHAR(64) NOT NULL REFERENCES tickets (ticket_id),
    author VARCHAR(100) NOT NULL,
    handed_to VARCHAR(100),
    body TEXT NOT NULL,
    noted_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
)""",
    "CREATE INDEX IF NOT EXISTS case_notes_ticket ON case_notes (ticket_id)",
    "ALTER TABLE mail_links DROP CONSTRAINT IF EXISTS mail_links_linked_by_check",
    "ALTER TABLE mail_links ADD CONSTRAINT mail_links_linked_by_check CHECK (linked_by IN ('subject', 'thread', 'manual'))",
)
NOTE = "INSERT INTO case_notes (note_id, ticket_id, author, body) VALUES ('NTPROBE', '{}', 'probe', 'probe')"
LINK = "INSERT INTO mail_links (mail_id, ticket_id, linked_by) VALUES ('MLPROBE', 'T00727', '{}')"


def main():
    env = load_env()
    try:
        with target(env) as owner:
            owner.autocommit = True  # This database answers "internal error" to CREATE TABLE inside a transaction.
            for statement in SCHEMA:
                owner.execute(statement)
            owner.execute(sql.SQL("GRANT SELECT, INSERT ON case_notes TO {}").format(sql.Identifier(ROLE)))
            owner.execute(sql.SQL("GRANT SELECT ON case_notes TO {}").format(sql.Identifier(READER)))
        denied = psycopg.errors.InsufficientPrivilege
        with target({**env, "PG_USER": env["PG_MAIL_WRITER_USER"], "PG_PASSWORD": env["PG_MAIL_WRITER_PASSWORD"]}) as writer:
            writer.autocommit = True
            checks = [
                ("adds a note", accepted(writer, NOTE.format("T00727"))),
                ("links a mail by hand", accepted(writer, PROBE, LINK.format("manual"))),
                ("an unknown linked_by is refused", refused(writer, PROBE, LINK.format("guess"))),
                ("a note on a ticket that doesn't exist is refused", refused(writer, NOTE.format("T99999"))),
                ("UPDATE on case_notes refused", refused(writer, "UPDATE case_notes SET body = 'changed'", error=denied)),
                ("DELETE on case_notes refused", refused(writer, "DELETE FROM case_notes", error=denied)),
            ]
        with target({**env, "PG_USER": env["PG_READONLY_USER"], "PG_PASSWORD": env["PG_READONLY_PASSWORD"]}) as reader:
            reader.autocommit = True
            checks.append(("orion_desk_reader reads case_notes", accepted(reader, "SELECT count(*) FROM case_notes")))
    except psycopg.Error as error:
        sys.exit("FAIL " + redact(str(error), env))
    for name, passed in checks:
        print(("PASS " if passed else "FAIL ") + name)
    if not all(passed for _, passed in checks):
        sys.exit("A check did not pass.")


if __name__ == "__main__":
    main()
