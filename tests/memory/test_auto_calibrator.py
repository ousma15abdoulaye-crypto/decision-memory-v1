"""Tests — AutoCalibrator."""

from __future__ import annotations

from src.memory.auto_calibrator import AutoCalibrator
from src.memory.calibration_models import CalibrationReport, CalibrationStatus


class TestAssess:
    def test_healthy(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.05, pattern_count=2)
        assert report.status == CalibrationStatus.healthy
        assert "within thresholds" in report.details[0]

    def test_degraded_by_rate(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.20, pattern_count=0)
        assert report.status == CalibrationStatus.degraded

    def test_critical_by_rate(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.35, pattern_count=0)
        assert report.status == CalibrationStatus.critical

    def test_degraded_by_patterns(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.05, pattern_count=15)
        assert report.status == CalibrationStatus.degraded

    def test_ragas_low_triggers_degraded(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.05, pattern_count=0, ragas_score=0.3)
        assert report.status == CalibrationStatus.degraded

    def test_ragas_ok_stays_healthy(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.05, pattern_count=0, ragas_score=0.8)
        assert report.status == CalibrationStatus.healthy

    def test_returns_calibration_report(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.10, pattern_count=5)
        assert isinstance(report, CalibrationReport)

    def test_critical_overrides_pattern_degraded(self) -> None:
        cal = AutoCalibrator()
        report = cal.assess(correction_rate_30d=0.35, pattern_count=15)
        assert report.status == CalibrationStatus.critical


class TestCalibrationReportModel:
    def test_extra_forbid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            CalibrationReport(
                status=CalibrationStatus.healthy,
                correction_rate_30d=0.0,
                pattern_count=0,
                rogue="x",
            )
