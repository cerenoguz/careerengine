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
