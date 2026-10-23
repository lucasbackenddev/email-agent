"""Configuração do Celery — fila de processamento de e-mails em background."""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "inbox_assistant",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Confiabilidade
    task_acks_late=True,             # só remove da fila após concluir
    task_reject_on_worker_lost=True, # re-enfileira se o worker morrer
    task_time_limit=300,             # 5 min por tarefa
    task_soft_time_limit=240,
    broker_connection_retry_on_startup=True,
)
