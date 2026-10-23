"""Rotas da API — persistência (Fase 2) + fila com Celery (Fase 3)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.models import EmailOut, ProcessResult, ReplySend
from app.services import generator_service, repository, sender_service


def _get_worker():
    """Importa o worker (e o Celery) só quando necessário."""
    from app import worker
    return worker


def _enqueue(task, *args) -> dict:
    """Enfileira uma task; sem Redis disponível, executa localmente (modo dev)."""
    try:
        result = task.delay(*args)
        return {"queued": True, "task_id": result.id}
    except Exception as exc:
        # Redis indisponível → executa em linha para não quebrar o dev
        task(*args)
        return {"queued": False, "executed_locally": True, "reason": str(exc)}

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/emails", response_model=list[EmailOut])
def list_unread(limit: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Lista e-mails não processados (sincroniza com o Gmail e lê do banco)."""
    try:
        repository.sync_unread(db, limit=limit)
    except Exception as exc:  # credenciais inválidas, rede, etc.
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    mails = repository.list_unprocessed(db, limit=limit)
    return [
        {
            "id": m.imap_uid,
            "from_": m.sender.address,
            "subject": m.subject,
            "body": m.body,
        }
        for m in mails
    ]


@router.post("/emails/process", response_model=list[ProcessResult])
def process_emails(limit: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Gera sugestão de resposta (IA) para cada e-mail não processado."""
    try:
        repository.sync_unread(db, limit=limit)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    mails = repository.list_unprocessed(db, limit=limit)
    results: list[dict] = []
    for mail in mails:
        sender_addr = mail.sender.address
        try:
            suggestion = generator_service.generate_reply(
                sender_addr, mail.subject, mail.body
            )
        except Exception as exc:
            results.append({
                "email_id": mail.imap_uid,
                "from_": sender_addr,
                "subject": mail.subject,
                "suggestion": None,
                "skip_reason": f"erro na geração: {exc}",
            })
            continue

        if suggestion == "NAO_RESPONDER":
            repository.mark_processed(db, mail.id)
            repository.create_reply(db, mail.id, None, status="skipped")
            db.commit()
            results.append({
                "email_id": mail.imap_uid,
                "from_": sender_addr,
                "subject": mail.subject,
                "suggestion": None,
                "skip_reason": "IA decidiu não responder (spam/sem pergunta)",
            })
            continue

        repository.create_reply(db, mail.id, suggestion)
        repository.mark_processed(db, mail.id)
        db.commit()
        results.append({
            "email_id": mail.imap_uid,
            "from_": sender_addr,
            "subject": mail.subject,
            "suggestion": suggestion,
            "skip_reason": None,
        })
    return results


@router.post("/replies/send")
def send_reply(payload: ReplySend, db: Session = Depends(get_db)) -> dict:
    """Envia uma resposta aprovada (ou editada) e registra no banco."""
    try:
        sender_service.send(payload.to, payload.subject, payload.body)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    repository.mark_reply_sent_by_email(db, payload.email_id, payload.body)
    db.commit()
    return {"status": "sent", "to": payload.to}


# ---------- Fila (Celery) ----------


@router.post("/queue/sync")
def queue_sync() -> dict:
    """Enfileira a sincronização de e-mails do Gmail (background)."""
    return _enqueue(_get_worker().sync_emails_task)


@router.post("/queue/process")
def queue_process() -> dict:
    """Enfileira o processamento (IA) de todos os e-mails pendentes."""
    return _enqueue(_get_worker().process_all_emails_task)


@router.get("/queue/status/{task_id}")
def queue_status(task_id: str) -> dict:
    """Consulta o status de uma tarefa da fila."""
    result = _get_worker().celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "state": result.state, "result": result.result if result.ready() else None}
