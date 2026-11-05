"""A fake Gmail on 127.0.0.1 for test_mail.py: IMAP and SMTP on plain sockets, on random ports.

The real imaplib and smtplib code runs against it, so label quoting and reply parsing are tested on the wire. Nothing is
encrypted and nothing leaves the machine. The fake keeps the verb of every command and, for STATUS, the raw mailbox
argument. It never keeps a password, a message or an address beyond the one it was given to check against.
"""
import base64
import imaplib
import smtplib
import socket
import socketserver
import threading

HOST = "127.0.0.1"
MODES = ("ok", "refuse", "hang", "down")


def unused_port():
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def arguments(text):
    """Atoms and quoted strings as (raw, value) pairs. A quoted value keeps its escapes in raw."""
    found, i = [], 0
    while i < len(text):
        if text[i] == " ":
            i += 1
        elif text[i] == '"':
            j, chars = i + 1, []
            while j < len(text) and text[j] != '"':
                if text[j] == "\\" and j + 1 < len(text):
                    j += 1
                chars.append(text[j])
                j += 1
            if j >= len(text):
                raise ValueError("unclosed quote")
            found.append((text[i:j + 1], "".join(chars)))
            i = j + 1
        else:
            j = text.find(" ", i)
            j = len(text) if j < 0 else j
            found.append((text[i:j], text[i:j]))
            i = j
    return found


class _Session(socketserver.StreamRequestHandler):
    timeout = 5  # A client that goes silent is cut off after this many seconds, so no session outlives the test.
    protocol = greeting = None

    def handle(self):
        fake = self.server.fake
        if fake.modes[self.protocol] == "hang":
            fake.stopping.wait()
            return
        self.reply(self.greeting)
        while True:
            try:
                line = self.rfile.readline()
            except OSError:
                return
            if not line or not self.command(line.rstrip(b"\r\n").decode("latin-1")):
                return

    def reply(self, *lines):
        for line in lines:
            self.wfile.write(line.encode("latin-1") + b"\r\n")
        return True


class _Imap(_Session):
    protocol = "imap"
    greeting = "* OK Fake Gmail IMAP ready."
    logged_in = False

    def command(self, line):
        tag, _, rest = line.partition(" ")
        verb, _, args = rest.partition(" ")
        verb = verb.upper()
        fake = self.server.fake
        fake.record("imap", verb)
        try:
            fields = arguments(args)
        except ValueError:
            return self.reply(f"{tag} BAD The arguments are not valid.")
        if verb == "CAPABILITY":
            return self.reply("* CAPABILITY IMAP4rev1 AUTH=PLAIN", f"{tag} OK CAPABILITY completed.")
        if verb == "LOGIN" and len(fields) == 2:
            self.logged_in = fake.accepts("imap", fields[0][1], fields[1][1])
            if self.logged_in:
                return self.reply(f"{tag} OK LOGIN completed.")
            return self.reply(f"{tag} NO [AUTHENTICATIONFAILED] Invalid credentials.")
        if verb == "STATUS" and fields:
            raw, name = fields[0]
            fake.status_arguments.append(raw)
            if not self.logged_in:
                return self.reply(f"{tag} NO Log in first.")
            if name not in fake.labels:
                return self.reply(f"{tag} NO Mailbox does not exist.")
            messages, unseen = fake.labels[name]
            return self.reply(f"* STATUS {quote(name)} (MESSAGES {messages} UNSEEN {unseen})",
                              f"{tag} OK STATUS completed.")
        if verb == "LOGOUT":
            self.reply("* BYE Logging out.", f"{tag} OK LOGOUT completed.")
            return False
        return self.reply(f"{tag} BAD Command not supported.")


class _Smtp(_Session):
    protocol = "smtp"
    greeting = "220 fake-gmail ESMTP ready."

    def command(self, line):
        verb, _, args = line.partition(" ")
        verb = verb.upper()
        self.server.fake.record("smtp", verb)
        if verb == "EHLO":
            return self.reply("250-fake-gmail", "250 AUTH LOGIN PLAIN")
        if verb == "AUTH":
            return self.authenticate(args)
        if verb == "QUIT":
            self.reply("221 2.0.0 Closing.")
            return False
        return self.reply("500 5.5.2 Command not recognized.")

    def authenticate(self, args):
        mechanism, _, token = args.partition(" ")
        if mechanism.upper() != "PLAIN":
            return self.reply("504 5.5.4 Mechanism not supported.")
        try:
            _, user, password = base64.b64decode(token, validate=True).split(b"\0")
        except ValueError:
            return self.reply("501 5.5.2 Malformed credentials.")
        if self.server.fake.accepts("smtp", user.decode("latin-1"), password.decode("latin-1")):
            return self.reply("235 2.7.0 Accepted.")
        # Gmail hangs up here, as seen on a real wrong password: smtplib's login() then fails on its next method.
        self.reply("535 5.7.8 Username and password not accepted.")
        return False


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, session, fake):
        super().__init__((HOST, 0), session)
        self.fake = fake
        self.timeout = 0.05  # How often the accept loop looks for a stop.


class FakeMail:
    """One fake mailbox. `labels` maps a label to (messages, unseen). A mode per protocol: "ok" checks the login,
    "refuse" refuses every login, "hang" accepts and then says nothing, "down" has nothing listening."""

    def __init__(self, user, password, labels, imap="ok", smtp="ok", timeout=5):
        if {imap, smtp} - set(MODES):
            raise ValueError("unknown mode")
        self.user, self.password, self.labels = user, password, labels
        self.modes = {"imap": imap, "smtp": smtp}
        self.timeout = timeout
        self.verbs = {"imap": [], "smtp": []}
        self.status_arguments = []
        self.ports = {}
        self.stopping = threading.Event()
        self._lock = threading.Lock()
        self._servers, self._threads = [], []

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.stop()

    def start(self):
        for protocol, session in (("imap", _Imap), ("smtp", _Smtp)):
            if self.modes[protocol] == "down":
                self.ports[protocol] = unused_port()
                continue
            server = _Server(session, self)
            self._servers.append(server)
            self.ports[protocol] = server.server_address[1]
            thread = threading.Thread(target=self._accept, args=(server,), daemon=True)
            thread.start()
            self._threads.append(thread)
        return self

    def stop(self):
        self.stopping.set()
        for thread in self._threads:
            thread.join()
        for server in self._servers:
            server.server_close()  # Also waits for the sessions still open.

    def _accept(self, server):
        while not self.stopping.is_set():
            server.handle_request()

    def accepts(self, protocol, user, password):
        return self.modes[protocol] == "ok" and user == self.user and password == self.password

    def record(self, protocol, verb):
        with self._lock:
            self.verbs[protocol].append(verb)

    def open_imap(self):
        return imaplib.IMAP4(HOST, self.ports["imap"], timeout=self.timeout)

    def open_smtp(self):
        return smtplib.SMTP(HOST, self.ports["smtp"], timeout=self.timeout)
