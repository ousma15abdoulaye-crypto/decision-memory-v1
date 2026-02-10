"""Alembic environment configuration — Source of Truth.

Imports metadata from src.db (canonical path).
"""

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# If DATABASE_URL contains an async driver, keep it for the backend import
# but derive a sync URL for Alembic's own connection.
_db_url_raw = os.environ.get("DATABASE_URL", "")
_sync_url: str | None = None
if _db_url_raw:
    _sync_url = _db_url_raw.replace("+asyncpg", "").replace("+aiosqlite", "")

from src.db import Base  # Source of Truth import

# Import all models so Base.metadata is populated
import src.couche_a.models  # noqa: F401
import src.couche_b.models  # noqa: F401
import src.system.audit  # noqa: F401

config = context.config

# Override sqlalchemy.url from DATABASE_URL env var if set.
# Alembic requires a synchronous driver, so async drivers are stripped.
if _sync_url:
    config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
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
