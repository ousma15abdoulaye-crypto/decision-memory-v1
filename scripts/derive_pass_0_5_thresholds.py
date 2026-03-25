#!/usr/bin/env python3
"""
Derive Pass 0.5 quality metrics from Label Studio / export JSONL files.

Usage:
  python scripts/derive_pass_0_5_thresholds.py file1.jsonl [file2.jsonl ...]

Each line should be a JSON object containing task text in one of:
  - {"data": {"text": "..."}}
  - {"data": {"content": "..."}}
  - {"text": "..."}

Output: summary stats to stdout (percentiles). Paste into
docs/contracts/annotation/PASS_0_5_EMPIRICAL_THRESHOLDS.md section 3.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path


def _extract_text(obj: dict) -> str:
    data = obj.get("data")
    if isinstance(data, dict):
        t = data.get("text")
        if isinstance(t, str) and t.strip():
            return t
        c = data.get("content")
        if isinstance(c, str) and c.strip():
            return c
    t = obj.get("text")
    if isinstance(t, str):
        return t
    task = obj.get("task")
    if isinstance(task, dict):
        td = task.get("data")
        if isinstance(td, dict):
            t2 = td.get("text") or td.get("content")
            if isinstance(t2, str):
                return t2
    return ""


def _normalize_light(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _metrics(text: str) -> dict[str, float | int]:
    norm = _normalize_light(text)
    chars = len(norm)
    words = len(norm.split()) if norm else 0
    alnum = sum(1 for c in norm if c.isalnum())
    non_alnum_ratio = 1.0 - (alnum / chars) if chars else 0.0
    repl = norm.count("\ufffd")
    return {
        "char_count": chars,
        "word_count": words,
        "non_alnum_ratio": round(non_alnum_ratio, 4),
        "replacement_char_hits": repl,
    }


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv[1:] if not p.startswith("-")]
    if not paths:
        print("Usage: derive_pass_0_5_thresholds.py <file.jsonl> [...]", file=sys.stderr)
        return 2

    all_rows: list[dict[str, float | int]] = []
    for path in paths:
        if not path.is_file():
            print(f"skip missing: {path}", file=sys.stderr)
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"{path}:{line_no}: JSON error {e}", file=sys.stderr)
                continue
            if not isinstance(obj, dict):
                continue
            text = _extract_text(obj)
            if not text.strip():
                continue
            all_rows.append(_metrics(text))

    n = len(all_rows)
    print(f"documents_with_text={n}")
    if n == 0:
        return 0

    chars = sorted(float(r["char_count"]) for r in all_rows)
    ratios = sorted(float(r["non_alnum_ratio"]) for r in all_rows)
    repls = sorted(float(r["replacement_char_hits"]) for r in all_rows)

    for name, vals in (
        ("char_count", chars),
        ("non_alnum_ratio", ratios),
        ("replacement_char_hits", repls),
    ):
        print(
            f"{name}: min={vals[0]:.4g} p25={_percentile(vals, 0.25):.4g} "
            f"p50={_percentile(vals, 0.5):.4g} p75={_percentile(vals, 0.75):.4g} "
            f"p90={_percentile(vals, 0.9):.4g} max={vals[-1]:.4g}"
        )

    if n >= 2:
        print(f"char_count_mean={statistics.mean(chars):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
