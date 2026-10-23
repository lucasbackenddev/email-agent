"""Repositório — persistência de e-mails e respostas com idempotência.

Camada que isola o acesso ao banco dos serviços externos (IMAP/SMTP/IA).
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Email, Reply, Sender


def get_or_create_sender(db: Session, address: str) -> Sender:
    """Busca o remetente pelo endereço; cria se não existir."""
    sender = db.scalar(select(Sender).where(Sender.address == address))
    if sender is None:
        sender = Sender(address=address)
        db.add(sender)
        db.flush()  # obtém o id antes do commit
    return sender


def upsert_email(db: Session, imap_uid: str, sender_address: str,
                 subject: str, body: str) -> tuple[Email, bool]:
    """Grava o e-mail se for novo. Retorna (email, created).

    Idempotência: `imap_uid` único — o mesmo e-mail nunca é duplicado.
    """
    existing = db.scalar(select(Email).where(Email.imap_uid == imap_uid))
    if existing is not None:
        return existing, False

    sender = get_or_create_sender(db, sender_address)
    mail = Email(
        imap_uid=imap_uid,
        sender_id=sender.id,
        subject=subject,
        body=body,
    )
    db.add(mail)
    db.flush()
    return mail, True


def mark_processed(db: Session, email_id: int) -> None:
    mail = db.get(Email, email_id)
    if mail is not None:
        mail.processed = True


def create_reply(db: Session, email_id: int, suggestion: str | None,
                 status: str = "pending") -> Reply:
    reply = Reply(email_id=email_id, suggestion=suggestion or "", status=status)
    db.add(reply)
    db.flush()
    return reply


def mark_reply_sent(db: Session, reply_id: int, sent_body: str) -> None:
    reply = db.get(Reply, reply_id)
    if reply is not None:
        reply.status = "sent"
        reply.sent_body = sent_body
        reply.sent_at = datetime.now(UTC)


def list_pending_replies(db: Session, limit: int | None = None) -> list[Email]:
    """E-mails processados que ainda têm resposta pendente."""
    stmt = (
        select(Email)
        .where(Email.processed.is_(True))
        .order_by(Email.received_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def list_emails(db: Session, limit: int | None = None) -> list[Email]:
    stmt = select(Email).order_by(Email.received_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def list_unprocessed(db: Session, limit: int | None = None) -> list[Email]:
    """E-mails ainda não processados (sem sugestão gerada)."""
    stmt = (
        select(Email)
        .where(Email.processed.is_(False))
        .order_by(Email.received_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def sync_unread(db: Session, limit: int | None = None) -> int:
    """Busca e-mails não lidos no Gmail e grava os novos no banco.

    Idempotente: e-mails já gravados (mesmo imap_uid) são ignorados.
    Retorna quantos e-mails novos foram gravados.
    """
    from app.services import reader_service  # import local evita ciclo

    created = 0
    for mail in reader_service.fetch_unread(limit=limit):
        address = mail["from"].split("<")[-1].strip("<>").strip() or mail["from"]
        _, is_new = upsert_email(
            db,
            imap_uid=mail["id"],
            sender_address=address,
            subject=mail["subject"],
            body=mail["body"],
        )
        if is_new:
            created += 1
    db.commit()
    return created


def mark_reply_sent_by_email(db: Session, imap_uid: str, sent_body: str) -> None:
    """Marca como enviada a resposta pendente mais recente do e-mail."""
    mail = db.scalar(select(Email).where(Email.imap_uid == imap_uid))
    if mail is None:
        return
    reply = db.scalar(
        select(Reply)
        .where(Reply.email_id == mail.id, Reply.status == "pending")
        .order_by(Reply.created_at.desc())
    )
    if reply is None:
        reply = create_reply(db, mail.id, sent_body)
    reply.status = "sent"
    reply.sent_body = sent_body
    reply.sent_at = datetime.now(UTC)
