"""Pydantic models for auto-calibration (VIVANT V2 H3)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CalibrationStatus(StrEnum):
    healthy = "healthy"
    degraded = "degraded"
    critical = "critical"


class CalibrationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CalibrationStatus
    correction_rate_30d: float = Field(ge=0.0)
    pattern_count: int = Field(ge=0)
    ragas_score: float | None = None
    details: list[str] = Field(default_factory=list)
