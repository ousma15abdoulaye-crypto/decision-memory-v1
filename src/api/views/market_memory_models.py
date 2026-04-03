"""Pydantic models for market memory card (VIVANT V2 H4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PricePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    price: float
    currency: str = "XOF"
    source: str = ""


class MarketSignalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_type: str
    detected_at: str
    description: str = ""


class MarketMemoryCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    zone: str | None = None
    price_history: list[PricePoint] = Field(default_factory=list)
    signals: list[MarketSignalSummary] = Field(default_factory=list)
    coverage_pct: float | None = None
    freshness_days: int | None = None
