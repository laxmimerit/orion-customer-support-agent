"""The desk's only way to send: one approved reply over SMTP, and only to the desk's own mailbox or a plus form of it.

Kept apart from mail.py, which still cannot send. Nothing calls this but POST /api/drafts/{draft_id}/send, which a person
presses after a named person approved the exact text. There is no timer and no retry. The recipient rule is checked
here, at the last step, whatever the draft says, and the envelope names that one address, so there is no CC or BCC.
"""
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import re
import smtplib

from .mail import MailProblem, failed, open_smtp, quietly


def desk_address(address, own):
    """True for `own` or `own` with a +tag. ASCII, so a look-alike letter can't match under IGNORECASE."""
    if not address or not own or "@" not in own:
        return False
    local, _, domain = own.partition("@")
    return re.fullmatch(rf"{re.escape(local)}(\+[A-Za-z0-9._-]+)?@{re.escape(domain)}", address,
                        re.IGNORECASE | re.ASCII) is not None


class MailSender:
    def __init__(self, settings, open_smtp=open_smtp):
        self._user = settings.mail_user
        self._password = "".join((settings.mail_app_password or "").split())
        self._open_smtp = open_smtp

    def allowed(self, address):
        return desk_address(address, self._user)

    def send(self, draft):
        """Hand one draft to SMTP and return its Message-ID, or raise MailProblem. A failure is never retried: SMTP can
        fail after the server took the mail, so a second try could send it twice."""
        if not (self._user and self._password):
            raise MailProblem("not_set_up")
        if not self.allowed(draft["recipient"]):
            raise MailProblem("recipient_not_allowed")
        message = EmailMessage()
        message["From"] = self._user
        message["To"] = draft["recipient"]
        message["Subject"] = draft["subject"]
        message["Date"] = formatdate(usegmt=True)
        message["Message-ID"] = make_msgid(domain=self._user.partition("@")[2])
        message["In-Reply-To"] = draft["in_reply_to"]
        message["References"] = draft["references"]
        message.set_content(draft["body"], cte="quoted-printable")
        try:
            client = self._open_smtp()
        except (OSError, smtplib.SMTPException) as reason:
            failed("smtp", reason)
            raise MailProblem("unavailable") from None
        try:
            # As in Mailbox._check_smtp: one method, because Gmail hangs up after a refusal.
            client.ehlo_or_helo_if_needed()
            client.user, client.password = self._user, self._password
            client.auth("PLAIN", client.auth_plain)
            client.send_message(message, from_addr=self._user, to_addrs=[draft["recipient"]])
        except (OSError, UnicodeError, smtplib.SMTPException) as reason:
            quietly(client.close)
            failed("smtp", reason)
            raise MailProblem("unavailable") from None
        quietly(client.quit)
        return message["Message-ID"]
