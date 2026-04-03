"""RAGAS evaluation harness — stub that runs without ragas dependency.

In production: wraps ragas library for context_precision, faithfulness, answer_relevancy.
In CI/tests: uses stub metrics for deterministic baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RAGASResult:
    context_precision: float
    faithfulness: float
    answer_relevancy: float
    overall: float
    details: dict[str, Any] = field(default_factory=dict)


class RAGASEvaluator:
    """Evaluates RAG output quality against golden dataset."""

    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
    ) -> RAGASResult:
        cp = self._stub_context_precision(contexts, ground_truth)
        faith = self._stub_faithfulness(answer, contexts)
        ar = self._stub_answer_relevancy(question, answer)
        overall = (cp + faith + ar) / 3.0
        return RAGASResult(
            context_precision=round(cp, 4),
            faithfulness=round(faith, 4),
            answer_relevancy=round(ar, 4),
            overall=round(overall, 4),
        )

    def evaluate_batch(self, samples: list[dict[str, Any]]) -> list[RAGASResult]:
        return [
            self.evaluate_single(
                question=s["question"],
                answer=s["answer"],
                contexts=s.get("contexts", []),
                ground_truth=s.get("ground_truth", ""),
            )
            for s in samples
        ]

    def _stub_context_precision(self, contexts: list[str], ground_truth: str) -> float:
        if not contexts or not ground_truth:
            return 0.0
        gt_words = set(ground_truth.lower().split())
        ctx_words = set(" ".join(contexts).lower().split())
        if not gt_words:
            return 0.0
        overlap = len(gt_words & ctx_words) / len(gt_words)
        return min(overlap, 1.0)

    def _stub_faithfulness(self, answer: str, contexts: list[str]) -> float:
        if not answer or not contexts:
            return 0.0
        ans_words = set(answer.lower().split())
        ctx_words = set(" ".join(contexts).lower().split())
        if not ans_words:
            return 0.0
        return min(len(ans_words & ctx_words) / len(ans_words), 1.0)

    def _stub_answer_relevancy(self, question: str, answer: str) -> float:
        if not question or not answer:
            return 0.0
        q_words = set(question.lower().split())
        a_words = set(answer.lower().split())
        if not q_words:
            return 0.0
        return min(len(q_words & a_words) / len(q_words), 1.0)
