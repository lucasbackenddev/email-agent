"""Leitura de e-mails do Gmail via IMAP."""
import email
import imaplib
from email.header import decode_header
from email.message import EmailMessage

import config


def _decode(value) -> str:
    """Decodifica cabeçalhos de e-mail (ex.: assunto com acentos)."""
    if value is None:
        return ""
    parts = decode_header(value)
    result = []
    for text, charset in parts:
        if isinstance(text, bytes):
            result.append(text.decode(charset or "utf-8", errors="replace"))
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
    client = imaplib.IMAP4_SSL("imap.gmail.com")
    client.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
    client.select(config.CHECK_FOLDER)
    return client


def fetch_unread(limit: int = None) -> list[EmailMessage]:
    """Retorna os e-mails não lidos mais recentes como (id, remetente, assunto, corpo)."""
    if limit is None:
        limit = config.MAX_EMAILS_PER_RUN

    client = connect()
    status, data = client.search(None, "UNSEEN")
    if status != "OK":
        client.logout()
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
    client.logout()
    return emails
