"""Envio de e-mails via SMTP do Gmail."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send(to: str, subject: str, body: str) -> None:
    """Envia uma resposta em texto simples."""
    msg = MIMEMultipart("alternative")
    msg["From"] = config.GMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)
