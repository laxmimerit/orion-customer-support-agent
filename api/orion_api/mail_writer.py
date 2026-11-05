"""The desk's only writes: adding rows to mail_messages, mail_links and mail_actions, as the login made by
tools/create_mail_writer.py.

That login has no UPDATE or DELETE and can reach no other table, so the database itself holds this to adding mail. It is
kept apart from Store, whose sessions stay read-only.
"""
import certifi
import psycopg

ADD_MAIL = """INSERT INTO mail_messages (mail_id, rfc_message_id, replies_to, sender_name, subject, body, received_at)
VALUES (%(mail_id)s, %(rfc_message_id)s, %(replies_to)s, %(sender_name)s, %(subject)s, %(body)s, %(received_at)s)
ON CONFLICT (mail_id) DO NOTHING"""
ADD_LINK = """INSERT INTO mail_links (mail_id, ticket_id, linked_by) VALUES (%(mail_id)s, %(ticket_id)s, %(linked_by)s)
ON CONFLICT (mail_id) DO NOTHING"""
# The primary key is (draft_id, action), so the second approval or send of a draft adds nothing.
ADD_ACTION = """INSERT INTO mail_actions (draft_id, action, ticket_id, actor, details)
VALUES (%(draft_id)s, %(action)s, %(ticket_id)s, %(actor)s, %(details)s)
ON CONFLICT (draft_id, action) DO NOTHING"""


class MailWriter:
    def __init__(self, settings):
        self.settings = settings

    @property
    def configured(self):
        return bool(self.settings.mail_writer_user and self.settings.mail_writer_password)

    def connect(self):
        settings = self.settings
        return psycopg.connect(host=settings.pg_host, port=settings.pg_port, user=settings.mail_writer_user,
                               password=settings.mail_writer_password, dbname=settings.pg_database, sslmode="verify-full",
                               sslrootcert=settings.pg_ssl_root_cert or certifi.where(), connect_timeout=10,
                               options="-c TimeZone=UTC")

    def add_action(self, row):
        """True if the row went in, False if this draft already has this action."""
        with self.connect() as db, db.cursor() as cursor:
            cursor.execute(ADD_ACTION, row)
            return cursor.rowcount == 1

    def save(self, mails, links):
        """One transaction, so a mail and its link land together."""
        with self.connect() as db, db.cursor() as cursor:
            if mails:
                cursor.executemany(ADD_MAIL, mails)
            if links:
                cursor.executemany(ADD_LINK, links)
