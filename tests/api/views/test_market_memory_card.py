"""Tests — Market Memory Card view."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.views.market_memory_card import get_market_memory_card
from src.api.views.market_memory_models import (
    MarketMemoryCard,
    MarketSignalSummary,
    PricePoint,
)


class TestGetMarketMemoryCard:
    def test_no_connection_returns_empty(self) -> None:
        result = get_market_memory_card("ITEM-001")
        assert isinstance(result, MarketMemoryCard)
        assert result.item_id == "ITEM-001"
        assert result.price_history == []

    def test_with_zone(self) -> None:
        result = get_market_memory_card("ITEM-001", zone="bamako")
        assert result.zone == "bamako"


class TestPricePoint:
    def test_valid(self) -> None:
        pp = PricePoint(date="2026-01-01", price=500.0)
        assert pp.currency == "XOF"

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            PricePoint(date="d", price=1.0, rogue="x")


class TestMarketSignalSummary:
    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            MarketSignalSummary(signal_type="anomaly", detected_at="now", rogue="x")


class TestMarketMemoryCardModel:
    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            MarketMemoryCard(item_id="I", rogue="x")
