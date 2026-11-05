"""The customer mailbox check against the real Gmail account. Skipped without the ORION_MAIL_* settings.

It logs in and reads the label's counts twice, through two mailboxes because one would answer the second call from its
cache. It sends nothing and opens no message, so the counts must not move.
"""
import json

import pytest

from orion_api.mail import Mailbox
from orion_api.settings import load_settings

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def settings():
    try:
        settings = load_settings()
    except RuntimeError as reason:
        pytest.skip(str(reason))
    if not (settings.mail_user and settings.mail_app_password and settings.mail_label):
        pytest.skip("The ORION_MAIL_* settings are not all set.")
    return settings


def test_the_check_is_connected_and_marks_nothing_as_read(settings):
    first, second = Mailbox(settings).status(), Mailbox(settings).status()
    assert first["state"] == "connected"
    assert second["state"] == "connected"
    assert (first["messages"], first["unread"]) == (second["messages"], second["unread"])
    secrets = {"address": settings.mail_user, "password": settings.mail_app_password,
               "password without spaces": "".join(settings.mail_app_password.split())}
    for result in (first, second):
        assert [name for name, secret in secrets.items() if secret in json.dumps(result)] == []
