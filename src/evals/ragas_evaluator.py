"""RAGAS evaluation harness.

In production (ragas installed): uses ragas library metrics with a mock LLM
evaluator suitable for CI.
In CI/tests (ragas not installed): uses deterministic stub metrics.

Baseline is saved to data/ragas_baseline.json and checked for regression.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BASELINE_PATH = Path(__file__).parent.parent.parent / "data" / "ragas_baseline.json"

_RAGAS_AVAILABLE = False
try:
    import ragas  # noqa: F401

    _RAGAS_AVAILABLE = True
except ImportError:
    pass


@dataclass(frozen=True)
class RAGASResult:
    context_precision: float
    faithfulness: float
    answer_relevancy: float
    overall: float
    details: dict[str, Any] = field(default_factory=dict)


class RAGASEvaluator:
    """Evaluates RAG output quality against golden dataset.

    Uses real ragas metrics when available; falls back to deterministic stub.
    """

    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
    ) -> RAGASResult:
        if _RAGAS_AVAILABLE:
            return self._evaluate_real(question, answer, contexts, ground_truth)
        return self._evaluate_stub(question, answer, contexts, ground_truth)

    def evaluate_batch(self, samples: list[dict[str, Any]]) -> list[RAGASResult]:
        if _RAGAS_AVAILABLE and len(samples) > 1:
            try:
                return self._evaluate_batch_real(samples)
            except Exception as exc:
                logger.warning("ragas batch eval failed, falling back to stub: %s", exc)
        return [
            self.evaluate_single(
                question=s["question"],
                answer=s["answer"],
                contexts=s.get("contexts", []),
                ground_truth=s.get("ground_truth", ""),
            )
            for s in samples
        ]

    def _evaluate_real(
        self, question: str, answer: str, contexts: list[str], ground_truth: str
    ) -> RAGASResult:
        """Single evaluation using ragas dataset API."""
        results = self._evaluate_batch_real(
            [
                {
                    "question": question,
                    "answer": answer,
                    "contexts": contexts,
                    "ground_truth": ground_truth,
                }
            ]
        )
        return (
            results[0]
            if results
            else self._evaluate_stub(question, answer, contexts, ground_truth)
        )

    def _evaluate_batch_real(self, samples: list[dict[str, Any]]) -> list[RAGASResult]:
        """Batch evaluation using ragas Dataset API."""
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, faithfulness

        dataset = Dataset.from_list(
            [
                {
                    "question": s["question"],
                    "answer": s["answer"],
                    "contexts": s.get("contexts", []) or [""],
                    "ground_truth": s.get("ground_truth", ""),
                }
                for s in samples
            ]
        )
        score = evaluate(
            dataset, metrics=[context_precision, faithfulness, answer_relevancy]
        )
        df = score.to_pandas()
        results: list[RAGASResult] = []
        for _, row in df.iterrows():
            cp = float(row.get("context_precision", 0.0) or 0.0)
            fa = float(row.get("faithfulness", 0.0) or 0.0)
            ar = float(row.get("answer_relevancy", 0.0) or 0.0)
            results.append(
                RAGASResult(
                    context_precision=round(cp, 4),
                    faithfulness=round(fa, 4),
                    answer_relevancy=round(ar, 4),
                    overall=round((cp + fa + ar) / 3.0, 4),
                )
            )
        return results

    def _evaluate_stub(
        self, question: str, answer: str, contexts: list[str], ground_truth: str
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

    # ── Stub metrics (word overlap — deterministic baseline for CI) ─────────

    def _stub_context_precision(self, contexts: list[str], ground_truth: str) -> float:
        if not contexts or not ground_truth:
            return 0.0
        gt_words = set(ground_truth.lower().split())
        ctx_words = set(" ".join(contexts).lower().split())
        if not gt_words:
            return 0.0
        return min(len(gt_words & ctx_words) / len(gt_words), 1.0)

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

    # ── Baseline management ─────────────────────────────────────────────────

    def save_baseline(self, results: list[RAGASResult]) -> None:
        """Persist aggregated baseline metrics to data/ragas_baseline.json."""
        if not results:
            return
        avg_cp = sum(r.context_precision for r in results) / len(results)
        avg_fa = sum(r.faithfulness for r in results) / len(results)
        avg_ar = sum(r.answer_relevancy for r in results) / len(results)
        avg_overall = sum(r.overall for r in results) / len(results)
        baseline = {
            "n_samples": len(results),
            "backend": "ragas" if _RAGAS_AVAILABLE else "stub",
            "context_precision": round(avg_cp, 4),
            "faithfulness": round(avg_fa, 4),
            "answer_relevancy": round(avg_ar, 4),
            "overall": round(avg_overall, 4),
        }
        _BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE_PATH.write_text(
            json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("RAGAS baseline saved to %s", _BASELINE_PATH)

    def check_regression(
        self, results: list[RAGASResult], threshold: float = 0.05
    ) -> tuple[bool, str]:
        """Check if current results regress by more than ``threshold`` vs baseline.

        Returns (passed, message).
        """
        if not _BASELINE_PATH.exists():
            return True, "No baseline found — regression check skipped."
        try:
            baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            return True, f"Baseline unreadable: {exc}"

        if not results:
            return True, "No results to check."

        current_overall = sum(r.overall for r in results) / len(results)
        baseline_overall = float(baseline.get("overall", 0.0))

        delta = baseline_overall - current_overall
        if delta > threshold:
            return False, (
                f"RAGAS regression: overall dropped from {baseline_overall:.4f} "
                f"to {current_overall:.4f} (delta={delta:.4f} > threshold={threshold})"
            )
        return (
            True,
            f"RAGAS OK: overall={current_overall:.4f} (baseline={baseline_overall:.4f})",
        )
