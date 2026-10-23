"""Testes do repositório — persistência e idempotência."""
from app.services import repository as repo


def test_upsert_email_creates_once(db_session):
    mail1, created1 = repo.upsert_email(
        db_session, "uid-1", "a@x.com", "Assunto", "Corpo"
    )
    mail2, created2 = repo.upsert_email(
        db_session, "uid-1", "a@x.com", "Assunto", "Corpo"
    )
    assert created1 is True
    assert created2 is False
    assert mail1.id == mail2.id


def test_upsert_email_reuses_sender(db_session):
    repo.upsert_email(db_session, "uid-1", "a@x.com", "s1", "b1")
    repo.upsert_email(db_session, "uid-2", "a@x.com", "s2", "b2")

    from sqlalchemy import select

    from app.models.entities import Sender

    senders = db_session.scalars(select(Sender)).all()
    assert len(senders) == 1  # mesmo remetente não duplica


def test_mark_processed_and_reply_flow(db_session):
    mail, _ = repo.upsert_email(db_session, "uid-1", "a@x.com", "s", "b")

    reply = repo.create_reply(db_session, mail.id, "resposta sugerida")
    assert reply.status == "pending"

    repo.mark_processed(db_session, mail.id)
    repo.mark_reply_sent_by_email(db_session, "uid-1", "corpo enviado")
    db_session.commit()

    assert mail.processed is True
    assert reply.status == "sent"
    assert reply.sent_body == "corpo enviado"
    assert reply.sent_at is not None


def test_list_unprocessed_excludes_processed(db_session):
    repo.upsert_email(db_session, "uid-1", "a@x.com", "s1", "b1")
    m2, _ = repo.upsert_email(db_session, "uid-2", "b@x.com", "s2", "b2")

    assert len(repo.list_unprocessed(db_session)) == 2

    repo.mark_processed(db_session, m2.id)
    remaining = repo.list_unprocessed(db_session)
    assert len(remaining) == 1
    assert remaining[0].imap_uid == "uid-1"


def test_mark_reply_sent_by_email_without_pending_creates_reply(db_session):
    mail, _ = repo.upsert_email(db_session, "uid-1", "a@x.com", "s", "b")

    repo.mark_reply_sent_by_email(db_session, "uid-1", "enviado direto")
    db_session.commit()

    replies = mail.replies
    assert len(replies) == 1
    assert replies[0].status == "sent"
