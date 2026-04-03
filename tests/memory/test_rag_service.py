"""Tests — RAGService (with mock connection)."""

from __future__ import annotations

from typing import Any

from src.memory.rag_models import RAGResult
from src.memory.rag_service import _MAX_RAG_CONFIDENCE, RAGService


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


class TestFindSimilarHybrid:
    def test_returns_results(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {"chunk_text": "passage A", "similarity": 0.9},
                {"chunk_text": "passage B", "similarity": 0.7},
            ]
        )
        svc = RAGService(lambda: conn)
        results = svc.find_similar_hybrid("test query")
        assert len(results) >= 1
        assert "text" in results[0]

    def test_empty_results(self) -> None:
        conn = MockConn()
        conn.set_fetchall([])
        svc = RAGService(lambda: conn)
        results = svc.find_similar_hybrid("no match")
        assert results == []


class TestAnswerWithContext:
    def test_returns_rag_result(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {"chunk_text": "context about procurement", "similarity": 0.8},
            ]
        )
        svc = RAGService(lambda: conn)
        result = svc.answer_with_context("What is the procedure?")
        assert isinstance(result, RAGResult)

    def test_confidence_capped(self) -> None:
        conn = MockConn()
        conn.set_fetchall(
            [
                {"chunk_text": "high confidence context", "similarity": 0.99},
            ]
        )
        svc = RAGService(lambda: conn)
        result = svc.answer_with_context("query")
        assert result.confidence <= _MAX_RAG_CONFIDENCE

    def test_review_always_required(self) -> None:
        conn = MockConn()
        conn.set_fetchall([{"chunk_text": "ctx", "similarity": 0.5}])
        svc = RAGService(lambda: conn)
        result = svc.answer_with_context("q")
        assert result.review_required is True

    def test_no_context_returns_zero_confidence(self) -> None:
        conn = MockConn()
        conn.set_fetchall([])
        svc = RAGService(lambda: conn)
        result = svc.answer_with_context("orphan query")
        assert result.confidence == 0.0
        assert result.review_required is True


class TestRAGResultModel:
    def test_extra_forbid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            RAGResult(answer="a", confidence=0.5, rogue="x")

    def test_confidence_bounds(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RAGResult(answer="a", confidence=1.5)
