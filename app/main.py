"""Inbox Assistant API — ponto de entrada da aplicação FastAPI."""
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


def create_app() -> FastAPI:
    get_settings()  # valida o .env na inicialização
    app = FastAPI(
        title="Inbox Assistant API",
        description=(
            "Backend de assistente de e-mail: lê a caixa de entrada do Gmail, "
            "gera respostas com IA (Gemini) e envia após aprovação."
        ),
        version="0.1.0",
    )
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
