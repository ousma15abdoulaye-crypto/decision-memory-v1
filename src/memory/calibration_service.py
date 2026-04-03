"""CalibrationService — reads real DB metrics and delegates to AutoCalibrator.

Bridges the gap between database tables and the pure-Python AutoCalibrator (GAP-13).
Reads:
  - correction_rate_30d from m13_correction_log
  - pattern_count from PatternDetector
  - ragas_score from data/ragas_baseline.json (if present)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from src.memory.auto_calibrator import AutoCalibrator
from src.memory.calibration_models import CalibrationReport

logger = logging.getLogger(__name__)

_BASELINE_PATH = Path(__file__).parent.parent.parent / "data" / "ragas_baseline.json"

_RATE_SQL = """
    SELECT
        COALESCE(
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days')::float
            / NULLIF(
                (SELECT COUNT(*) FROM m13_correction_log
                 WHERE created_at >= NOW() - INTERVAL '30 days'), 0
            ),
            0.0
        ) AS rate_30d
    FROM m13_correction_log
"""

_TOTAL_SQL = """
    SELECT COUNT(*) AS total FROM m13_correction_log
"""


@runtime_checkable
class _ConnectionProtocol(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


class CalibrationService:
    """Collects metrics from DB and produces a CalibrationReport."""

    def __init__(self, conn_factory: Callable[[], _ConnectionProtocol]) -> None:
        self._conn_factory = conn_factory
        self._calibrator = AutoCalibrator()

    def assess(self) -> CalibrationReport:
        conn = self._conn_factory()

        # Correction rate
        correction_rate = 0.0
        try:
            conn.execute(_RATE_SQL)
            row = conn.fetchone()
            if row and row.get("rate_30d") is not None:
                correction_rate = float(row["rate_30d"])
        except Exception as exc:
            logger.warning(
                "CalibrationService: could not read correction rate: %s", exc
            )

        # Pattern count
        pattern_count = 0
        try:
            from src.memory.pattern_detector import PatternDetector

            detector = PatternDetector(lambda: conn)
            patterns = detector.detect_all()
            # Count unresolved patterns (those with high occurrences)
            pattern_count = len([p for p in patterns if p.occurrences >= 3])
        except Exception as exc:
            logger.warning("CalibrationService: could not detect patterns: %s", exc)

        # RAGAS score from baseline file
        ragas_score: float | None = None
        try:
            if _BASELINE_PATH.exists():
                baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
                ragas_score = float(baseline.get("overall", 0.0))
        except Exception as exc:
            logger.warning("CalibrationService: could not read RAGAS baseline: %s", exc)

        return self._calibrator.assess(
            correction_rate_30d=correction_rate,
            pattern_count=pattern_count,
            ragas_score=ragas_score,
        )
