"""
M12 Benchmark Harness — bootstrap calibration against annotated corpus.

Runs Pass 1A against every line of the JSONL corpus, compares predictions
to ground-truth taxonomy_core, and produces P/R/F1 + confusion matrix.

Usage:
    python scripts/m12_benchmark_against_corpus.py [--corpus PATH] [--out-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.annotation.passes.pass_1a_core_recognition import (  # noqa: E402
    run_pass_1a_core_recognition,
)
from src.procurement.document_ontology import (  # noqa: E402
    OFFER_KINDS,
    DocumentKindParent,
)
from src.procurement.taxonomy_mapping import corpus_to_parent_subtype  # noqa: E402

DEFAULT_CORPUS = REPO_ROOT / "data" / "annotations" / "m12_corpus_from_ls.jsonl"
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "calibration"

THRESHOLDS_BOOTSTRAP_75 = {
    "document_kind_parent_accuracy_n5": 0.80,
    "evaluation_doc_non_offer_recall": 1.00,
    "framework_detection_accuracy": 0.85,
}


def _load_corpus(path: Path) -> list[dict]:
    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            d = json.loads(raw)
            if not d.get("export_ok"):
                continue
            if not d.get("dms_annotation"):
                continue
            if not d.get("source_text"):
                continue
            lines.append(d)
    return lines


def _ground_truth_parent(entry: dict) -> DocumentKindParent:
    """Extract ground-truth DocumentKindParent from a corpus entry."""
    dms = entry["dms_annotation"]
    c1 = dms.get("couche_1_routing", {})
    corpus_key = c1.get("taxonomy_core", "unknown")
    parent, _ = corpus_to_parent_subtype(corpus_key)
    return parent


def _predicted_parent(entry: dict) -> tuple[DocumentKindParent, float, str]:
    """Run Pass 1A and extract predicted DocumentKindParent."""
    text = entry["source_text"]
    run_id = uuid.uuid4()
    doc_id = entry.get("content_hash", "bench_doc")

    result = run_pass_1a_core_recognition(
        normalized_text=text,
        document_id=doc_id,
        run_id=run_id,
        quality_class="good",
        block_llm=True,
    )

    od = result.output_data
    predicted_str = od.get("taxonomy_core", "unknown")
    try:
        predicted = DocumentKindParent(predicted_str)
    except ValueError:
        predicted = DocumentKindParent.UNKNOWN

    confidence = od.get("routing_confidence", 0.0)
    rule = od.get("matched_rule", "none")
    return predicted, confidence, rule


def _compute_metrics(
    y_true: list[DocumentKindParent],
    y_pred: list[DocumentKindParent],
) -> dict:
    """Compute per-class P/R/F1, macro averages, and accuracy."""
    all_labels = sorted(set(y_true) | set(y_pred), key=lambda x: x.value)
    tp: Counter[DocumentKindParent] = Counter()
    fp: Counter[DocumentKindParent] = Counter()
    fn: Counter[DocumentKindParent] = Counter()
    label_counts: Counter[DocumentKindParent] = Counter(y_true)

    for true, pred in zip(y_true, y_pred):
        if true == pred:
            tp[true] += 1
        else:
            fn[true] += 1
            fp[pred] += 1

    per_class = {}
    for label in all_labels:
        p = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) > 0 else 0.0
        r = tp[label] / (tp[label] + fn[label]) if (tp[label] + fn[label]) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        per_class[label.value] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "support": label_counts[label],
        }

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) if y_true else 0.0

    classes_n5 = [lbl for lbl in all_labels if label_counts[lbl] >= 5]
    if classes_n5:
        correct_n5 = sum(
            1 for t, p in zip(y_true, y_pred) if t == p and label_counts[t] >= 5
        )
        total_n5 = sum(1 for t in y_true if label_counts[t] >= 5)
        accuracy_n5 = correct_n5 / total_n5 if total_n5 > 0 else 0.0
    else:
        accuracy_n5 = 0.0

    macro_p = (
        sum(per_class[lbl.value]["precision"] for lbl in all_labels) / len(all_labels)
        if all_labels
        else 0.0
    )
    macro_r = (
        sum(per_class[lbl.value]["recall"] for lbl in all_labels) / len(all_labels)
        if all_labels
        else 0.0
    )
    macro_f1 = (
        sum(per_class[lbl.value]["f1"] for lbl in all_labels) / len(all_labels)
        if all_labels
        else 0.0
    )

    return {
        "accuracy_global": round(accuracy, 4),
        "accuracy_n5_types": round(accuracy_n5, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "types_n5": [lbl.value for lbl in classes_n5],
        "types_below_n5": [lbl.value for lbl in all_labels if label_counts[lbl] < 5],
    }


def _build_confusion_matrix(
    y_true: list[DocumentKindParent],
    y_pred: list[DocumentKindParent],
) -> dict:
    all_labels = sorted(set(y_true) | set(y_pred), key=lambda x: x.value)
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t, p in zip(y_true, y_pred):
        matrix[t.value][p.value] += 1
    return {
        "labels": [lbl.value for lbl in all_labels],
        "matrix": {k: dict(v) for k, v in matrix.items()},
    }


def _check_fatal_eval_doc_not_offer(
    y_true: list[DocumentKindParent],
    y_pred: list[DocumentKindParent],
) -> dict:
    """Fatal check: evaluation_doc must NEVER be classified as offer_*."""
    eval_indices = [
        i for i, t in enumerate(y_true) if t == DocumentKindParent.EVALUATION_DOC
    ]
    violations = []
    for i in eval_indices:
        if y_pred[i] in OFFER_KINDS:
            violations.append(
                {
                    "index": i,
                    "ground_truth": y_true[i].value,
                    "predicted": y_pred[i].value,
                }
            )
    total_eval = len(eval_indices)
    recall_non_offer = (
        1.0 if not violations else (total_eval - len(violations)) / total_eval
    )
    return {
        "total_evaluation_doc": total_eval,
        "violations_as_offer": violations,
        "recall_non_offer": round(recall_non_offer, 4),
        "fatal_pass": len(violations) == 0,
    }


def _check_framework_accuracy(entries: list[dict]) -> dict:
    """Measure framework detection accuracy against corpus procurement_family hints."""
    correct = 0
    total = 0
    distribution: Counter[str] = Counter()
    for entry in entries:
        dms = entry["dms_annotation"]
        c1 = dms.get("couche_1_routing", {})
        fam = c1.get("procurement_family_main", "MISSING")

        result = run_pass_1a_core_recognition(
            normalized_text=entry["source_text"],
            document_id=entry.get("content_hash", "fw_bench"),
            run_id=uuid.uuid4(),
            quality_class="good",
            block_llm=True,
        )
        m12_rec = result.output_data.get("m12_recognition", {})
        fw = m12_rec.get("framework_detected", {}).get("value", "unknown")
        distribution[fw] += 1
        if fam != "MISSING" and fam != "NOT_APPLICABLE":
            total += 1
            if fw != "unknown":
                correct += 1

    accuracy = correct / total if total > 0 else 0.0
    return {
        "framework_accuracy": round(accuracy, 4),
        "total_assessable": total,
        "distribution": dict(distribution.most_common()),
    }


def _format_markdown_report(
    metrics: dict,
    confusion: dict,
    fatal_check: dict,
    fw_check: dict,
    threshold_results: dict,
    corpus_size: int,
    timestamp: str,
) -> str:
    lines = [
        f"# M12 Benchmark — bootstrap_{corpus_size}",
        "",
        f"**Date**: {timestamp}",
        f"**Corpus**: {corpus_size} annotations (export_ok=100%)",
        "",
        "## Threshold Checks",
        "",
        "| Check | Target | Actual | Pass |",
        "|-------|--------|--------|------|",
    ]
    for name, info in threshold_results.items():
        mark = "PASS" if info["pass"] else "**FAIL**"
        lines.append(
            f"| {name} | {info['target']:.2f} | {info['actual']:.4f} | {mark} |"
        )

    lines += [
        "",
        "## Global Metrics",
        "",
        f"- Accuracy (global): **{metrics['accuracy_global']:.4f}**",
        f"- Accuracy (n>=5 types): **{metrics['accuracy_n5_types']:.4f}**",
        f"- Macro P/R/F1: {metrics['macro_precision']:.4f} / {metrics['macro_recall']:.4f} / {metrics['macro_f1']:.4f}",
        f"- Types with n>=5: {metrics['types_n5']}",
        f"- Types below n<5: {metrics['types_below_n5']}",
        "",
        "## Per-Class Metrics",
        "",
        "| Type | P | R | F1 | Support |",
        "|------|---|---|----|---------| ",
    ]
    for cls, vals in sorted(metrics["per_class"].items()):
        lines.append(
            f"| {cls} | {vals['precision']:.4f} | {vals['recall']:.4f} | "
            f"{vals['f1']:.4f} | {vals['support']} |"
        )

    lines += [
        "",
        "## Confusion Matrix",
        "",
        "Rows = ground truth, Cols = predicted",
        "",
    ]
    labels = confusion["labels"]
    header = "| |" + "|".join(labels) + "|"
    sep = "|---|" + "|".join(["---"] * len(labels)) + "|"
    lines.append(header)
    lines.append(sep)
    for row_label in labels:
        row_data = confusion["matrix"].get(row_label, {})
        cells = [str(row_data.get(c, 0)) for c in labels]
        lines.append(f"| {row_label} |" + "|".join(cells) + "|")

    lines += [
        "",
        "## Fatal Check: evaluation_doc != offer_*",
        "",
        f"- Total evaluation_doc samples: {fatal_check['total_evaluation_doc']}",
        f"- Violations (classified as offer): {len(fatal_check['violations_as_offer'])}",
        f"- Non-offer recall: {fatal_check['recall_non_offer']:.4f}",
        f"- **{'PASS' if fatal_check['fatal_pass'] else 'FATAL FAIL'}**",
        "",
        "## Framework Detection",
        "",
        f"- Accuracy: {fw_check['framework_accuracy']:.4f}",
        f"- Total assessable: {fw_check['total_assessable']}",
        f"- Distribution: {fw_check['distribution']}",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="M12 benchmark harness")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="Path to JSONL corpus",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for results",
    )
    args = parser.parse_args()

    corpus = _load_corpus(args.corpus)
    if not corpus:
        print("ERROR: No valid corpus entries found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(corpus)} corpus entries from {args.corpus}")

    y_true: list[DocumentKindParent] = []
    y_pred: list[DocumentKindParent] = []
    details: list[dict] = []

    for i, entry in enumerate(corpus):
        gt = _ground_truth_parent(entry)
        pred, conf, rule = _predicted_parent(entry)
        y_true.append(gt)
        y_pred.append(pred)
        match = "OK" if gt == pred else "MISS"
        details.append(
            {
                "index": i,
                "ground_truth": gt.value,
                "predicted": pred.value,
                "confidence": conf,
                "rule": rule,
                "match": match,
            }
        )
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(corpus)}...")

    print(f"  Processed {len(corpus)}/{len(corpus)} — computing metrics...")

    metrics = _compute_metrics(y_true, y_pred)
    confusion = _build_confusion_matrix(y_true, y_pred)
    fatal_check = _check_fatal_eval_doc_not_offer(y_true, y_pred)
    fw_check = _check_framework_accuracy(corpus)

    threshold_results = {
        "document_kind_parent_accuracy_n5": {
            "target": THRESHOLDS_BOOTSTRAP_75["document_kind_parent_accuracy_n5"],
            "actual": metrics["accuracy_n5_types"],
            "pass": metrics["accuracy_n5_types"]
            >= THRESHOLDS_BOOTSTRAP_75["document_kind_parent_accuracy_n5"],
        },
        "evaluation_doc_non_offer_recall": {
            "target": THRESHOLDS_BOOTSTRAP_75["evaluation_doc_non_offer_recall"],
            "actual": fatal_check["recall_non_offer"],
            "pass": fatal_check["recall_non_offer"]
            >= THRESHOLDS_BOOTSTRAP_75["evaluation_doc_non_offer_recall"],
        },
        "framework_detection_accuracy": {
            "target": THRESHOLDS_BOOTSTRAP_75["framework_detection_accuracy"],
            "actual": fw_check["framework_accuracy"],
            "pass": fw_check["framework_accuracy"]
            >= THRESHOLDS_BOOTSTRAP_75["framework_detection_accuracy"],
        },
    }

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    json_report = {
        "benchmark": f"bootstrap_{len(corpus)}",
        "timestamp": timestamp,
        "corpus_size": len(corpus),
        "thresholds": THRESHOLDS_BOOTSTRAP_75,
        "threshold_results": threshold_results,
        "metrics": metrics,
        "confusion_matrix": confusion,
        "fatal_check_eval_doc": fatal_check,
        "framework_check": fw_check,
        "details": details,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"benchmark_bootstrap_{len(corpus)}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    print(f"JSON report: {json_path}")

    md_report = _format_markdown_report(
        metrics,
        confusion,
        fatal_check,
        fw_check,
        threshold_results,
        len(corpus),
        timestamp,
    )
    md_path = args.out_dir / f"benchmark_bootstrap_{len(corpus)}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report: {md_path}")

    all_pass = all(v["pass"] for v in threshold_results.values())
    if all_pass:
        print("\nALL THRESHOLDS PASSED")
    else:
        failed = [k for k, v in threshold_results.items() if not v["pass"]]
        print(f"\nTHRESHOLDS FAILED: {failed}")
        sys.exit(2)


if __name__ == "__main__":
    main()
