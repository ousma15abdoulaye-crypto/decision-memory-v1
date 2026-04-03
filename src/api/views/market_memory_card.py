"""Market memory card — prices, signals, coverage for an item/zone."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.views.market_memory_models import (
    MarketMemoryCard,
    MarketSignalSummary,
    PricePoint,
)
from src.db.connection import get_db_cursor

router = APIRouter(prefix="/views", tags=["views"])

_PRICE_HISTORY_SQL = """
    SELECT
        decided_at::text  AS date,
        unit_price::float AS price,
        currency
    FROM public.decision_history
    WHERE item_id = %(item_id)s
    ORDER BY decided_at DESC
    LIMIT 20
"""

_PRICE_HISTORY_ZONE_SQL = """
    SELECT
        decided_at::text  AS date,
        unit_price::float AS price,
        currency
    FROM public.decision_history
    WHERE item_id = %(item_id)s
      AND zone_id = %(zone_id)s
    ORDER BY decided_at DESC
    LIMIT 20
"""

_SIGNALS_SQL = """
    SELECT
        alert_level         AS signal_type,
        created_at::text    AS detected_at,
        COALESCE(signal_quality, '') AS description
    FROM public.market_signals_v2
    WHERE item_id = %(item_id)s
    ORDER BY created_at DESC
    LIMIT 10
"""

_SIGNALS_ZONE_SQL = """
    SELECT
        alert_level         AS signal_type,
        created_at::text    AS detected_at,
        COALESCE(signal_quality, '') AS description
    FROM public.market_signals_v2
    WHERE item_id = %(item_id)s
      AND zone_id = %(zone_id)s
    ORDER BY created_at DESC
    LIMIT 10
"""

_COVERAGE_SQL = """
    SELECT
        coverage_pct::float  AS coverage_pct,
        freshness_days::int  AS freshness_days
    FROM public.market_coverage
    WHERE item_id = %(item_id)s
    LIMIT 1
"""

_COVERAGE_ZONE_SQL = """
    SELECT
        coverage_pct::float  AS coverage_pct,
        freshness_days::int  AS freshness_days
    FROM public.market_coverage
    WHERE item_id = %(item_id)s
      AND zone_id = %(zone_id)s
    LIMIT 1
"""


@router.get("/market/{item_id}", response_model=MarketMemoryCard)
def get_market_memory_card(item_id: str, zone: str | None = None) -> MarketMemoryCard:
    try:
        with get_db_cursor() as cur:
            params: dict = {"item_id": item_id}

            # Price history
            if zone:
                cur.execute(_PRICE_HISTORY_ZONE_SQL, {**params, "zone_id": zone})
            else:
                cur.execute(_PRICE_HISTORY_SQL, params)
            price_rows = cur.fetchall()
            price_history = [
                PricePoint(
                    date=str(r["date"]),
                    price=float(r["price"]),
                    currency=str(r.get("currency") or "XOF"),
                    source="decision_history",
                )
                for r in price_rows
            ]

            # Market signals
            if zone:
                cur.execute(_SIGNALS_ZONE_SQL, {**params, "zone_id": zone})
            else:
                cur.execute(_SIGNALS_SQL, params)
            signal_rows = cur.fetchall()
            signals = [
                MarketSignalSummary(
                    signal_type=str(r.get("signal_type") or "UNKNOWN"),
                    detected_at=str(r.get("detected_at") or ""),
                    description=str(r.get("description") or ""),
                )
                for r in signal_rows
            ]

            # Coverage
            coverage_pct: float | None = None
            freshness_days: int | None = None
            try:
                if zone:
                    cur.execute(_COVERAGE_ZONE_SQL, {**params, "zone_id": zone})
                else:
                    cur.execute(_COVERAGE_SQL, params)
                cov_row = cur.fetchone()
                if cov_row:
                    coverage_pct = (
                        float(cov_row["coverage_pct"])
                        if cov_row.get("coverage_pct") is not None
                        else None
                    )
                    freshness_days = (
                        int(cov_row["freshness_days"])
                        if cov_row.get("freshness_days") is not None
                        else None
                    )
            except Exception:
                pass

            return MarketMemoryCard(
                item_id=item_id,
                zone=zone,
                price_history=price_history,
                signals=signals,
                coverage_pct=coverage_pct,
                freshness_days=freshness_days,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
