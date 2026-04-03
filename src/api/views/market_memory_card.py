"""Market memory card — prices, signals, coverage for an item/zone."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.api.views.market_memory_models import MarketMemoryCard

router = APIRouter(prefix="/views", tags=["views"])


def _get_connection() -> Any:
    return None


@router.get("/market/{item_id}", response_model=MarketMemoryCard)
def get_market_memory_card(item_id: str, zone: str | None = None) -> MarketMemoryCard:
    conn = _get_connection()
    if conn is None:
        return MarketMemoryCard(item_id=item_id, zone=zone)
    return MarketMemoryCard(item_id=item_id, zone=zone)
