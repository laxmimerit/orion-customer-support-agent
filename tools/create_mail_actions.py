# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]==3.2.10", "certifi>=2025.1.31"]
# ///
"""Create mail_actions, the log behind Compose, Approve, Send and the case page's Action history.

Connects with the owner login (PG_USER). The mail writer login gets SELECT and INSERT and nothing else, so a draft, an
approval or a send can't be changed or removed once written. orion_desk_reader gets SELECT. The primary key is
(draft_id, action), so a draft can be approved once and handed to SMTP once, whoever presses the button twice.

Then it logs in as the writer and checks what works and what must be refused, with every write rolled back.

    uv run tools/create_mail_actions.py
"""
import sys

import psycopg
from psycopg import sql

from create_mail_writer import ROLE, accepted
from create_reader import ROLE as READER, refused
from orion_db import load_env, redact, target

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS mail_actions (
    draft_id VARCHAR(16) NOT NULL,
    action VARCHAR(16) NOT NULL CHECK (action IN ('drafted', 'approved', 'sending', 'sent', 'failed')),
    ticket_id VARCHAR(64) NOT NULL REFERENCES tickets (ticket_id),
    actor VARCHAR(100) NOT NULL,
    details TEXT,
    acted_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    PRIMARY KEY (draft_id, action)
)""",
    "CREATE INDEX IF NOT EXISTS mail_actions_ticket ON mail_actions (ticket_id)",
)
PROBE = "INSERT INTO mail_actions (draft_id, action, ticket_id, actor) VALUES ('DRPROBE', 'drafted', 'T00727', 'probe')"


def main():
    env = load_env()
    if not env.get("PG_MAIL_WRITER_USER"):
        sys.exit("Run tools/create_mail_writer.py first.")
    try:
        with target(env) as owner:
            owner.autocommit = True  # This database answers "internal error" to CREATE TABLE inside a transaction.
            for statement in SCHEMA:
                owner.execute(statement)
            owner.execute(sql.SQL("GRANT SELECT, INSERT ON mail_actions TO {}").format(sql.Identifier(ROLE)))
            owner.execute(sql.SQL("GRANT SELECT ON mail_actions TO {}").format(sql.Identifier(READER)))
        with target({**env, "PG_USER": env["PG_MAIL_WRITER_USER"], "PG_PASSWORD": env["PG_MAIL_WRITER_PASSWORD"]}) as writer:
            writer.autocommit = True
            denied = psycopg.errors.InsufficientPrivilege
            checks = [
                ("adds an action", accepted(writer, PROBE)),
                ("the same action twice on one draft is refused", refused(writer, PROBE, PROBE)),
                ("UPDATE refused", refused(writer, PROBE, "UPDATE mail_actions SET actor = 'x'", error=denied)),
                ("DELETE refused", refused(writer, "DELETE FROM mail_actions", error=denied)),
            ]
        with target({**env, "PG_USER": env["PG_READONLY_USER"], "PG_PASSWORD": env["PG_READONLY_PASSWORD"]}) as reader:
            reader.autocommit = True
            checks.append(("orion_desk_reader reads it", accepted(reader, "SELECT count(*) FROM mail_actions")))
    except psycopg.Error as error:
        sys.exit("FAIL " + redact(str(error), env))
    for name, passed in checks:
        print(("PASS " if passed else "FAIL ") + name)
    if not all(passed for _, passed in checks):
        sys.exit("mail_actions exists but did not pass.")


if __name__ == "__main__":
    main()
