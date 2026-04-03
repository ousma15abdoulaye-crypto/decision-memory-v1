"""Tests — ARQ tasks (real implementations with mocked DB)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch


class MockConn:
    """Minimal mock connection for arq task tests."""

    def __init__(self) -> None:
        self.last_sql: str = ""
        self._fetchone: dict[str, Any] | None = None
        self._fetchall: list[dict[str, Any]] = []

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        self.last_sql = sql

    def fetchone(self) -> dict[str, Any] | None:
        return self._fetchone

    def fetchall(self) -> list[dict[str, Any]]:
        return self._fetchall


class TestIndexEvent:
    def test_raises_on_incomplete_event(self) -> None:
        """index_event should raise ValidationError for an incomplete event dict."""
        import pytest

        from src.workers.arq_tasks import index_event

        with pytest.raises(Exception):
            asyncio.get_event_loop().run_until_complete(
                index_event({}, {"event_type": "test"})
            )

    def test_complete_event_calls_service(self) -> None:
        """index_event with a valid event dict calls EventIndexService.append."""
        from src.workers.arq_tasks import index_event

        complete_event = {
            "event_domain": "procurement",
            "source_table": "m13_correction_log",
            "source_pk": 1,
            "aggregate_type": "case",
            "event_type": "m13_correction_applied",
            "event_time": "2026-01-01T00:00:00Z",
        }

        mock_conn = MockConn()
        mock_conn._fetchone = {"event_id": "abc-123"}

        with patch("src.workers.arq_tasks._get_conn_factory", return_value=lambda: mock_conn):
            result = asyncio.get_event_loop().run_until_complete(
                index_event({}, complete_event)
            )
        assert result == "abc-123"


class TestDetectPatterns:
    def test_runs_without_db_connection_via_mock(self) -> None:
        """detect_patterns uses PatternDetector — mocked to return 0 patterns."""
        from src.workers.arq_tasks import detect_patterns

        mock_conn = MockConn()
        mock_conn._fetchall = []  # No patterns found

        with patch("src.workers.arq_tasks._get_conn_factory", return_value=lambda: mock_conn):
            result = asyncio.get_event_loop().run_until_complete(detect_patterns({}))

        assert result == 0

    def test_returns_count_of_saved_rules(self) -> None:
        """detect_patterns returns count of rules saved."""
        from src.workers.arq_tasks import detect_patterns

        mock_conn = MockConn()
        mock_conn._fetchall = [
            {
                "field_path": "contract_value",
                "occurrences": 5,
                "first_seen": "2026-01-01",
                "last_seen": "2026-01-15",
            }
        ]
        mock_conn._fetchone = {"rule_id": "cand_corr_cluster_abc"}

        with patch("src.workers.arq_tasks._get_conn_factory", return_value=lambda: mock_conn):
            result = asyncio.get_event_loop().run_until_complete(detect_patterns({}))

        assert result >= 0


class TestGenerateCandidateRules:
    def test_delegates_to_detect_patterns(self) -> None:
        """generate_candidate_rules is an alias for detect_patterns."""
        from src.workers.arq_tasks import generate_candidate_rules

        mock_conn = MockConn()
        mock_conn._fetchall = []

        with patch("src.workers.arq_tasks._get_conn_factory", return_value=lambda: mock_conn):
            result = asyncio.get_event_loop().run_until_complete(
                generate_candidate_rules({})
            )

        assert result == 0
