"""Configuração central via Pydantic Settings (substitui o config.py antigo)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Gmail ---
    gmail_user: str = ""
    gmail_app_password: str = ""

    # --- Gemini (Google AI Studio) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # --- Comportamento ---
    check_folder: str = "INBOX"
    unread_only: bool = True
    max_emails_per_run: int = 5

    # --- Banco de dados ---
    database_url: str = "sqlite:///./inbox_assistant.db"

    # --- Redis (fila Celery) ---
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
