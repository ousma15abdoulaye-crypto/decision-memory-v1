"""Append-only audit log helper."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from backend.system.db import Base

__all__ = ["AuditLog", "log_audit"]


class AuditLog(Base):
    __tablename__ = "audit_log"

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


async def log_audit(
    db: AsyncSession,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
) -> AuditLog:
    """Create an append-only audit record. No update/delete exposed."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    await db.flush()
    return entry
