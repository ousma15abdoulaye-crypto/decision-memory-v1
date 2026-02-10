"""Couche B – Market intelligence statistics."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.couche_b.models import MarketSignal

__all__ = ["get_price_stats"]


async def get_price_stats(
    item_id: str, geo_id: str | None, db: AsyncSession
) -> dict:
    """Compute price stats for an item, optionally filtered by geography."""
    stmt = select(MarketSignal).where(
        MarketSignal.item_id == item_id,
        MarketSignal.superseded_by.is_(None),
    )
    if geo_id:
        stmt = stmt.where(MarketSignal.geo_id == geo_id)

    rows = (await db.execute(stmt)).scalars().all()
    # Chronological order for trend analysis
    chrono_prices = [r.unit_price for r in sorted(rows, key=lambda r: r.created_at) if r.unit_price is not None]

    if not chrono_prices:
        return {
            "item_id": item_id,
            "geo_id": geo_id,
            "count": 0,
            "min": None,
            "max": None,
            "avg": None,
            "median": None,
            "trend": None,
        }

    prices_sorted = sorted(chrono_prices)
    n = len(prices_sorted)
    median = (
        prices_sorted[n // 2]
        if n % 2 == 1
        else (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
    )

    # Trend: compare earliest and latest signals chronologically
    trend = None
    if n >= 2:
        if chrono_prices[-1] > chrono_prices[0]:
            trend = "up"
        elif chrono_prices[-1] < chrono_prices[0]:
            trend = "down"
        else:
            trend = "stable"

    return {
        "item_id": item_id,
        "geo_id": geo_id,
        "count": n,
        "min": min(chrono_prices),
        "max": max(chrono_prices),
        "avg": round(sum(chrono_prices) / n, 2),
        "median": median,
        "trend": trend,
    }
