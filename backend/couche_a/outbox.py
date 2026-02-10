"""Couche A – Outbox pattern for emitting market signals to Couche B."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.couche_a.models import OutboxEvent, Submission

__all__ = ["emit_market_signal"]


async def emit_market_signal(
    db: AsyncSession,
    submission_id: str,
    signal_data: dict,
) -> OutboxEvent | None:
    """Emit a market signal only if the submission is validated (CONF)."""
    stmt = select(Submission).where(Submission.id == submission_id)
    sub = (await db.execute(stmt)).scalar_one_or_none()

    if not sub or sub.status != "CONF":
        return None

    event = OutboxEvent(
        event_type="market_signal",
        payload={"submission_id": submission_id, **signal_data},
    )
    db.add(event)
    await db.flush()
    return event
