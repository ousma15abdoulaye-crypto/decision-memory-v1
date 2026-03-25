#!/usr/bin/env python3
"""
Reconstruit data/ingest/test_mistral_output/skipped.json à partir du tableau figé
docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md

Les chemins `path` sont des placeholders : remplacer par un run réel de
ingest_to_annotation_bridge.py quand les PDFs sont disponibles localement.

Compte les lignes du tableau et affiche 81 vs 84 (nom de fichier seul dans le freeze).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

TABLE_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*$")


def parse_freeze_table(md_text: str) -> list[dict]:
    rows: list[dict] = []
    for line in md_text.splitlines():
        m = TABLE_ROW.match(line.strip())
        if not m:
            continue
        idx, process_name, filename, reason = (
            m.group(1),
            m.group(2).strip(),
            m.group(3).strip(),
            m.group(4).strip(),
        )
        if not filename.endswith(".pdf"):
            continue
        placeholder_path = f"<SOURCE_ROOT>/{process_name}/{filename}".replace("//", "/")
        rows.append(
            {
                "path": placeholder_path,
                "process_name": process_name,
                "reason": reason,
                "classification": "scanned_pdf",
                "engine_route": "blocked",
                "freeze_row": int(idx),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--freeze-md",
        type=Path,
        default=_PROJECT_ROOT
        / "docs"
        / "freeze"
        / "M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_PROJECT_ROOT
        / "data"
        / "ingest"
        / "test_mistral_output"
        / "skipped.json",
    )
    args = parser.parse_args()

    if not args.freeze_md.is_file():
        print(f"Missing {args.freeze_md}", file=sys.stderr)
        return 1

    text = args.freeze_md.read_text(encoding="utf-8")
    rows = parse_freeze_table(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Rows parsed: {len(rows)}")
    print(f"Written: {args.output}")
    print(
        "Note: paths are placeholders; regenerate from ingest_to_annotation_bridge "
        "when PDFs are on disk."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
