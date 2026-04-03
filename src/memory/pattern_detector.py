"""
Pattern detector over append-only logs (e.g. ``m13_correction_log``).

Connection protocol matches ``m13_correction_writer`` — no direct DB driver imports.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from src.memory.pattern_models import DetectedPattern, PatternType


@runtime_checkable
class _ConnectionProtocol(Protocol):
    """Minimal DB connection — ``_ConnectionWrapper`` or test doubles."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


_CORRECTION_CLUSTERS_SQL = """
    SELECT
        field_path,
        COUNT(*)::int AS occurrences,
        MIN(created_at)::text AS first_seen,
        MAX(created_at)::text AS last_seen
    FROM m13_correction_log
    GROUP BY field_path
    HAVING COUNT(*) >= :min_occurrences
"""


def _cluster_confidence(occurrences: int) -> float:
    """Heuristic score in [0, 1] from occurrence count."""
    return min(1.0, 0.4 + 0.12 * min(occurrences, 5))


class PatternDetector:
    """Reads correction and telemetry tables; emits ``DetectedPattern`` rows."""

    def __init__(self, conn_factory: Callable[[], _ConnectionProtocol]) -> None:
        self._conn_factory = conn_factory

    def detect_correction_clusters(
        self, min_occurrences: int = 3
    ) -> list[DetectedPattern]:
        if min_occurrences < 1:
            raise ValueError("min_occurrences must be >= 1")
        conn = self._conn_factory()
        conn.execute(_CORRECTION_CLUSTERS_SQL, {"min_occurrences": min_occurrences})
        rows = conn.fetchall()
        patterns: list[DetectedPattern] = []
        for r in rows:
            fp = r.get("field_path")
            field_path = str(fp) if fp is not None else None
            occ = int(r["occurrences"])
            first = str(r["first_seen"])
            last = str(r["last_seen"])
            desc = f"Correction cluster on field_path={field_path!r}: {occ} occurrences"
            patterns.append(
                DetectedPattern(
                    pattern_type=PatternType.correction_cluster,
                    field_path=field_path,
                    occurrences=occ,
                    confidence=_cluster_confidence(occ),
                    description=desc,
                    first_seen=first,
                    last_seen=last,
                    metadata={"source": "m13_correction_log"},
                )
            )
        return patterns

    def detect_all(self) -> list[DetectedPattern]:
        """Runs all detectors and merges results (order: correction clusters)."""
        merged: list[DetectedPattern] = []
        merged.extend(self.detect_correction_clusters())
        return merged
