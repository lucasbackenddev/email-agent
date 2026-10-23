"""Serviço de leitura de e-mails do Gmail via IMAP.

Migrado do reader.py original, agora usando Pydantic Settings.
"""
import email.message
import email.utils
import imaplib
from email.header import decode_header

from app.core.config import get_settings


def _decode(value) -> str:
    """Decodifica cabeçalhos de e-mail (ex.: assunto com acentos)."""
    if value is None:
        return ""
    parts = decode_header(value)
    result = []
    for text, charset in parts:
        if isinstance(text, bytes):
            try:
                result.append(text.decode(charset or "utf-8", errors="replace"))
            except LookupError:  # encodings exóticos do Gmail (ex.: unknown-8bit)
                result.append(text.decode("utf-8", errors="replace"))
        else:
            result.append(text)
    return "".join(result)


def _get_body(msg: email.message.Message) -> str:
    """Extrai o corpo em texto simples de um e-mail."""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        # fallback: primeira parte HTML
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return msg.get_payload(decode=True).decode(charset, errors="replace")


def connect() -> imaplib.IMAP4_SSL:
    settings = get_settings()
    client = imaplib.IMAP4_SSL("imap.gmail.com")
    client.login(settings.gmail_user, settings.gmail_app_password)
    client.select(settings.check_folder)
    return client


def fetch_unread(limit: int | None = None) -> list[dict]:
    """Retorna os e-mails não lidos mais recentes."""
    settings = get_settings()
    if limit is None:
        limit = settings.max_emails_per_run

    client = connect()
    try:
        status, data = client.search(None, "UNSEEN")
        if status != "OK":
            return []

        ids = data[0].split()[-limit:]  # mais recentes
        emails = []
        for num in ids:
            status, msg_data = client.fetch(num, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            emails.append({
                "id": num.decode(),
                "from": _decode(msg.get("From", "")),
                "subject": _decode(msg.get("Subject", "")),
                "body": _get_body(msg),
            })
        return emails
    finally:
        client.logout()
