"""The customer mailbox check, through the route and on the wire. fake_mail stands in for Gmail on 127.0.0.1, so no
network and no secret is needed."""
import dataclasses
import imaplib
import inspect
import logging
import re
import smtplib
import socket
import ssl
import threading

from fastapi.testclient import TestClient
import pytest

from orion_api import mail
from orion_api.main import create_app
from orion_api.settings import OPTIONAL, REQUIRED, load_settings

from .conftest import AGENT, SETTINGS, auth
from .fake_mail import FakeMail

LABEL = "Orion Desk"
USER = "desk.inbox@example.com"
TYPED_PASSWORD = "abcd efgh ijkl mnop"  # Made up, in the four groups Google shows.
PASSWORD = "abcdefghijklmnop"  # What the server expects once the spaces are gone.
MAIL_SETTINGS = dataclasses.replace(SETTINGS, mail_user=USER, mail_app_password=TYPED_PASSWORD, mail_label=LABEL)
SECRETS = {"address": USER, "typed password": TYPED_PASSWORD, "password": PASSWORD}
DEFAULTS = {"user": USER, "password": PASSWORD, "labels": {LABEL: (12, 3)}}
FIELD_NAMES = {"user": "mail_user", "password": "mail_app_password", "label": "mail_label"}
FIELD_VALUES = {"user": USER, "password": TYPED_PASSWORD, "label": LABEL}
BASE_ENV = "PG_HOST=h\nPG_USER=u\nPG_PASSWORD=p\nPG_DATABASE=d\nORION_AGENT_TOKEN=a\nORION_ADMIN_TOKEN=b\n"

# Each case: the changes to the fake, the state, the IMAP and SMTP states, and the counts the body shows.
CASES = [
    pytest.param({}, "connected", "connected", "connected", (12, 3), id="connected"),
    pytest.param({"imap": "refuse"}, "login_refused", "login_refused", "connected", (None, None),
                 id="imap-login-refused"),
    pytest.param({"smtp": "refuse"}, "login_refused", "connected", "login_refused", (12, 3),
                 id="smtp-login-refused"),
    pytest.param({"labels": {}}, "label_missing", "label_missing", "connected", (None, None), id="label-missing"),
    pytest.param({"imap": "down"}, "not_answering", "not_answering", "connected", (None, None), id="imap-down"),
    pytest.param({"smtp": "down"}, "not_answering", "connected", "not_answering", (12, 3), id="smtp-down"),
    pytest.param({"imap": "hang", "timeout": 0.5}, "not_answering", "not_answering", "connected", (None, None),
                 id="imap-hangs"),
    pytest.param({"smtp": "hang", "timeout": 0.5}, "not_answering", "connected", "not_answering", (12, 3),
                 id="smtp-hangs"),
    pytest.param({"imap": "down", "smtp": "refuse"}, "not_answering", "not_answering", "login_refused", (None, None),
                 id="imap-first-when-both-fail"),
    pytest.param({"imap": "refuse", "smtp": "down"}, "login_refused", "login_refused", "not_answering", (None, None),
                 id="imap-refused-before-smtp-down"),
]


def expected(state, imap, smtp, counts=(None, None), label=LABEL):
    messages, unread = counts
    return {"provider": "Gmail", "state": state, "label": label, "messages": messages, "unread": unread,
            "imap": {"address": "imap.gmail.com:993", "state": imap},
            "smtp": {"address": "smtp.gmail.com:465", "state": smtp}}


def mailbox_for(fake, settings=MAIL_SETTINGS):
    return mail.Mailbox(settings, open_imap=fake.open_imap, open_smtp=fake.open_smtp)


def refuse_to_open():
    raise AssertionError("a connection was opened")


@pytest.fixture
def fake_gmail():
    started = []

    def start(**options):
        fake = FakeMail(**options).start()
        started.append(fake)
        return fake

    yield start
    for fake in started:
        fake.stop()


@pytest.fixture
def status_of(fake_store, fake_embedder, fake_assistant):
    def get(box, settings=MAIL_SETTINGS):
        app = create_app(settings, fake_store, fake_embedder, fake_assistant, box)
        with TestClient(app, raise_server_exceptions=False) as client:
            return client.get("/api/mail/status", headers=auth(AGENT))
    return get


@pytest.fixture
def clean_env(monkeypatch):
    for key in (*REQUIRED, *OPTIONAL):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("changes, state, imap, smtp, counts", CASES)
def test_each_check_answers_its_state_and_counts(status_of, fake_gmail, changes, state, imap, smtp, counts):
    response = status_of(mailbox_for(fake_gmail(**{**DEFAULTS, **changes})))
    assert response.status_code == 200
    assert response.json() == expected(state, imap, smtp, counts)


def test_a_label_with_a_space_goes_out_quoted(fake_gmail):
    fake = fake_gmail(**DEFAULTS)
    assert mailbox_for(fake).status()["state"] == "connected"
    assert fake.status_arguments == ['"Orion Desk"']


@pytest.mark.parametrize("label, wire", [
    ('Say "hi" \\ there', r'"Say \"hi\" \\ there"'),
    ("Back\\slash", r'"Back\\slash"'),
])
def test_quotes_and_backslashes_in_a_label_are_escaped(fake_gmail, label, wire):
    fake = fake_gmail(user=USER, password=PASSWORD, labels={label: (5, 2)})
    body = mailbox_for(fake, dataclasses.replace(MAIL_SETTINGS, mail_label=label)).status()
    assert fake.status_arguments == [wire]
    assert (body["state"], body["messages"], body["unread"]) == ("connected", 5, 2)


@pytest.mark.parametrize("label", ["MESSAGES 3 UNSEEN 9", "Team (EMEA) UNSEEN 1"])
def test_count_words_in_a_label_do_not_change_the_counts(status_of, fake_gmail, label):
    fake = fake_gmail(user=USER, password=PASSWORD, labels={label: (12, 3)})
    response = status_of(mailbox_for(fake, dataclasses.replace(MAIL_SETTINGS, mail_label=label)),
                         dataclasses.replace(MAIL_SETTINGS, mail_label=label))
    assert response.json() == expected("connected", "connected", "connected", (12, 3), label=label)


def test_spaces_in_the_app_password_are_removed_before_login(fake_gmail):
    assert mailbox_for(fake_gmail(**DEFAULTS)).status()["state"] == "connected"


def test_the_server_refuses_the_password_with_its_spaces(fake_gmail):
    fake = fake_gmail(user=USER, password=TYPED_PASSWORD, labels={LABEL: (12, 3)})
    assert mailbox_for(fake).status()["state"] == "login_refused"


def test_a_connected_check_sends_exactly_the_checks(fake_gmail):
    fake = fake_gmail(**DEFAULTS)
    mailbox_for(fake).status()
    # Python 3.14's imaplib asks for CAPABILITY again after LOGIN, so that repeat is left out of the comparison.
    assert fake.verbs["imap"][0] == "CAPABILITY"
    assert [verb for verb in fake.verbs["imap"][1:] if verb != "CAPABILITY"] == ["LOGIN", "STATUS", "LOGOUT"]
    assert fake.verbs["smtp"] == ["EHLO", "AUTH", "QUIT"]


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


def logins(fake):
    return fake.verbs["imap"].count("LOGIN"), fake.verbs["smtp"].count("AUTH")


def test_a_second_call_inside_a_minute_logs_in_to_nothing(fake_gmail):
    fake, clock = fake_gmail(**DEFAULTS), Clock()
    box = mail.Mailbox(MAIL_SETTINGS, open_imap=fake.open_imap, open_smtp=fake.open_smtp, clock=clock)
    first = box.status()
    clock.now += mail.CACHE_SECONDS - 1
    assert box.status() == first
    assert logins(fake) == (1, 1)


def test_the_check_runs_again_after_a_minute(fake_gmail):
    fake, clock = fake_gmail(**DEFAULTS), Clock()
    box = mail.Mailbox(MAIL_SETTINGS, open_imap=fake.open_imap, open_smtp=fake.open_smtp, clock=clock)
    box.status()
    clock.now += mail.CACHE_SECONDS
    box.status()
    assert logins(fake) == (2, 2)


def test_a_refused_login_is_held_too_so_the_account_is_not_hammered(fake_gmail):
    fake = fake_gmail(**{**DEFAULTS, "imap": "refuse", "smtp": "refuse"})
    box = mailbox_for(fake)
    for _ in range(5):
        assert box.status()["state"] == "login_refused"
    assert logins(fake) == (1, 1)


def test_callers_at_the_same_moment_share_one_check(fake_gmail):
    fake = fake_gmail(**DEFAULTS)
    box = mailbox_for(fake)
    answers, gate = [], threading.Barrier(8)

    def ask():
        gate.wait()
        answers.append(box.status()["state"])

    callers = [threading.Thread(target=ask) for _ in range(8)]
    for caller in callers:
        caller.start()
    for caller in callers:
        caller.join()
    assert answers == ["connected"] * 8
    assert logins(fake) == (1, 1)


def test_repeated_route_calls_log_in_once(fake_gmail, fake_store, fake_embedder, fake_assistant):
    fake = fake_gmail(**DEFAULTS)
    app = create_app(MAIL_SETTINGS, fake_store, fake_embedder, fake_assistant, mailbox_for(fake))
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(3):
            assert client.get("/api/mail/status", headers=auth(AGENT)).status_code == 200
    assert logins(fake) == (1, 1)


def test_a_refused_smtp_login_is_refused_even_though_gmail_hangs_up(fake_gmail):
    fake = fake_gmail(**{**DEFAULTS, "smtp": "refuse"})
    status = mailbox_for(fake).status()
    assert status["smtp"]["state"] == "login_refused"
    assert fake.verbs["smtp"] == ["EHLO", "AUTH"]


def test_a_label_imaplib_cannot_encode_is_never_sent(fake_gmail):
    fake = fake_gmail(**DEFAULTS)
    settings = dataclasses.replace(MAIL_SETTINGS, mail_label="Réclamations")
    assert mailbox_for(fake, settings).status()["imap"]["state"] == "label_missing"
    assert "STATUS" not in fake.verbs["imap"]


@pytest.mark.parametrize("changes, state, imap, smtp, counts", CASES)
def test_the_wire_carries_only_the_checks(fake_gmail, changes, state, imap, smtp, counts):
    fake = fake_gmail(**{**DEFAULTS, **changes})
    mailbox_for(fake).status()
    assert set(fake.verbs["imap"]) <= {"CAPABILITY", "LOGIN", "STATUS", "LOGOUT"}
    assert set(fake.verbs["smtp"]) <= {"EHLO", "AUTH", "QUIT"}


@pytest.mark.parametrize("changes, state, imap, smtp, counts", CASES)
def test_no_secret_reaches_the_body_the_log_or_a_repr(status_of, fake_gmail, caplog, changes, state, imap, smtp,
                                                       counts):
    caplog.set_level(logging.DEBUG)
    box = mailbox_for(fake_gmail(**{**DEFAULTS, **changes}))
    response = status_of(box)
    texts = {"body": response.text, "log": caplog.text, "settings": repr(MAIL_SETTINGS), "mailbox": repr(box)}
    assert [(where, name) for where, text in texts.items() for name, secret in SECRETS.items() if secret in text] == []


@pytest.mark.parametrize("changes, message", [
    ({"imap": "down"}, "mail imap check failed: ConnectionRefusedError"),
    ({"smtp": "down"}, "mail smtp check failed: ConnectionRefusedError"),
    ({"imap": "hang", "timeout": 0.5}, "mail imap check failed: TimeoutError"),
])
def test_a_failed_check_logs_only_its_exception_type(fake_gmail, caplog, changes, message):
    caplog.set_level(logging.WARNING)
    mailbox_for(fake_gmail(**{**DEFAULTS, **changes})).status()
    assert [record.getMessage() for record in caplog.records if record.name == "orion_api"] == [message]


@pytest.mark.parametrize("present", [(), ("user",), ("password",), ("label",), ("user", "password"),
                                     ("user", "label"), ("password", "label")])
def test_partial_mail_settings_open_no_connection(present):
    settings = dataclasses.replace(SETTINGS, **{FIELD_NAMES[name]: FIELD_VALUES[name] for name in present})
    box = mail.Mailbox(settings, open_imap=refuse_to_open, open_smtp=refuse_to_open)
    assert box.status() == expected("not_set_up", "not_set_up", "not_set_up",
                                    label=LABEL if "label" in present else None)


def test_a_blank_app_password_is_not_set_up():
    settings = dataclasses.replace(MAIL_SETTINGS, mail_app_password="    ")
    box = mail.Mailbox(settings, open_imap=refuse_to_open, open_smtp=refuse_to_open)
    assert box.status()["state"] == "not_set_up"


def test_without_mail_settings_the_route_says_not_set_up(client, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("the test opened a network connection")

    monkeypatch.setattr(socket, "create_connection", no_network)
    response = client.get("/api/mail/status", headers=auth(AGENT))
    assert response.status_code == 200
    assert response.json() == expected("not_set_up", "not_set_up", "not_set_up", label=None)


def test_tls_context_requires_a_verified_certificate_for_the_host():
    context = mail.tls_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_gmail_is_reached_on_the_tls_ports():
    assert (mail.IMAP_PORT, mail.SMTP_PORT) == (993, 465)


def test_the_default_openers_connect_over_tls_to_gmail(monkeypatch):
    calls = []

    class Refused:
        def __init__(self, host, port, **options):
            calls.append((host, port, options))
            raise ConnectionRefusedError

    monkeypatch.setattr(imaplib, "IMAP4_SSL", Refused)
    monkeypatch.setattr(smtplib, "SMTP_SSL", Refused)
    body = mail.Mailbox(MAIL_SETTINGS).status()
    assert (body["imap"]["state"], body["smtp"]["state"]) == ("not_answering", "not_answering")
    (imap_host, imap_port, imap_options), (smtp_host, smtp_port, smtp_options) = calls
    assert (imap_host, imap_port, smtp_host, smtp_port) == ("imap.gmail.com", 993, "smtp.gmail.com", 465)
    assert imap_options["ssl_context"].verify_mode == ssl.CERT_REQUIRED
    assert smtp_options["context"].check_hostname is True


def test_mailbox_has_one_public_method():
    public = [name for name, _ in inspect.getmembers(mail.Mailbox, inspect.isfunction) if not name.startswith("_")]
    assert public == ["status"]


def test_the_module_source_never_sends_or_names_a_mail_command():
    assert re.search(r"sendmail|send_message|\.send\(|\bMAIL\b|\bRCPT\b|\bDATA\b", inspect.getsource(mail)) is None


def test_load_settings_reads_the_mail_keys_from_the_env_file(tmp_path, clean_env):
    env = tmp_path / ".env"
    env.write_text(BASE_ENV + f"ORION_MAIL_USER={USER}\nORION_MAIL_APP_PASSWORD={TYPED_PASSWORD}\nORION_MAIL_LABEL={LABEL}\n")
    settings = load_settings(env)
    assert (settings.mail_user, settings.mail_app_password, settings.mail_label) == (USER, TYPED_PASSWORD, LABEL)


def test_the_environment_wins_over_the_env_file(tmp_path, monkeypatch, clean_env):
    env = tmp_path / ".env"
    env.write_text(BASE_ENV + f"ORION_MAIL_USER={USER}\nORION_MAIL_LABEL=From the file\n")
    monkeypatch.setenv("ORION_MAIL_LABEL", LABEL)
    settings = load_settings(env)
    assert (settings.mail_user, settings.mail_label) == (USER, LABEL)


def test_the_mail_keys_stay_optional(tmp_path, clean_env):
    env = tmp_path / ".env"
    env.write_text(BASE_ENV)
    settings = load_settings(env)
    assert (settings.mail_user, settings.mail_app_password, settings.mail_label) == (None, None, None)
