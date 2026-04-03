"""Pydantic models for RAG service (VIVANT V2 H3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RAGResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    review_required: bool = True
    sources: list[str] = Field(default_factory=list)
    reasoning: str = ""
