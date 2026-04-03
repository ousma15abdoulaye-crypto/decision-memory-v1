"""Run RAGAS evaluation against golden dataset and print summary."""

from __future__ import annotations

from src.evals.golden_dataset_loader import GoldenDatasetLoader
from src.evals.ragas_evaluator import RAGASEvaluator


def main() -> None:
    loader = GoldenDatasetLoader()
    count = loader.count()
    print(f"Golden dataset: {count} cases")

    if count == 0:
        print("No cases found. Skipping evaluation.")
        return

    evaluator = RAGASEvaluator()
    samples = loader.load_all()

    eval_samples = []
    for s in samples:
        case = s["case"]
        expected = s["expected"]
        eval_samples.append(
            {
                "question": case.get("description", ""),
                "answer": expected.get("expected_regime", {}).get("procedure_type", ""),
                "contexts": [case.get("description", "")],
                "ground_truth": expected.get("expected_regime", {}).get(
                    "procedure_type", ""
                ),
            }
        )

    results = evaluator.evaluate_batch(eval_samples)

    print(f"\n{'Case':<12} {'CP':>6} {'Faith':>6} {'AR':>6} {'Overall':>8}")
    print("-" * 42)
    for i, r in enumerate(results):
        print(
            f"case_{i+1:03d}     {r.context_precision:>6.4f} {r.faithfulness:>6.4f} "
            f"{r.answer_relevancy:>6.4f} {r.overall:>8.4f}"
        )

    avg = sum(r.overall for r in results) / len(results) if results else 0
    print(f"\nAverage overall: {avg:.4f}")
    print("RAGAS baseline defined." if results else "No results.")


if __name__ == "__main__":
    main()
