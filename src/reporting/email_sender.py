import os
import smtplib
from email.message import EmailMessage


def send_email_report(subject: str, body: str) -> bool:
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

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)

    print(f"Email report sent to: {email_to}")
    return True
