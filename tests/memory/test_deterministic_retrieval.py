"""Tests — DeterministicRetrieval (find_similar_cases)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.memory.deterministic_retrieval import DeterministicRetrieval


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


class TestFindSimilarCases:
    def test_returns_results(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {
                    "case_id": "CASE-002",
                    "content_json": json.dumps(
                        {
                            "framework_detected": "sci",
                            "procurement_family": "goods",
                        }
                    ),
                    "similarity_score": 1.0,
                }
            ]
        )
        retrieval = DeterministicRetrieval(lambda: conn)
        results = retrieval.find_similar_cases("CASE-001")
        assert len(results) == 1
        assert results[0]["case_id"] == "CASE-002"
        assert results[0]["framework"] == "sci"
        assert results[0]["similarity_score"] == 1.0

    def test_empty_result(self) -> None:
        conn = MockConn()
        conn.set_fetchall([])
        retrieval = DeterministicRetrieval(lambda: conn)
        assert retrieval.find_similar_cases("CASE-001") == []

    def test_limit_validation(self) -> None:
        conn = MockConn()
        retrieval = DeterministicRetrieval(lambda: conn)
        with pytest.raises(ValueError, match="limit must be >= 1"):
            retrieval.find_similar_cases("C", limit=0)

    def test_content_json_as_dict(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {
                    "case_id": "C2",
                    "content_json": {
                        "framework_detected": "dgmp_mali",
                        "procurement_family": "works",
                    },
                    "similarity_score": 0.7,
                }
            ]
        )
        retrieval = DeterministicRetrieval(lambda: conn)
        results = retrieval.find_similar_cases("C1")
        assert results[0]["framework"] == "dgmp_mali"

    def test_sql_references_memory_entries(self) -> None:
        conn = MockConn()
        conn.set_fetchall([])
        retrieval = DeterministicRetrieval(lambda: conn)
        retrieval.find_similar_cases("C1")
        assert "memory_entries" in conn.last_sql
