"""The customer mailbox: a live check of Gmail over IMAP and SMTP, and a read of the mail under its label.

This module cannot send. SMTP logs in and quits, and there is no method that takes a recipient or a message
(contract C1, C2). The check asks IMAP for STATUS only. `read_new` opens the label read-only and fetches with PEEK, so
nothing is marked as read.
Exception text never leaves here, because a server's answer can repeat what it was sent (C12): a failure becomes one
fixed state word, and only the exception's type is logged.
"""
from datetime import UTC
import email
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
import hashlib
import imaplib
import logging
import re
import smtplib
import ssl
import threading
import time

import certifi

PROVIDER = "Gmail"
IMAP_HOST, IMAP_PORT = "imap.gmail.com", 993
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465
TIMEOUT = 8  # Seconds per socket step. The two checks run in turn, inside the web client's 20 seconds.
CACHE_SECONDS = 60  # One check a minute at most. Google can throttle or lock an account that logs in too often.

SYNC_SECONDS = 60  # One sync a minute at most, for the same reason.
SYNC_BATCH = 25  # New mails per sync, which keeps one sync inside the web client's wait.
LARGEST_MAIL = 2_000_000  # Bytes. Anything bigger is counted as skipped.
BODY_LIMIT, SUBJECT_LIMIT, NAME_LIMIT = 20_000, 500, 200
TICKET_ID = re.compile(r"(?<![A-Za-z0-9])T\d{5}(?![A-Za-z0-9])")  # Exact and case-sensitive, as every ticket lookup is (M01).
MESSAGE_ID = re.compile(r"<[^<>\s]+>")

log = logging.getLogger("orion_api")


def tls_context():
    return ssl.create_default_context(cafile=certifi.where())


def open_imap():
    return imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=tls_context(), timeout=TIMEOUT)


def open_smtp():
    return smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT, context=tls_context())


def quoted(name):
    """imaplib sends a mailbox name as it is given, so a label with a space needs its quotes added here."""
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def counts(lines):
    """`"Label" (MESSAGES 12 UNSEEN 3)` as (12, 3). Only the part after the last bracket, as a label can hold any words."""
    fields = dict(re.findall(rb"(MESSAGES|UNSEEN) (\d+)", lines[-1].rpartition(b"(")[2]))
    return int(fields[b"MESSAGES"]), int(fields[b"UNSEEN"])


def quietly(step):
    """Closing a connection the check has finished with. If that fails, the answer already found still stands."""
    try:
        step()
    except (OSError, imaplib.IMAP4.error, smtplib.SMTPException):
        pass


def failed(check, reason):
    log.warning("mail %s check failed: %s", check, type(reason).__name__)
    return "not_answering"


class MailProblem(Exception):
    """A sync that can't run. `code` is one of the fixed words the route turns into an error."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def clean(text, limit):
    """PostgreSQL refuses NUL in text."""
    return text.replace("\x00", "")[:limit] if text else None


def body_text(message):
    """The plain text part, or the HTML with its tags left in: the desk only ever shows this as text."""
    part = message.get_body(("plain", "html"))
    try:
        return part.get_content() if part is not None else None
    except (LookupError, ValueError):  # A charset Python doesn't know.
        return part.get_payload(decode=True).decode("utf-8", "replace")


def parsed(raw):
    """One raw mail as a row for mail_messages, or None if it has no Message-ID to know it by."""
    message = email.message_from_bytes(raw, policy=policy.default)
    found = MESSAGE_ID.search(str(message["Message-ID"] or ""))
    if found is None:
        return None
    try:
        received = parsedate_to_datetime(str(message["Date"])).astimezone(UTC).replace(tzinfo=None)
    except (TypeError, ValueError):
        received = None
    chain = MESSAGE_ID.findall(f"{message['References'] or ''} {message['In-Reply-To'] or ''}")
    return {"mail_id": "ML" + hashlib.sha256(found[0].encode()).hexdigest()[:12].upper(), "rfc_message_id": found[0],
            "replies_to": " ".join(chain), "sender_name": clean(parseaddr(str(message["From"] or ""))[0], NAME_LIMIT),
            "subject": clean(str(message["Subject"] or ""), SUBJECT_LIMIT), "body": clean(body_text(message), BODY_LIMIT),
            "received_at": received}


def subject_ids(mail):
    return set(TICKET_ID.findall(mail["subject"] or ""))


def new_links(mails, stored, tickets):
    """Links to add, as rows for mail_links. One ticket ID in the subject links a mail. Otherwise a mail takes the ticket
    of the nearest mail it replies to, so a reply with a bare subject still reaches its case. `stored` rows can gain a
    link too, when the mail they answer arrives after them. The sender isn't checked: the desk says so wherever it shows mail.
    """
    ticket_of = {row["rfc_message_id"]: row["ticket_id"] for row in stored}
    links = {}
    for mail in mails:
        ticket_of[mail["rfc_message_id"]] = None
        ids = subject_ids(mail)
        if len(ids) == 1 and ids <= tickets:
            ticket_of[mail["rfc_message_id"]] = next(iter(ids))
            links[mail["mail_id"]] = {"mail_id": mail["mail_id"], "ticket_id": next(iter(ids)), "linked_by": "subject"}
    waiting = [row for row in [*stored, *mails] if ticket_of[row["rfc_message_id"]] is None]
    moved = True
    while moved:  # A chain can arrive in any order, so go round until nothing changes.
        moved = False
        for row in waiting:
            parent = next((ticket_of[name] for name in reversed(row["replies_to"].split()) if ticket_of.get(name)), None)
            if parent and ticket_of[row["rfc_message_id"]] is None:
                ticket_of[row["rfc_message_id"]] = parent
                links[row["mail_id"]] = {"mail_id": row["mail_id"], "ticket_id": parent, "linked_by": "thread"}
                moved = True
    return list(links.values())


class Mailbox:
    def __init__(self, settings, open_imap=open_imap, open_smtp=open_smtp, clock=time.monotonic):
        """Only tests pass their own openers and clock. There is no setting that turns TLS off."""
        self._user = settings.mail_user
        # Google shows an app password in four groups, and it works without the spaces.
        self._password = "".join((settings.mail_app_password or "").split())
        self._label = settings.mail_label
        self._open_imap, self._open_smtp, self._clock = open_imap, open_smtp, clock
        self._lock = threading.Lock()
        self._answer, self._answered = None, None
        self._synced = None

    def status(self):
        """The last answer while it is under a minute old, a failure included, since repeated refused logins are what
        puts the account at risk. Callers who arrive during a check wait for it and share its answer."""
        with self._lock:
            if self._answered is None or self._clock() - self._answered >= CACHE_SECONDS:
                self._answer = self._check()
                self._answered = self._clock()
            return self._answer

    def read_new(self, known):
        """Mails under the label whose Message-ID isn't in `known`, as (rows, skipped, remaining)."""
        with self._lock:
            if self._synced is not None and self._clock() - self._synced < SYNC_SECONDS:
                raise MailProblem("too_soon")
            if not (self._user and self._password and self._label):
                raise MailProblem("not_set_up")
            self._synced = self._clock()
            try:
                client = self._open_imap()
            except (OSError, imaplib.IMAP4.error) as reason:
                failed("imap", reason)
                raise MailProblem("unavailable") from None
            try:
                answer = self._read_label_mail(client, known)
            except (OSError, imaplib.IMAP4.error, UnicodeError, IndexError, TypeError) as reason:
                quietly(client.shutdown)
                failed("imap", reason)
                raise MailProblem("unavailable") from None
            quietly(client.logout)
            return answer

    def reply_address(self, rfc_message_id):
        """The From address of one mail under the label, read-only. The desk stores no address, so this is asked for only
        when a person composes a reply. Raises MailProblem."""
        with self._lock:
            if not (self._user and self._password and self._label):
                raise MailProblem("not_set_up")
            try:
                client = self._open_imap()
            except (OSError, imaplib.IMAP4.error) as reason:
                failed("imap", reason)
                raise MailProblem("unavailable") from None
            try:
                client.login(self._user, self._password)
                if client.select(quoted(self._label), readonly=True)[0] != "OK":
                    raise imaplib.IMAP4.error("no label")
                _, found = client.uid("SEARCH", "HEADER", "Message-ID", quoted(rfc_message_id))
                _, parts = client.uid("FETCH", found[0].split()[0], "(BODY.PEEK[HEADER.FIELDS (FROM)])")
                sender = email.message_from_bytes(parts[0][1], policy=policy.default)["From"]
            except (OSError, imaplib.IMAP4.error, UnicodeError, IndexError, TypeError) as reason:
                quietly(client.shutdown)
                failed("imap", reason)
                raise MailProblem("unavailable") from None
            quietly(client.logout)
            return parseaddr(str(sender or ""))[1]

    def _read_label_mail(self, client, known):
        client.login(self._user, self._password)
        if client.select(quoted(self._label), readonly=True)[0] != "OK":
            raise imaplib.IMAP4.error("no label")
        _, lines = client.uid("FETCH", "1:*", "(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
        waiting, skipped = [], 0
        for line in lines:
            if not isinstance(line, tuple):
                continue
            found = MESSAGE_ID.search(line[1].decode("latin-1"))
            if found is None or int(re.search(rb"RFC822\.SIZE (\d+)", line[0])[1]) > LARGEST_MAIL:
                skipped += 1
            elif found[0] not in known:
                waiting.append(re.search(rb"UID (\d+)", line[0])[1])
        rows = []
        for uid in waiting[:SYNC_BATCH]:
            _, parts = client.uid("FETCH", uid, "(BODY.PEEK[])")
            rows.append(parsed(parts[0][1]))
        return rows, skipped, len(waiting) - len(rows)

    def _check(self):
        imap, messages, unread, smtp = "not_set_up", None, None, "not_set_up"
        if self._user and self._password and self._label:
            imap, messages, unread = self._check_imap()
            smtp = self._check_smtp()
        return {
            "provider": PROVIDER,
            "state": next((state for state in (imap, smtp) if state != "connected"), "connected"),
            "label": self._label,
            "messages": messages,
            "unread": unread,
            "imap": {"address": f"{IMAP_HOST}:{IMAP_PORT}", "state": imap},
            "smtp": {"address": f"{SMTP_HOST}:{SMTP_PORT}", "state": smtp},
        }

    def _check_imap(self):
        try:
            client = self._open_imap()
        except (OSError, imaplib.IMAP4.error) as reason:
            return failed("imap", reason), None, None
        try:
            answer = self._read_label(client)
        except (OSError, imaplib.IMAP4.error, KeyError, AttributeError, IndexError) as reason:
            # No LOGOUT here: on a silent server it would wait out a second timeout.
            quietly(client.shutdown)
            return failed("imap", reason), None, None
        quietly(client.logout)
        return answer

    def _read_label(self, client):
        try:
            client.login(self._user, self._password)
        except imaplib.IMAP4.abort:
            raise
        except (imaplib.IMAP4.error, UnicodeError):
            return "login_refused", None, None
        # imaplib can't encode other labels, and Gmail would need them in modified UTF-7.
        if not (self._label.isascii() and self._label.isprintable()):
            return "label_missing", None, None
        kind, lines = client.status(quoted(self._label), "(MESSAGES UNSEEN)")
        return ("connected", *counts(lines)) if kind == "OK" else ("label_missing", None, None)

    def _check_smtp(self):
        try:
            client = self._open_smtp()
        except (OSError, smtplib.SMTPException) as reason:
            return failed("smtp", reason)
        try:
            # One method, not client.login(): Gmail hangs up after a refusal, and login() would try its next method on
            # the dead connection, so a wrong password would look like a server that isn't answering.
            client.ehlo_or_helo_if_needed()
            client.user, client.password = self._user, self._password
            client.auth("PLAIN", client.auth_plain)
        except (smtplib.SMTPAuthenticationError, UnicodeError):
            quietly(client.close)
            return "login_refused"
        except (OSError, smtplib.SMTPException) as reason:
            quietly(client.close)
            return failed("smtp", reason)
        quietly(client.quit)
        return "connected"
