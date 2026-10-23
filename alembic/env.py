"""Configuração do Alembic — lê DATABASE_URL das settings do app."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base
import app.models.entities  # noqa: F401 — registra os modelos no metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL do banco vem das settings (suporta .env / variável DATABASE_URL)
# Normaliza postgres:// → postgresql+psycopg2:// (formato de provedores como Render)
from app.core.database import _normalize_url

config.set_main_option("sqlalchemy.url", _normalize_url(get_settings().database_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
