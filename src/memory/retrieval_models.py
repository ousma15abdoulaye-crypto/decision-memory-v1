"""Pydantic models for deterministic retrieval (VIVANT V2 H2)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SimilarCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    framework: str
    procurement_family: str
    summary: dict[str, Any] = Field(default_factory=dict)
