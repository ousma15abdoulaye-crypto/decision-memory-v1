"""
Case Memory Writer — structured pipeline bridge into ``memory_entries``.

Builds a rich ``CaseMemoryEntry`` from M12 pipeline output and inserts it
into ``memory_entries`` (migration 002).  In the current schema,
``content_json`` is stored as TEXT containing serialized JSON, so this
module writes JSON with ``json.dumps`` and parses it on read when needed.

``memory_entries`` has no uniqueness constraint on ``(case_id, entry_type)``
in migration 002; writes are append-only.  Use ``get_latest()`` (ORDER BY
created_at DESC LIMIT 1) to retrieve the most recent summary for a case.
A dedicated migration is required to move to JSONB + upsert semantics.

Uses the same ``_ConnectionWrapper`` pattern as ``m12_correction_writer``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CaseMemoryEntry(BaseModel):
    """Structured case summary — serialised into memory_entries.content_json."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1)
    documents_count: int = Field(..., ge=0)
    document_kinds: list[str]
    document_subtypes: list[str] = Field(default_factory=list)
    framework_detected: str
    framework_confidence: float = Field(..., ge=0.0, le=1.0)
    other_frameworks: list[str] = Field(default_factory=list)
    procurement_family: str
    estimated_value: float | None = None
    currency: str | None = None
    zone_scope: list[str] = Field(default_factory=list)
    suppliers_detected: list[str] = Field(default_factory=list)
    buyer_detected: str | None = None
    procedure_reference: str | None = None
    links_count: int = 0
    unresolved_count: int = 0
    m12_confidence_avg: float = Field(..., ge=0.0, le=1.0)
    m12_confidence_min: float = Field(..., ge=0.0, le=1.0)
    review_flags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


@runtime_checkable
class _MemoryConnection(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...
    def fetchone(self) -> dict[str, Any] | None: ...


_ENTRY_TYPE = "case_summary"

_INSERT_SQL = """
    INSERT INTO memory_entries (id, case_id, entry_type, content_json, created_at)
    VALUES (:mid, :cid, :etype, :content, :ts)
    RETURNING id
"""

_SELECT_SQL = """
    SELECT id, case_id, entry_type, content_json, created_at
    FROM memory_entries
    WHERE case_id = :cid AND entry_type = :etype
    ORDER BY created_at DESC
    LIMIT 1
"""

_COUNT_SQL = """
    SELECT COUNT(*) AS c FROM memory_entries WHERE entry_type = :etype
"""


def build_from_m12_output(case_id: str, m12_output: dict[str, Any]) -> CaseMemoryEntry:
    """
    Build a ``CaseMemoryEntry`` from raw M12 pipeline output dict.

    Expected keys in *m12_output* (all optional — defaults applied):
    - ``documents``: list of document dicts with ``document_kind``, ``subtype``
    - ``framework``: dict with ``name``, ``confidence``, ``alternatives``
    - ``procurement_family``: str
    - ``estimated_value``, ``currency``
    - ``zone_scope``, ``suppliers_detected``, ``buyer_detected``
    - ``procedure_reference``
    - ``links``: list of link dicts
    - ``confidences``: list of floats
    - ``review_flags``: list of str
    """
    documents = m12_output.get("documents", [])
    doc_kinds = sorted(
        {d.get("document_kind", "unknown") for d in documents if isinstance(d, dict)}
    )
    doc_subtypes = sorted(
        {
            d.get("subtype", "")
            for d in documents
            if isinstance(d, dict) and d.get("subtype")
        }
    )

    fw = m12_output.get("framework", {}) or {}
    fw_name = fw.get("name", "UNKNOWN")
    fw_confidence = float(fw.get("confidence", 0.6))
    fw_alternatives = fw.get("alternatives", []) or []

    links = m12_output.get("links", []) or []
    unresolved = sum(
        1 for lk in links if isinstance(lk, dict) and lk.get("status") == "unresolved"
    )

    confidences = m12_output.get("confidences", []) or []
    float_confs = [float(c) for c in confidences if isinstance(c, int | float)]
    avg_conf = sum(float_confs) / len(float_confs) if float_confs else 0.6
    min_conf = min(float_confs) if float_confs else 0.6

    return CaseMemoryEntry(
        case_id=case_id,
        documents_count=len(documents),
        document_kinds=doc_kinds,
        document_subtypes=doc_subtypes,
        framework_detected=fw_name,
        framework_confidence=fw_confidence,
        other_frameworks=fw_alternatives,
        procurement_family=m12_output.get("procurement_family", "unknown"),
        estimated_value=m12_output.get("estimated_value"),
        currency=m12_output.get("currency"),
        zone_scope=m12_output.get("zone_scope", []) or [],
        suppliers_detected=m12_output.get("suppliers_detected", []) or [],
        buyer_detected=m12_output.get("buyer_detected"),
        procedure_reference=m12_output.get("procedure_reference"),
        links_count=len(links),
        unresolved_count=unresolved,
        m12_confidence_avg=avg_conf,
        m12_confidence_min=min_conf,
        review_flags=m12_output.get("review_flags", []) or [],
    )


class CaseMemoryWriter:
    """
    Append-only writer for ``memory_entries`` (entry_type = ``case_summary``).

    ``memory_entries`` has no uniqueness constraint on ``(case_id, entry_type)``
    in migration 002, so writes are plain INSERTs.  Use ``get_latest()`` to
    retrieve the most recent entry per case.

    Pattern mirrors ``M12CorrectionWriter``: connection protocol, no ORM.
    """

    def write(self, conn: _MemoryConnection, entry: CaseMemoryEntry) -> str:
        """Insert a case summary. Returns the new memory_entries id."""
        mem_id = str(uuid4())
        payload = entry.model_dump(mode="json")
        params: dict[str, Any] = {
            "mid": mem_id,
            "cid": entry.case_id,
            "etype": _ENTRY_TYPE,
            "content": json.dumps(payload, ensure_ascii=False),
            "ts": entry.created_at,
        }
        conn.execute(_INSERT_SQL, params)
        row = conn.fetchone()
        if row is None or "id" not in row:
            raise RuntimeError("memory_entries INSERT did not RETURNING id")
        return str(row["id"])

    def get_latest(
        self, conn: _MemoryConnection, case_id: str
    ) -> CaseMemoryEntry | None:
        """Retrieve the latest case summary for *case_id*, or None."""
        conn.execute(_SELECT_SQL, {"cid": case_id, "etype": _ENTRY_TYPE})
        row = conn.fetchone()
        if row is None:
            return None
        content = row.get("content_json")
        if isinstance(content, str):
            content = json.loads(content)
        return CaseMemoryEntry.model_validate(content)

    def count_total(self, conn: _MemoryConnection) -> int:
        conn.execute(_COUNT_SQL, {"etype": _ENTRY_TYPE})
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])
