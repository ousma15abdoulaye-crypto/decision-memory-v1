"""
Similar-case retrieval via ``memory_entries.content_json`` (framework / family).

Aligns with ``CaseMemoryEntry`` keys: ``framework_detected``, ``procurement_family``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

_ENTRY_TYPE = "case_summary"


@runtime_checkable
class _ConnectionProtocol(Protocol):
    """Minimal DB connection — ``_ConnectionWrapper`` or test doubles."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


_SIMILAR_CASES_SQL = """
    WITH anchor AS (
        SELECT
            content_json->>'framework_detected' AS fw,
            content_json->>'procurement_family' AS fam
        FROM memory_entries
        WHERE case_id = :case_id AND entry_type = :etype
        ORDER BY created_at DESC
        LIMIT 1
    )
    SELECT
        m.case_id,
        m.content_json,
        CASE
            WHEN a.fw IS NULL AND a.fam IS NULL THEN 0.0
            WHEN (m.content_json->>'framework_detected') IS NOT DISTINCT FROM a.fw
                 AND (m.content_json->>'procurement_family') IS NOT DISTINCT FROM a.fam
            THEN 1.0
            WHEN (m.content_json->>'framework_detected') = a.fw
                 OR (m.content_json->>'procurement_family') = a.fam
            THEN 0.7
            ELSE 0.0
        END AS similarity_score
    FROM memory_entries m
    CROSS JOIN anchor a
    WHERE m.entry_type = :etype
      AND m.case_id <> :case_id
      AND (
          (a.fw IS NOT NULL AND (m.content_json->>'framework_detected') = a.fw)
          OR (a.fam IS NOT NULL AND (m.content_json->>'procurement_family') = a.fam)
      )
    ORDER BY similarity_score DESC, m.created_at DESC
    LIMIT :limit
"""


class DeterministicRetrieval:
    """JSONB-aware similarity over ``memory_entries`` for case_summary rows."""

    def __init__(self, conn_factory: Callable[[], _ConnectionProtocol]) -> None:
        self._conn_factory = conn_factory

    def find_similar_cases(self, case_id: str, limit: int = 5) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        conn = self._conn_factory()
        conn.execute(
            _SIMILAR_CASES_SQL,
            {"case_id": case_id, "etype": _ENTRY_TYPE, "limit": limit},
        )
        rows = conn.fetchall()
        from src.memory.retrieval_models import SimilarCaseResult

        results: list[dict[str, Any]] = []
        for r in rows:
            raw = r.get("content_json")
            if isinstance(raw, str):
                raw = json.loads(raw)
            if not isinstance(raw, dict):
                raw = {}
            fw = str(raw.get("framework_detected", "") or "")
            fam = str(raw.get("procurement_family", "") or "")
            score = float(r.get("similarity_score") or 0.0)
            validated = SimilarCaseResult(
                case_id=str(r["case_id"]),
                similarity_score=score,
                framework=fw,
                procurement_family=fam,
                summary=raw,
            )
            results.append(validated.model_dump())
        return results
