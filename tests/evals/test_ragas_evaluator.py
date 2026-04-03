"""Tests — RAGASEvaluator (stub metrics)."""

from __future__ import annotations

from src.evals.ragas_evaluator import RAGASEvaluator, RAGASResult


class TestEvaluateSingle:
    def test_returns_ragas_result(self) -> None:
        ev = RAGASEvaluator()
        result = ev.evaluate_single(
            question="What is the regime?",
            answer="open tender",
            contexts=["open tender procedure"],
            ground_truth="open tender",
        )
        assert isinstance(result, RAGASResult)
        assert 0.0 <= result.overall <= 1.0

    def test_perfect_overlap(self) -> None:
        ev = RAGASEvaluator()
        result = ev.evaluate_single(
            question="hello",
            answer="hello",
            contexts=["hello"],
            ground_truth="hello",
        )
        assert result.context_precision == 1.0
        assert result.faithfulness == 1.0
        assert result.answer_relevancy == 1.0

    def test_no_overlap(self) -> None:
        ev = RAGASEvaluator()
        result = ev.evaluate_single(
            question="alpha",
            answer="beta",
            contexts=["gamma"],
            ground_truth="delta",
        )
        assert result.overall < 0.5

    def test_empty_inputs(self) -> None:
        ev = RAGASEvaluator()
        result = ev.evaluate_single(
            question="", answer="", contexts=[], ground_truth=""
        )
        assert result.overall == 0.0


class TestEvaluateBatch:
    def test_batch_returns_list(self) -> None:
        ev = RAGASEvaluator()
        samples = [
            {
                "question": "Q1",
                "answer": "A1",
                "contexts": ["C1"],
                "ground_truth": "A1",
            },
            {
                "question": "Q2",
                "answer": "A2",
                "contexts": ["C2"],
                "ground_truth": "A2",
            },
        ]
        results = ev.evaluate_batch(samples)
        assert len(results) == 2

    def test_empty_batch(self) -> None:
        ev = RAGASEvaluator()
        assert ev.evaluate_batch([]) == []
