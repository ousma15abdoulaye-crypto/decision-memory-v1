"""Pydantic models for pattern detection (VIVANT V2 H2)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PatternType(StrEnum):
    correction_cluster = "correction_cluster"
    confidence_drift = "confidence_drift"
    volume_anomaly = "volume_anomaly"
    field_recurrence = "field_recurrence"


class DetectedPattern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_type: PatternType
    field_path: str | None
    occurrences: int
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    first_seen: str
    last_seen: str
    metadata: dict[str, Any] = Field(default_factory=dict)
