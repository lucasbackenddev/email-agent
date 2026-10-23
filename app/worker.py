"""Tasks do Celery — processamento de e-mails em background."""
import logging

from sqlalchemy.orm import close_all_sessions

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.entities import Email
from app.services import generator_service, reader_service
from app.services import repository as repo

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def sync_emails_task(self) -> dict:
    """Sincroniza e-mails não lidos do Gmail para o banco (idempotente)."""
    db = SessionLocal()
    try:
        mails = reader_service.fetch_unread()
        novos = 0
        for mail in mails:
            _, created = repo.upsert_email(
                db, imap_uid=mail["id"],
                sender_address=mail["from"],
                subject=mail["subject"],
                body=mail["body"],
            )
            if created:
                novos += 1
        db.commit()
        logger.info("Sincronização concluída: %d novos e-mails", novos)
        return {"novos": novos, "total_lido": len(mails)}
    except Exception as exc:
        db.rollback()
        logger.exception("Falha na sincronização")
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_email_task(self, email_id: int) -> dict:
    """Gera a resposta (IA) para um e-mail específico e persiste a sugestão."""
    db = SessionLocal()
    try:
        mail = db.get(Email, email_id)
        if mail is None:
            return {"email_id": email_id, "status": "not_found"}

        # Idempotência: pula se já processado
        if mail.processed:
            return {"email_id": email_id, "status": "already_processed"}

        reply = repo.create_reply(db, email_id=email_id, suggestion=None, status="pending")
        try:
            suggestion = generator_service.generate_reply(
                mail.sender.address, mail.subject, mail.body
            )
        except Exception as exc:
            db.rollback()
            logger.exception("Falha na geração para e-mail %d", email_id)
            raise self.retry(exc=exc)

        if suggestion == "NAO_RESPONDER":
            reply.status = "skipped"
            reply.suggestion = ""
            db.commit()
            return {"email_id": email_id, "status": "skipped"}

        reply.suggestion = suggestion
        mail.processed = True
        db.commit()
        logger.info("Resposta gerada para e-mail %d", email_id)
        return {"email_id": email_id, "status": "generated"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        close_all_sessions()


@celery_app.task(bind=True)
def process_all_emails_task(self) -> dict:
    """Processa todos os e-mails ainda não processados (fan-out por e-mail)."""
    db = SessionLocal()
    try:
        ids = list(db.scalars(
            __import__("sqlalchemy").select(Email.id).where(Email.processed.is_(False))
        ))
    finally:
        db.close()

    for eid in ids:
        process_email_task.delay(eid)
    return {"dispatched": len(ids)}
