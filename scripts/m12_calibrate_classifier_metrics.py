#!/usr/bin/env python3
"""
M12 — Calibration : Pass 0/0.5/1 vs ``document_role`` humain (JSONL exporté).

Exige ``source_text`` sur chaque ligne (merge manuel ou export étendu) et
``dms_annotation.couche_1_routing.document_role`` pour le gold.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.annotation.passes import (  # noqa: E402, I001
    run_pass_0_ingestion,
    run_pass_0_5_quality_gate,
    run_pass_1_router,
)


def _gold_role(line: dict) -> str | None:
    dms = line.get("dms_annotation")
    if not isinstance(dms, dict):
        return None
    c1 = dms.get("couche_1_routing")
    if not isinstance(c1, dict):
        return None
    r = c1.get("document_role")
    return str(r).strip() if r else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Précision/rappel document_role (macro) — Pass 1 déterministe"
    )
    parser.add_argument(
        "jsonl", type=Path, help="JSONL avec source_text + dms_annotation"
    )
    parser.add_argument(
        "--min-threshold",
        type=float,
        default=0.70,
        help="Code de sortie 1 si macro-F1 < seuil (défaut 0.70)",
    )
    args = parser.parse_args()

    if not args.jsonl.is_file():
        print(f"Fichier manquant: {args.jsonl}", file=sys.stderr)
        return 2

    y_true: list[str] = []
    y_pred: list[str] = []

    for raw in args.jsonl.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        line = json.loads(raw)
        text = line.get("source_text") or ""
        gold = _gold_role(line)
        if not text.strip() or not gold:
            continue

        rid = uuid.uuid4()
        doc_id = str(line.get("ls_meta", {}).get("task_id") or "unknown")

        p0 = run_pass_0_ingestion(text, document_id=doc_id, run_id=rid)
        if p0.status.value == "failed":
            continue
        norm = (p0.output_data or {}).get("normalized_text") or ""
        p05 = run_pass_0_5_quality_gate(
            norm,
            document_id=doc_id,
            run_id=rid,
            strict_block_llm_on_poor=True,
        )
        block_llm = bool((p05.output_data or {}).get("block_llm"))
        p1 = run_pass_1_router(
            norm,
            document_id=doc_id,
            run_id=rid,
            block_llm=block_llm,
            filename=line.get("source_filename"),
        )
        pred = (p1.output_data or {}).get("document_role")
        if not pred:
            continue
        y_true.append(gold)
        y_pred.append(str(pred))

    if not y_true:
        print("Aucune ligne complète (source_text + gold).")
        return 1

    labels = sorted(set(y_true) | set(y_pred))
    tp = {c: 0 for c in labels}
    fp = {c: 0 for c in labels}
    fn = {c: 0 for c in labels}
    for t, p in zip(y_true, y_pred, strict=True):
        if t == p:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1

    precisions = []
    recalls = []
    for c in labels:
        p_denom = tp[c] + fp[c]
        r_denom = tp[c] + fn[c]
        prec = tp[c] / p_denom if p_denom else 0.0
        rec = tp[c] / r_denom if r_denom else 0.0
        precisions.append(prec)
        recalls.append(rec)

    macro_p = sum(precisions) / len(precisions) if precisions else 0.0
    macro_r = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = (
        (2 * macro_p * macro_r / (macro_p + macro_r)) if (macro_p + macro_r) else 0.0
    )

    print(f"N={len(y_true)}")
    print(f"macro_precision={macro_p:.4f}")
    print(f"macro_recall={macro_r:.4f}")
    print(f"macro_f1={macro_f1:.4f}")

    if macro_f1 < args.min_threshold:
        # REGLE-23 : viser ≥ 0.70 sur le corpus de calibration
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
