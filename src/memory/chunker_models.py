"""Pydantic models for semantic chunking (VIVANT V2 H3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_index: int = Field(ge=0)
    text: str
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    section_title: str | None = None
    token_count: int = Field(ge=0, default=0)
