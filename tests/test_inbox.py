# tests/test_inbox.py

import imaplib
import pytest
from email.message import EmailMessage
from inbox import InboxConnector


class FakeIMAP:
    def __init__(self, host):
        self.host = host
        self.logged_in = None
        self.selected_mailbox = None
        self.store_calls = []
        self.closed = False
        self.logged_out = False

        # Defaults for search/fetch; tests will override as needed
        self._search_result = ("OK", [b""])
        self._fetch_results = {}  # maps uid (bytes) -> (status, data list)

    def login(self, username, password):
        self.logged_in = (username, password)

    def select(self, mailbox):
        self.selected_mailbox = mailbox
        return ("OK", [b""])

    def search(self, charset, criteria):
        return self._search_result

    def fetch(self, uid, spec):
        return self._fetch_results.get(uid, ("NO", []))

    def store(self, uid, flags, flag):
        self.store_calls.append((uid, flags, flag))

    def close(self):
        self.closed = True

    def logout(self):
        self.logged_out = True


@pytest.fixture
def fake_imap(monkeypatch):
    """
    Replace imaplib.IMAP4_SSL with our FakeIMAP.
    """
    fake = FakeIMAP("imap.test.com")
    monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host: fake)
    return fake


def test_connect(fake_imap):
    conn = InboxConnector(host="imap.test.com", username="user", password="pass", mailbox="CUSTOM")
    conn.connect()
    # ensure login and select were called correctly
    assert fake_imap.logged_in == ("user", "pass")
    assert fake_imap.selected_mailbox == "CUSTOM"
    # ensure connector.conn was set
    assert conn.conn is fake_imap


def test_fetch_unread_no_results(fake_imap):
    # Simulate search failure
    fake_imap._search_result = ("NO", [b""])
    conn = InboxConnector("imap.test.com", "u", "p")
    conn.connect()
    msgs = conn.fetch_unread()
    assert msgs == []


def test_fetch_unread_fetch_failure(fake_imap):
    # One UID, but fetch returns NO
    fake_imap._search_result = ("OK", [b"1"])
    fake_imap._fetch_results = {b"1": ("NO", [])}

    conn = InboxConnector("imap.test.com", "u", "p")
    conn.connect()
    msgs = conn.fetch_unread(limit=1)
    assert msgs == []
    # No store call on fetch failure
    assert fake_imap.store_calls == []


def test_fetch_unread_single_message(fake_imap):
    # Build a simple EmailMessage
    msg = EmailMessage()
    msg["Subject"] = "Test Subject"
    msg["From"] = "sender@example.com"
    msg["Date"] = "Thu, 01 Jan 1970 00:00:00 +0000"
    msg.set_content("Hello world")
    raw = msg.as_bytes()

    fake_imap._search_result = ("OK", [b"1"])
    fake_imap._fetch_results = {b"1": ("OK", [(None, raw)])}

    conn = InboxConnector("imap.test.com", "u", "p")
    conn.connect()
    msgs = conn.fetch_unread(limit=1)

    # Validate parsed output
    assert len(msgs) == 1
    parsed = msgs[0]
    assert parsed["uid"] == "1"
    assert parsed["sender"] == "sender@example.com"
    assert parsed["subject"] == "Test Subject"
    assert parsed["date"] == "Thu, 01 Jan 1970 00:00:00 +0000"
    assert parsed["body"] == "Hello world"

    # Check it was marked as read
    assert fake_imap.store_calls == [(b"1", "+FLAGS", "\\Seen")]


def test_fetch_unread_multipart_message(fake_imap):
    # Multipart: text + attachment
    msg = EmailMessage()
    msg["Subject"] = "Multipart"
    msg["From"] = "multi@example.com"
    msg["Date"] = "Thu, 01 Jan 1970 00:00:00 +0000"
    msg.set_content("Part one")
    # Add a dummy attachment
    msg.add_attachment(b"data", maintype="application", subtype="octet-stream", filename="file.bin")
    raw = msg.as_bytes()

    fake_imap._search_result = ("OK", [b"1"])
    fake_imap._fetch_results = {b"1": ("OK", [(None, raw)])}

    conn = InboxConnector("imap.test.com", "u", "p")
    conn.connect()
    msgs = conn.fetch_unread(limit=1)

    assert len(msgs) == 1
    # The body should include only the text part, not the attachment
    assert msgs[0]["body"] == "Part one"


def test_logout(fake_imap):
    conn = InboxConnector("imap.test.com", "u", "p")
    conn.connect()
    conn.logout()
    assert fake_imap.closed is True
    assert fake_imap.logged_out is True
