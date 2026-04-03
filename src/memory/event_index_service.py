"""
Event index service — append events and query timelines.

Uses the same connection protocol as ``m12_correction_writer`` /
``m13_correction_writer`` (execute / fetchone / fetchall). Table assumed:
``dms_event_index`` (migration 061) with JSONB ``summary`` and UUID ``event_id``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from src.memory.event_index_models import CaseTimelineEntry, EventDomain, EventEntry


@runtime_checkable
class _ConnectionProtocol(Protocol):
    """Minimal DB connection — ``_ConnectionWrapper`` or test doubles."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


class EventIndexService:
    """Append-only event log with case timeline and domain counts."""

    _INSERT_SQL = """
        INSERT INTO dms_event_index (
            event_domain,
            source_table,
            source_pk,
            case_id,
            supplier_id,
            item_id,
            document_id,
            aggregate_type,
            aggregate_id,
            event_type,
            aggregate_version,
            idempotency_key,
            event_time,
            summary,
            source_hash,
            schema_version
        ) VALUES (
            :event_domain,
            :source_table,
            :source_pk,
            :case_id,
            :supplier_id,
            :item_id,
            :document_id,
            :aggregate_type,
            :aggregate_id,
            :event_type,
            :aggregate_version,
            :idempotency_key,
            :event_time,
            CAST(:summary AS jsonb),
            :source_hash,
            :schema_version
        )
        RETURNING event_id
    """

    _TIMELINE_SQL = """
        SELECT
            event_id::text AS event_id,
            event_type,
            event_domain::text AS event_domain,
            event_time,
            summary
        FROM dms_event_index
        WHERE case_id = :case_id
        ORDER BY event_time DESC
        LIMIT :limit
    """

    _COUNT_DOMAIN_SQL = """
        SELECT COUNT(*) AS c
        FROM dms_event_index
        WHERE event_domain = :domain
    """

    def __init__(self, conn_factory: Callable[[], _ConnectionProtocol]) -> None:
        self._conn_factory = conn_factory

    def append(self, entry: EventEntry) -> str:
        """Insert one event; returns ``event_id``."""
        conn = self._conn_factory()
        params: dict[str, Any] = {
            "event_domain": entry.event_domain.value,
            "source_table": entry.source_table,
            "source_pk": entry.source_pk,
            "case_id": entry.case_id,
            "supplier_id": entry.supplier_id,
            "item_id": entry.item_id,
            "document_id": entry.document_id,
            "aggregate_type": entry.aggregate_type,
            "aggregate_id": entry.aggregate_id,
            "event_type": entry.event_type,
            "aggregate_version": entry.aggregate_version,
            "idempotency_key": entry.idempotency_key,
            "event_time": entry.event_time,
            "summary": json.dumps(entry.summary, ensure_ascii=False),
            "source_hash": entry.source_hash,
            "schema_version": entry.schema_version,
        }
        conn.execute(self._INSERT_SQL, params)
        row = conn.fetchone()
        if row is None or "event_id" not in row:
            raise RuntimeError("event_index INSERT did not RETURNING event_id")
        return str(row["event_id"])

    def case_timeline(self, case_id: str, limit: int = 50) -> list[CaseTimelineEntry]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        conn = self._conn_factory()
        conn.execute(self._TIMELINE_SQL, {"case_id": case_id, "limit": limit})
        rows = conn.fetchall()
        out: list[CaseTimelineEntry] = []
        for r in rows:
            summary = r.get("summary")
            if isinstance(summary, str):
                summary = json.loads(summary)
            if not isinstance(summary, dict):
                summary = {}
            out.append(
                CaseTimelineEntry(
                    event_id=str(r["event_id"]),
                    event_type=str(r["event_type"]),
                    event_domain=str(r["event_domain"]),
                    event_time=str(r["event_time"]),
                    summary=summary,
                )
            )
        return out

    def count_by_domain(self, domain: EventDomain) -> int:
        conn = self._conn_factory()
        conn.execute(self._COUNT_DOMAIN_SQL, {"domain": domain.value})
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])
