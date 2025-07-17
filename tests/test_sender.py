# tests/test_sender.py

import smtplib
import pytest

import sender
from sender import EmailSender

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # Prevent real sleeping
    monkeypatch.setattr(sender.time, "sleep", lambda s: None)
    yield

def test_send_email_success(monkeypatch):
    calls = {"login": 0, "send_message": 0, "quit": 0}

    # Fake SMTP that always succeeds
    class FakeSMTP:
        def __init__(self, host, port):
            assert host == "smtp.test" and port == 465
        def login(self, user, pw):
            calls["login"] += 1
            assert user == "user" and pw == "pass"
        def send_message(self, msg, from_addr=None, to_addrs=None):
            calls["send_message"] += 1
            # Check message headers
            assert msg["Subject"] == "Test Subject"
            assert msg["From"] == "from@test"
            assert msg.get_content().strip() == "Hello"
            assert to_addrs == ["to1@test.com", "cc1@test.com"]
            assert from_addr == "from@test"
        def quit(self):
            calls["quit"] += 1

    # Patch SMTP_SSL
    monkeypatch.setattr(sender.smtplib, "SMTP_SSL", FakeSMTP)

    es = EmailSender(
        smtp_host="smtp.test",
        smtp_port=465,
        username="user",
        password="pass",
        max_retries=3,
        retry_delay=0.1
    )

    # Should not raise
    es.send_email(
        to=["to1@test.com"],
        subject="Test Subject",
        body="Hello",
        from_addr="from@test",
        cc=["cc1@test.com"]
    )

    # All three methods called exactly once
    assert calls["login"] == 1
    assert calls["send_message"] == 1
    assert calls["quit"] == 1

def test_send_email_retry_on_smtp_exception(monkeypatch):
    call_count = {"i": 0}

    class FakeSMTP:
        def __init__(self, host, port):
            pass
        def login(self, user, pw):
            pass
        def send_message(self, msg, from_addr=None, to_addrs=None):
            # fail first time, succeed second
            if call_count["i"] == 0:
                call_count["i"] += 1
                raise smtplib.SMTPException("temporary failure")
            call_count["i"] += 1
        def quit(self):
            pass

    monkeypatch.setattr(sender.smtplib, "SMTP_SSL", FakeSMTP)

    es = EmailSender(
        smtp_host="smtp.test",
        smtp_port=465,
        username="u",
        password="p",
        max_retries=3,
        retry_delay=0.1
    )

    # Should catch the first exception and retry once
    es.send_email(
        to=["t@test.com"],
        subject="S",
        body="B",
        from_addr="f@test.com",
        cc=[]
    )

    # send_message should have been called twice (1 fail, 1 success)
    assert call_count["i"] == 2

def test_send_email_all_failures(monkeypatch):
    call_count = {"i": 0}

    class FakeSMTPAlwaysFail:
        def __init__(self, host, port):
            pass
        def login(self, user, pw):
            pass
        def send_message(self, msg, from_addr=None, to_addrs=None):
            call_count["i"] += 1
            raise smtplib.SMTPException("always fail")
        def quit(self):
            pass

    monkeypatch.setattr(sender.smtplib, "SMTP_SSL", FakeSMTPAlwaysFail)

    es = EmailSender(
        smtp_host="smtp.test",
        smtp_port=465,
        username="u",
        password="p",
        max_retries=4,
        retry_delay=0.1
    )

    # Should exhaust all retries without throwing
    es.send_email(
        to=["x@test.com"],
        subject="Sub",
        body="Body"
    )

    # send_message should have been called max_retries times
    assert call_count["i"] == 4
