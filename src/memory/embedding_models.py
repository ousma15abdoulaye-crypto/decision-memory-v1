"""Pydantic models for embeddings (VIVANT V2 H3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    chunk_index: int = Field(ge=0)
    dense: list[float]
    sparse: dict[str, float] = Field(default_factory=dict)
    model_name: str = "bge-m3"
    model_version: str = "1.0"
