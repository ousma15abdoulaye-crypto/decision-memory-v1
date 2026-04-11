"""Tests ADR-V53 — ``market_signal_lookup`` (alignement market_delta / MQL)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.services.market_signal_lookup import (
    ITEM_SIMILARITY_THRESHOLD,
    lookup_market_price_seasonal_adj,
    normalize_label_to_item_slug,
)


def test_normalize_label_to_item_slug() -> None:
    assert normalize_label_to_item_slug("Stylo Bic (bleu)") == "stylo_bic_bleu"
    assert normalize_label_to_item_slug("  ") == ""


def test_lookup_market_price_no_row_returns_none() -> None:
    conn = MagicMock()
    with patch("src.services.market_signal_lookup.db_execute_one", return_value=None):
        assert lookup_market_price_seasonal_adj(conn, "riz_25kg", "MLI-BKO") is None


def test_lookup_market_price_null_column_returns_none() -> None:
    conn = MagicMock()
    with patch(
        "src.services.market_signal_lookup.db_execute_one",
        return_value={"price_seasonal_adj": None},
    ):
        assert lookup_market_price_seasonal_adj(conn, "riz_25kg", "MLI-BKO") is None


def test_lookup_market_price_invalid_decimal_returns_none() -> None:
    conn = MagicMock()
    with patch(
        "src.services.market_signal_lookup.db_execute_one",
        return_value={"price_seasonal_adj": object()},
    ):
        assert lookup_market_price_seasonal_adj(conn, "riz_25kg", "MLI-BKO") is None


def test_lookup_market_price_uses_expected_threshold() -> None:
    conn = MagicMock()
    captured: dict = {}

    def fake_execute_one(c, sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return {"price_seasonal_adj": "125.50"}

    with patch(
        "src.services.market_signal_lookup.db_execute_one", side_effect=fake_execute_one
    ):
        out = lookup_market_price_seasonal_adj(conn, "riz_25kg", "MLI-BKO")

    assert out == Decimal("125.50")
    assert captured["params"]["threshold"] == float(ITEM_SIMILARITY_THRESHOLD)
    assert "market_signals_v2" in captured["sql"]
    assert "price_seasonal_adj" in captured["sql"]
