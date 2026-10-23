"""Conexão com o banco de dados (SQLAlchemy).

Pensado para PostgreSQL em produção e SQLite em desenvolvimento:
basta ajustar DATABASE_URL no .env.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM."""


def _normalize_url(url: str) -> str:
    """Normaliza URLs de provedores (Render/Heroku usam postgres://)."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _make_engine():
    settings = get_settings()
    url = _normalize_url(settings.database_url)
    # SQLite não suporta pool "check_same_thread" padrão do SQLAlchemy em threads
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = _make_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session]:
    """Dependency do FastAPI — fornece uma sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
