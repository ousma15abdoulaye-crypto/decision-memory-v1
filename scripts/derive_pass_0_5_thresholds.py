#!/usr/bin/env python3
"""
Dérive des statistiques pour PASS_0_5_EMPIRICAL_THRESHOLDS (§1–3).

Lit un ou plusieurs JSONL (export LS m12-v2 ou lignes avec ``source_text``).
Les métriques sont calculées sur le **texte normalisé** (Pass 0), comme Pass 0.5.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.annotation.passes.pass_0_ingestion import run_pass_0_ingestion  # noqa: E402


def _extract_text(obj: dict) -> str:
    if "source_text" in obj and obj["source_text"]:
        return str(obj["source_text"])
    st = obj.get("source_task") or {}
    if isinstance(st, dict) and st.get("text"):
        return str(st["text"])
    # fallback : anciennes lignes sans source_text (export avant m12_export_line)
    return ""


def _metrics(text: str) -> tuple[int, float, int]:
    n = len(text)
    alnum = sum(1 for c in text if c.isalnum())
    non_alnum_ratio = 1.0 - (alnum / n) if n else 0.0
    repl = text.count("\ufffd")
    return n, non_alnum_ratio, repl


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Statistiques char_count / non_alnum / replacement pour seuils Pass 0.5"
    )
    parser.add_argument(
        "jsonl_files",
        nargs="+",
        type=Path,
        help="Fichiers JSONL (une ligne JSON par document)",
    )
    args = parser.parse_args()

    rows: list[tuple[int, float, int]] = []
    for path in args.jsonl_files:
        if not path.is_file():
            print(f"SKIP missing: {path}", file=sys.stderr)
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = _extract_text(obj)
            if not text.strip():
                continue
            rid = uuid.uuid4()
            task_id = (
                (obj.get("ls_meta") or {}).get("task_id")
                if isinstance(obj.get("ls_meta"), dict)
                else None
            )
            doc_id = f"derive:{task_id}" if task_id is not None else f"derive:{rid}"
            p0 = run_pass_0_ingestion(
                text,
                document_id=doc_id,
                run_id=rid,
            )
            if p0.status.value == "failed":
                continue
            normalized = (p0.output_data or {}).get("normalized_text") or ""
            if not normalized.strip():
                continue
            rows.append(_metrics(normalized))

    if not rows:
        print(
            "N=0 — aucun texte exploitable. Ajoutez ``source_text`` aux lignes JSONL."
        )
        return 1

    chars = [r[0] for r in rows]
    ratios = [r[1] for r in rows]
    repls = [r[2] for r in rows]

    def pct_nearest(xs: list[int], p: float) -> float:
        if not xs:
            return 0.0
        s = sorted(xs)
        i = int(round((p / 100.0) * (len(s) - 1)))
        return float(s[i])

    print(f"N={len(rows)}")
    print(
        f"char_count: min={min(chars)} max={max(chars)} "
        f"mean={statistics.mean(chars):.1f}"
    )
    print(
        f"  percentiles p5={pct_nearest(chars, 5):.0f} p25={pct_nearest(chars, 25):.0f} "
        f"p50={pct_nearest(chars, 50):.0f} p75={pct_nearest(chars, 75):.0f} "
        f"p95={pct_nearest(chars, 95):.0f}"
    )
    print(
        f"non_alnum_ratio: min={min(ratios):.4f} max={max(ratios):.4f} "
        f"mean={statistics.mean(ratios):.4f}"
    )
    print(
        f"replacement_char_hits: min={min(repls)} max={max(repls)} "
        f"mean={statistics.mean(repls):.1f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
