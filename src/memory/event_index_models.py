"""Pydantic models for the VIVANT V2 event index (H2)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventDomain(StrEnum):
    procurement = "procurement"
    market = "market"
    annotation = "annotation"
    pipeline = "pipeline"
    agent = "agent"
    decision = "decision"


class EventEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_domain: EventDomain
    source_table: str
    source_pk: int
    case_id: str | None = None
    supplier_id: str | None = None
    item_id: str | None = None
    document_id: str | None = None
    aggregate_type: str
    aggregate_id: str | None = None
    event_type: str
    aggregate_version: int | None = None
    idempotency_key: str | None = None
    event_time: str
    summary: dict[str, Any] = Field(default_factory=dict)
    source_hash: str | None = None
    schema_version: str = "1.0"


class CaseTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    event_domain: str
    event_time: str
    summary: dict[str, Any]
