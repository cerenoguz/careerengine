import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_email_report(
    subject: str,
    body: str,
    attachment_paths: list[Path] | None = None,
) -> bool:
    """
    Send the CareerEngine report by email.

    Email sending is disabled unless CAREERENGINE_SEND_EMAIL=true.

    Required environment variables when enabled:
    - CAREERENGINE_SMTP_HOST
    - CAREERENGINE_SMTP_PORT
    - CAREERENGINE_EMAIL_FROM
    - CAREERENGINE_EMAIL_TO
    - CAREERENGINE_EMAIL_USERNAME
    - CAREERENGINE_EMAIL_PASSWORD

    Returns True only when an email was actually sent.
    """
    send_email_enabled = os.getenv("CAREERENGINE_SEND_EMAIL", "false").lower()

    if send_email_enabled != "true":
        print("Email sending skipped. Set CAREERENGINE_SEND_EMAIL=true to enable.")
        return False

    smtp_host = os.environ["CAREERENGINE_SMTP_HOST"]
    smtp_port = int(os.environ["CAREERENGINE_SMTP_PORT"])
    email_from = os.environ["CAREERENGINE_EMAIL_FROM"]
    email_to = os.environ["CAREERENGINE_EMAIL_TO"]
    username = os.environ["CAREERENGINE_EMAIL_USERNAME"]
    password = os.environ["CAREERENGINE_EMAIL_PASSWORD"]

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = email_to
    message.set_content(body)

    for attachment_path in attachment_paths or []:
        if not attachment_path.exists():
            print(f"Attachment skipped because file does not exist: {attachment_path}")
            continue

        attachment_text = attachment_path.read_text(encoding="utf-8")

        message.add_attachment(
            attachment_text,
            subtype="plain",
            filename=attachment_path.name,
        )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)

    print(f"Email report sent to: {email_to}")
    return True