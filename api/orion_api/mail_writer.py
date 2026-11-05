"""The desk's only writes: adding rows to mail_messages and mail_links, as the login made by tools/create_mail_writer.py.

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


class MailWriter:
    def __init__(self, settings):
        self.settings = settings

    @property
    def configured(self):
        return bool(self.settings.mail_writer_user and self.settings.mail_writer_password)

    def save(self, mails, links):
        """One transaction, so a mail and its link land together."""
        settings = self.settings
        with psycopg.connect(host=settings.pg_host, port=settings.pg_port, user=settings.mail_writer_user,
                             password=settings.mail_writer_password, dbname=settings.pg_database, sslmode="verify-full",
                             sslrootcert=settings.pg_ssl_root_cert or certifi.where(), connect_timeout=10,
                             options="-c TimeZone=UTC") as db, db.cursor() as cursor:
            if mails:
                cursor.executemany(ADD_MAIL, mails)
            if links:
                cursor.executemany(ADD_LINK, links)
