"""Tests — Reranker (stub backend)."""

from __future__ import annotations

from src.memory.reranker import RerankedResult, Reranker


class TestReranker:
    def test_empty_passages(self) -> None:
        r = Reranker()
        assert r.rerank("query", []) == []

    def test_returns_reranked_results(self) -> None:
        r = Reranker()
        results = r.rerank("query", ["a", "b", "c"])
        assert len(results) == 3
        assert isinstance(results[0], RerankedResult)

    def test_top_k_limits(self) -> None:
        r = Reranker()
        results = r.rerank("q", ["a", "b", "c", "d", "e", "f"], top_k=3)
        assert len(results) == 3

    def test_stub_scores_descending(self) -> None:
        r = Reranker()
        results = r.rerank("q", ["a", "b", "c"])
        scores = [rr.score for rr in results]
        assert scores == sorted(scores, reverse=True)

    def test_original_rank_preserved(self) -> None:
        r = Reranker()
        results = r.rerank("q", ["first", "second"])
        assert results[0].original_rank == 0
        assert results[0].text == "first"

    def test_single_passage(self) -> None:
        r = Reranker()
        results = r.rerank("q", ["only"])
        assert len(results) == 1
        assert results[0].score == 1.0
