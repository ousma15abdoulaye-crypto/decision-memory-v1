"""Auto-calibrator — monitors system health from correction rates + patterns.

Thresholds (from V2 plan):
- correction_rate > 0.15 → degraded
- correction_rate > 0.30 → critical
- pattern_count > 10 unresolved → degraded
"""

from __future__ import annotations

from src.memory.calibration_models import CalibrationReport, CalibrationStatus

_DEGRADE_RATE = 0.15
_CRITICAL_RATE = 0.30
_DEGRADE_PATTERNS = 10


class AutoCalibrator:
    """Computes calibration status from metrics."""

    def assess(
        self,
        correction_rate_30d: float,
        pattern_count: int,
        ragas_score: float | None = None,
    ) -> CalibrationReport:
        details: list[str] = []
        status = CalibrationStatus.healthy

        if correction_rate_30d > _CRITICAL_RATE:
            status = CalibrationStatus.critical
            details.append(
                f"correction_rate {correction_rate_30d:.2%} > {_CRITICAL_RATE:.0%}"
            )
        elif correction_rate_30d > _DEGRADE_RATE:
            status = CalibrationStatus.degraded
            details.append(
                f"correction_rate {correction_rate_30d:.2%} > {_DEGRADE_RATE:.0%}"
            )

        if pattern_count > _DEGRADE_PATTERNS:
            if status == CalibrationStatus.healthy:
                status = CalibrationStatus.degraded
            details.append(f"unresolved patterns {pattern_count} > {_DEGRADE_PATTERNS}")

        if ragas_score is not None and ragas_score < 0.5:
            if status == CalibrationStatus.healthy:
                status = CalibrationStatus.degraded
            details.append(f"RAGAS score {ragas_score:.2f} < 0.50")

        if not details:
            details.append("all metrics within thresholds")

        return CalibrationReport(
            status=status,
            correction_rate_30d=correction_rate_30d,
            pattern_count=pattern_count,
            ragas_score=ragas_score,
            details=details,
        )
