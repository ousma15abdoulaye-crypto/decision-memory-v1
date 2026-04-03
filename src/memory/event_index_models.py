"""Pydantic models for the VIVANT V2 event index (H2).

EventEntry.event_type is validated against the 38 types declared in
config/events/event_types.yaml.  Unknown types are warned (not rejected) so
bridge triggers from source tables still work even if they use a type that
predates the registry.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

_REGISTRY_PATH = (
    Path(__file__).parent.parent.parent / "config" / "events" / "event_types.yaml"
)


def _load_allowed_event_types() -> frozenset[str]:
    """Load the set of allowed event type strings from event_types.yaml."""
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8"))
        types: set[str] = set()
        for domain_data in (data.get("domains") or {}).values():
            for t in domain_data.get("events") or []:
                types.add(str(t))
        return frozenset(types)
    except Exception as exc:
        logger.warning("event_index_models: could not load event_types.yaml: %s", exc)
        return frozenset()


_ALLOWED_EVENT_TYPES: frozenset[str] = _load_allowed_event_types()


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

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Warn (not reject) if event_type is not in the registered list.

        Bridge triggers may use internal event types not yet in the YAML registry.
        A warning is sufficient to maintain auditability without breaking production writes.
        """
        if _ALLOWED_EVENT_TYPES and v not in _ALLOWED_EVENT_TYPES:
            logger.warning(
                "EventEntry: unregistered event_type=%r — not in event_types.yaml (38 known types). "
                "Add it to config/events/event_types.yaml if intentional.",
                v,
            )
        return v


class CaseTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    event_domain: str
    event_time: str
    summary: dict[str, Any]
