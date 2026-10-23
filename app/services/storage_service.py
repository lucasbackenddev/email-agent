"""Serviço de persistência — salvar e-mails, respostas e idempotência."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Email, Reply, Sender


def get_or_create_sender(db: Session, address: str) -> Sender:
    sender = db.scalar(select(Sender).where(Sender.address == address))
    if sender is None:
        sender = Sender(address=address)
        db.add(sender)
        db.flush()
    return sender


def upsert_email(db: Session, imap_uid: str, from_addr: str, subject: str, body: str) -> tuple[Email, bool]:
    """Insere o e-mail se ainda não existir. Retorna (email, created).

    O `created=False` indica idempotência — o e-mail já estava salvo.
    """
    existing = db.scalar(select(Email).where(Email.imap_uid == imap_uid))
    if existing is not None:
        return existing, False

    sender = get_or_create_sender(db, from_addr)
    email = Email(imap_uid=imap_uid, sender_id=sender.id, subject=subject, body=body)
    db.add(email)
    db.flush()
    return email, True


def create_reply(db: Session, email_id: int, suggestion: str, status: str = "pending") -> Reply:
    reply = Reply(email_id=email_id, suggestion=suggestion, status=status)
    db.add(reply)
    db.flush()
    return reply


def mark_reply_sent(db: Session, reply_id: int, sent_body: str) -> Reply:
    reply = db.get(Reply, reply_id)
    reply.sent_body = sent_body
    reply.status = "sent"
    reply.sent_at = datetime.now(UTC)
    db.flush()
    return reply


def get_unprocessed_emails(db: Session, limit: int | None = None) -> list[Email]:
    """E-mails ainda não processados (idempotência da Fase 3 começa aqui)."""
    query = select(Email).where(Email.processed.is_(False)).order_by(Email.received_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return list(db.scalars(query))


def commit(db: Session) -> None:
    db.commit()
