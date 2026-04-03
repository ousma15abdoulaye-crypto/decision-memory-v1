"""Tests — PatternDetector (correction clusters)."""

from __future__ import annotations

from typing import Any

import pytest

from src.memory.pattern_detector import PatternDetector, _cluster_confidence
from src.memory.pattern_models import DetectedPattern, PatternType


class MockConn:
    def __init__(self) -> None:
        self.last_sql: str = ""
        self.last_params: dict[str, Any] | None = None
        self._fetchall_result: list[dict[str, Any]] = []

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        self.last_sql = sql
        self.last_params = params

    def fetchone(self) -> dict[str, Any] | None:
        return None

    def fetchall(self) -> list[dict[str, Any]]:
        return self._fetchall_result

    def set_fetchall(self, result: list[dict[str, Any]]) -> None:
        self._fetchall_result = result


class TestCorrectionClusters:
    def test_returns_patterns(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {
                    "field_path": "regime.procedure_type",
                    "occurrences": 5,
                    "first_seen": "2026-01-01",
                    "last_seen": "2026-03-01",
                }
            ]
        )
        pd = PatternDetector(lambda: conn)
        patterns = pd.detect_correction_clusters(min_occurrences=3)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.correction_cluster
        assert patterns[0].occurrences == 5
        assert patterns[0].field_path == "regime.procedure_type"

    def test_empty_result(self) -> None:
        conn = MockConn()
        conn.set_fetchall([])
        pd = PatternDetector(lambda: conn)
        assert pd.detect_correction_clusters() == []

    def test_min_occurrences_validation(self) -> None:
        conn = MockConn()
        pd = PatternDetector(lambda: conn)
        with pytest.raises(ValueError, match="min_occurrences"):
            pd.detect_correction_clusters(min_occurrences=0)


class TestDetectAll:
    def test_merges_results(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {
                    "field_path": "fp",
                    "occurrences": 3,
                    "first_seen": "2026-01-01",
                    "last_seen": "2026-03-01",
                }
            ]
        )
        pd = PatternDetector(lambda: conn)
        all_patterns = pd.detect_all()
        assert len(all_patterns) >= 1


class TestClusterConfidence:
    def test_low_occurrences(self) -> None:
        assert _cluster_confidence(1) == pytest.approx(0.52)

    def test_high_occurrences_capped(self) -> None:
        assert _cluster_confidence(100) <= 1.0

    def test_five_occurrences(self) -> None:
        assert _cluster_confidence(5) == pytest.approx(1.0)


class TestDetectedPatternModel:
    def test_extra_forbid(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            DetectedPattern(
                pattern_type=PatternType.correction_cluster,
                field_path="fp",
                occurrences=1,
                confidence=0.5,
                description="d",
                first_seen="a",
                last_seen="b",
                rogue="x",
            )
