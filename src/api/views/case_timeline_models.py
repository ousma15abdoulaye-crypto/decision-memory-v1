"""Pydantic models for case timeline view (VIVANT V2 H4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    event_domain: str
    event_time: str
    summary: dict = Field(default_factory=dict)


class CaseTimeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    events: list[TimelineEvent] = Field(default_factory=list)
    total_events: int = 0
