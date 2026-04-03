"""
Benchmark bootstrap → production — métriques stub jusqu’à données réelles.
ADR-M13-001
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkStatus(BaseModel):
    total_cases_processed: int = 0
    regime_resolution_accuracy: float = 0.0
    gate_assembly_recall: float = 0.0
    eliminatory_gate_recall: float = 0.0
    principles_coverage_completeness: float = 0.0
    correction_rate_last_30d: float = 0.0
    computed_at: str = ""

    model_config = ConfigDict(extra="forbid")


class ModeTransitionProposal(BaseModel):
    current_mode: str = "bootstrap"
    proposed_mode: str = "bootstrap"
    transition_eligible: bool = False
    blocking_criteria: list[str] = Field(default_factory=list)
    met_criteria: list[str] = Field(default_factory=list)
    proposal_timestamp: str = ""
    requires_cto_validation: bool = True

    model_config = ConfigDict(extra="forbid")


class BenchmarkStatusService:
    """Propose la transition — ne décide jamais (stub sans requêtes lourdes)."""

    PRODUCTION_THRESHOLDS: dict[str, Any] = {
        "total_cases_processed": 50,
        "regime_resolution_accuracy": 0.90,
        "gate_assembly_recall": 0.85,
        "eliminatory_gate_recall": 0.95,
        "principles_coverage_completeness": 0.90,
        "correction_rate_last_30d_max": 0.10,
    }

    def __init__(self, _db_session_factory: Any = None, _correction_repo: Any = None):
        self._db = _db_session_factory
        self._corrections = _correction_repo

    def compute_status(self) -> BenchmarkStatus:
        if self._db is None or self._corrections is None:
            return BenchmarkStatus(
                total_cases_processed=0,
                regime_resolution_accuracy=0.0,
                gate_assembly_recall=0.0,
                eliminatory_gate_recall=0.0,
                principles_coverage_completeness=0.0,
                correction_rate_last_30d=0.0,
                computed_at=datetime.now(UTC).isoformat(),
            )
        return self._compute_from_db()

    def _compute_from_db(self) -> BenchmarkStatus:
        """Real metrics from m13_regulatory_profile_versions + m13_correction_log."""
        conn = self._db()
        try:
            conn.execute(
                "SELECT COUNT(DISTINCT case_id) AS c "
                "FROM m13_regulatory_profile_versions",
                {},
            )
            row = conn.fetchone()
            total = int(row["c"]) if row else 0

            correction_rate = self._corrections.rate_last_30d(conn)

            return BenchmarkStatus(
                total_cases_processed=total,
                regime_resolution_accuracy=0.0,
                gate_assembly_recall=0.0,
                eliminatory_gate_recall=0.0,
                principles_coverage_completeness=0.0,
                correction_rate_last_30d=correction_rate,
                computed_at=datetime.now(UTC).isoformat(),
            )
        except Exception:
            return BenchmarkStatus(
                total_cases_processed=0,
                regime_resolution_accuracy=0.0,
                gate_assembly_recall=0.0,
                eliminatory_gate_recall=0.0,
                principles_coverage_completeness=0.0,
                correction_rate_last_30d=0.0,
                computed_at=datetime.now(UTC).isoformat(),
            )

    def evaluate_transition(self) -> ModeTransitionProposal:
        status = self.compute_status()
        blocking: list[str] = []
        met: list[str] = []
        checks = [
            ("total_cases", status.total_cases_processed, 50, "gte"),
            ("regime_accuracy", status.regime_resolution_accuracy, 0.90, "gte"),
            ("gate_recall", status.gate_assembly_recall, 0.85, "gte"),
            ("elim_recall", status.eliminatory_gate_recall, 0.95, "gte"),
            ("principles", status.principles_coverage_completeness, 0.90, "gte"),
            ("correction_rate", status.correction_rate_last_30d, 0.10, "lte"),
        ]
        for name, actual, threshold, op in checks:
            passed = actual >= threshold if op == "gte" else actual <= threshold
            entry = f"{name}: {actual:.2f} (need: {threshold})"
            (met if passed else blocking).append(entry)

        return ModeTransitionProposal(
            current_mode="bootstrap",
            proposed_mode="production" if not blocking else "bootstrap",
            transition_eligible=len(blocking) == 0,
            blocking_criteria=blocking,
            met_criteria=met,
            proposal_timestamp=datetime.now(UTC).isoformat(),
        )
