#!/usr/bin/env python3
"""
Inventaire détaillé d'un JSONL corpus M12 (export R2, LS, ou DMS brut).

Usage (racine du dépôt) :
  python scripts/inventory_m12_corpus_jsonl.py data/annotations/m12_corpus_r2.jsonl
  python scripts/inventory_m12_corpus_jsonl.py data/annotations/fixtures/golden_dms_line.jsonl

Ne loggue pas le texte source (privacy) : longueurs et métadonnées uniquement.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.annotation.m12_export_io import (  # noqa: E402
    dms_annotation_from_line,
    export_line_kind,
    iter_m12_jsonl_lines,
)


def _meta(dms: dict) -> dict:
    return dms.get("_meta") if isinstance(dms.get("_meta"), dict) else {}


def _routing(dms: dict) -> dict:
    return dms.get("couche_1_routing") if isinstance(dms.get("couche_1_routing"), dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Inventaire JSONL corpus M12")
    ap.add_argument("jsonl", type=Path, help="Chemin fichier .jsonl")
    ap.add_argument(
        "--list",
        action="store_true",
        help="Lister une ligne résumée par document (task_id / kind / taxonomie)",
    )
    args = ap.parse_args()
    path = args.jsonl
    if not path.is_file():
        print(f"ERREUR: fichier introuvable: {path}", file=sys.stderr)
        return 1

    kinds: Counter[str] = Counter()
    export_ok_c: Counter[str] = Counter()
    ann_status: Counter[str] = Counter()
    taxonomy_core: Counter[str] = Counter()
    document_role: Counter[str] = Counter()
    project_id: Counter[str] = Counter()
    rows: list[dict[str, str | int | bool | None]] = []

    line_no = 0
    for line in iter_m12_jsonl_lines(path):
        line_no += 1
        kind = export_line_kind(line)
        kinds[kind] += 1
        ok = line.get("export_ok")
        export_ok_c[str(ok)] += 1

        ls_meta = line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
        st = (ls_meta.get("annotation_status") or _meta(line).get("annotation_status") or "").strip()
        if st:
            ann_status[st] += 1
        else:
            ann_status["(absent)"] += 1

        pid = ls_meta.get("project_id")
        project_id[str(pid) if pid is not None else "(absent)"] += 1

        dms = dms_annotation_from_line(line)
        tax = role = ""
        src_len = 0
        if isinstance(line.get("source_text"), str):
            src_len = len(line["source_text"].strip())
        if dms:
            r = _routing(dms)
            tax = str(r.get("taxonomy_core") or "")
            role = str(r.get("document_role") or "")
            if tax:
                taxonomy_core[tax] += 1
            else:
                taxonomy_core["(absent)"] += 1
            if role:
                document_role[role] += 1
            else:
                document_role["(absent)"] += 1
        else:
            taxonomy_core["(pas de DMS sur la ligne)"] += 1
            document_role["(pas de DMS sur la ligne)"] += 1

        rows.append(
            {
                "line": line_no,
                "kind": kind,
                "task_id": ls_meta.get("task_id"),
                "annotation_id": ls_meta.get("annotation_id"),
                "annotation_status": st or None,
                "export_ok": ok if isinstance(ok, bool) else None,
                "taxonomy_core": tax or None,
                "document_role": role or None,
                "source_text_chars": src_len,
            }
        )

    print(f"Fichier: {path.resolve()}")
    print(f"Lignes JSON non vides: {line_no}")
    print()
    print("## Formats (export_line_kind)")
    for k, v in kinds.most_common():
        print(f"  {k}: {v}")
    print()
    print("## export_ok (brut ligne)")
    for k, v in sorted(export_ok_c.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {k}: {v}")
    print()
    print("## annotation_status")
    for k, v in ann_status.most_common():
        print(f"  {k}: {v}")
    print()
    print("## project_id (ls_meta)")
    for k, v in project_id.most_common():
        print(f"  {k}: {v}")
    print()
    print("## taxonomy_core (depuis DMS si présent)")
    for k, v in taxonomy_core.most_common():
        print(f"  {k}: {v}")
    print()
    print("## document_role (depuis DMS si présent)")
    for k, v in document_role.most_common():
        print(f"  {k}: {v}")

    if args.list:
        print()
        print("## Détail par ligne")
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
