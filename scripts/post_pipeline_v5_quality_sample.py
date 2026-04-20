#!/usr/bin/env python3
"""Échantillon aléatoire d'assessments M14 pour revue humaine (qualité scores).

Usage::

  python scripts/post_pipeline_v5_quality_sample.py <workspace_uuid> [--n 10] [--out report.json]

Remplir ensuite le champ ``expert_label`` (correct / incorrect / partiel) dans le JSON
ou dans une feuille de suivi, puis calculer le taux de justesse.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

from src.db import db_fetchall, get_connection


def _cell_snippet(cell: Any, max_len: int = 240) -> str:
    if cell is None:
        return ""
    if isinstance(cell, dict):
        raw = json.dumps(cell, ensure_ascii=False)
    else:
        raw = str(cell)
    return raw[:max_len]


def run_sample(workspace_id: str, n: int, out_path: str) -> None:
    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT id::text AS id,
                   bundle_id::text AS bundle_id,
                   criterion_key,
                   cell_json,
                   dao_criterion_id::text AS dao_criterion_id
            FROM criterion_assessments
            WHERE workspace_id = CAST(:wid AS uuid)
              AND cell_json->>'source' = 'm14'
            ORDER BY random()
            LIMIT :lim
            """,
            {"wid": workspace_id, "lim": max(1, n)},
        )

    if not rows:
        print("Aucun assessment avec cell_json.source=m14.")
        return

    pick = rows
    report: dict[str, Any] = {
        "workspace_id": workspace_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "sample_size": len(pick),
        "instructions": (
            "Pour chaque item, l'expert renseigne expert_label ∈ "
            "{correct, incorrect, partiel} puis on calcule le taux de correct+partiel."
        ),
        "items": [],
    }

    for r in pick:
        cj = r.get("cell_json") if isinstance(r.get("cell_json"), dict) else {}
        report["items"].append(
            {
                "assessment_id": r["id"],
                "bundle_id": r.get("bundle_id"),
                "criterion_key": r.get("criterion_key"),
                "dao_criterion_id": r.get("dao_criterion_id"),
                "m14_score": cj.get("score"),
                "confidence": cj.get("confidence"),
                "snippet": _cell_snippet(cj),
                "expert_label": None,
                "expert_notes": None,
            }
        )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Rapport écrit : {out_path} ({len(pick)} assessments)")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace_id")
    p.add_argument("--n", type=int, default=10, help="Taille de l'échantillon")
    p.add_argument(
        "--out",
        default="",
        help="Fichier JSON de sortie (défaut: quality_report_<workspace>.json)",
    )
    args = p.parse_args()
    wid = args.workspace_id.strip()
    out = args.out or f"quality_report_{wid}.json"
    try:
        run_sample(wid, max(1, args.n), out)
    except Exception as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
