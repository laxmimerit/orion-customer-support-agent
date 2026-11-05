"""The customer mailbox: one live check of Gmail over IMAP and SMTP, and nothing more.

This module cannot send. SMTP logs in and quits, and there is no method that takes a recipient or a message
(contract C1, C2). IMAP asks for STATUS only, which doesn't open the mailbox, so no message is read or marked as read.
Exception text never leaves here, because a server's answer can repeat what it was sent (C12): a failure becomes one
fixed state word, and only the exception's type is logged.
"""
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

    def status(self):
        """The last answer while it is under a minute old, a failure included, since repeated refused logins are what
        puts the account at risk. Callers who arrive during a check wait for it and share its answer."""
        with self._lock:
            if self._answered is None or self._clock() - self._answered >= CACHE_SECONDS:
                self._answer = self._check()
                self._answered = self._clock()
            return self._answer

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
