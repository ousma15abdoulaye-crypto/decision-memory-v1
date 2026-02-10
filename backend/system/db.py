"""SQLAlchemy 2.0 async database setup."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.system.settings import get_settings

__all__ = ["Base", "engine", "async_session_factory", "get_db", "init_db"]

_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_convention)

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4())
    )


settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables (dev convenience – use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
