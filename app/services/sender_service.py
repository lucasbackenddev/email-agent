"""Serviço de envio de e-mails via SMTP do Gmail.

Migrado do sender.py original.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.core.retry import retry

# Erros transitórios de rede/SMTP que valem retry
_RETRYABLE = (ConnectionError, TimeoutError, OSError)


@retry(times=3, backoff=2.0, initial_delay=1.0, exceptions=_RETRYABLE)
def send(to: str, subject: str, body: str) -> None:
    """Envia uma resposta em texto simples."""
    settings = get_settings()

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.gmail_user
    msg["To"] = to
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(settings.gmail_user, settings.gmail_app_password)
        smtp.send_message(msg)
