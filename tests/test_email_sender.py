from src.reporting import email_sender
from src.reporting.email_sender import send_email_report


def test_email_sender_skips_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("CAREERENGINE_SEND_EMAIL", raising=False)

    was_sent = send_email_report(
        subject="Test Subject",
        body="Test Body",
    )

    assert was_sent is False


def test_email_sender_skips_when_flag_is_false(monkeypatch) -> None:
    monkeypatch.setenv("CAREERENGINE_SEND_EMAIL", "false")

    was_sent = send_email_report(
        subject="Test Subject",
        body="Test Body",
    )

    assert was_sent is False


class _FakeSMTP:
    sent_messages: list = []

    def __init__(self, host, port):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def starttls(self):
        pass

    def login(self, username, password):
        pass

    def send_message(self, message):
        _FakeSMTP.sent_messages.append(message)


def _configure_smtp_env(monkeypatch) -> None:
    monkeypatch.setenv("CAREERENGINE_SEND_EMAIL", "true")
    monkeypatch.setenv("CAREERENGINE_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CAREERENGINE_SMTP_PORT", "587")
    monkeypatch.setenv("CAREERENGINE_EMAIL_FROM", "from@example.com")
    monkeypatch.setenv("CAREERENGINE_EMAIL_TO", "to@example.com")
    monkeypatch.setenv("CAREERENGINE_EMAIL_USERNAME", "user")
    monkeypatch.setenv("CAREERENGINE_EMAIL_PASSWORD", "pass")


def test_email_sender_includes_html_alternative_when_provided(monkeypatch) -> None:
    _configure_smtp_env(monkeypatch)
    _FakeSMTP.sent_messages = []
    monkeypatch.setattr(email_sender.smtplib, "SMTP", _FakeSMTP)

    was_sent = send_email_report(
        subject="Test Subject",
        body="Plain text body",
        html_body="<html><body>HTML body</body></html>",
    )

    assert was_sent is True
    assert len(_FakeSMTP.sent_messages) == 1

    message = _FakeSMTP.sent_messages[0]
    assert message.is_multipart()

    plain_part = message.get_body(preferencelist=("plain",))
    html_part = message.get_body(preferencelist=("html",))

    assert plain_part is not None and "Plain text body" in plain_part.get_content()
    assert html_part is not None and "HTML body" in html_part.get_content()


def test_email_sender_omits_html_alternative_when_not_provided(monkeypatch) -> None:
    _configure_smtp_env(monkeypatch)
    _FakeSMTP.sent_messages = []
    monkeypatch.setattr(email_sender.smtplib, "SMTP", _FakeSMTP)

    was_sent = send_email_report(
        subject="Test Subject",
        body="Plain text body",
    )

    assert was_sent is True
    message = _FakeSMTP.sent_messages[0]
    assert message.get_body(preferencelist=("html",)) is None
