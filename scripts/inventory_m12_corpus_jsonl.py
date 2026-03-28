"""
Inventaire rapide d'un ou plusieurs fichiers JSONL M12 (export LS, R2 agrégé, etc.).

Sans révéler de secrets : compte les lignes, les clés stables, les formats (m12-v2, …),
export_ok, répartition des statuts LS.

Usage :
  python scripts/inventory_m12_corpus_jsonl.py data/annotations/ls_smoke_export.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.annotation.m12_export_io import (  # noqa: E402
    export_line_kind,
    stable_m12_corpus_line_id,
)


def _scan_file(path: Path) -> dict[str, Any]:
    kinds: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    export_ok_t = export_ok_f = 0
    export_ok_na = 0
    stable_ids: list[str] = []
    parse_errors = 0
    non_dict = 0
    lines_non_empty = 0

    with path.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            lines_non_empty += 1
            try:
                obj: Any = json.loads(raw)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            if not isinstance(obj, dict):
                non_dict += 1
                continue

            kind = export_line_kind(obj)
            kinds[kind] += 1
            sid = stable_m12_corpus_line_id(obj)
            stable_ids.append(sid)

            lm = obj.get("ls_meta")
            if isinstance(lm, dict):
                st = (lm.get("annotation_status") or "").strip() or "(vide)"
                statuses[st] += 1

            if kind == "m12-v2":
                if obj.get("export_ok") is True:
                    export_ok_t += 1
                elif obj.get("export_ok") is False:
                    export_ok_f += 1
                else:
                    export_ok_na += 1
            else:
                export_ok_na += 1

    id_counts = Counter(stable_ids)
    dup_ids = sum(1 for _k, n in id_counts.items() if n > 1)

    return {
        "path": str(path.resolve()),
        "lines_non_empty": lines_non_empty,
        "parse_errors": parse_errors,
        "non_dict_lines": non_dict,
        "parsed_dict_lines": lines_non_empty - parse_errors - non_dict,
        "unique_stable_ids": len(id_counts),
        "duplicate_stable_id_values": dup_ids,
        "kinds": dict(kinds),
        "ls_annotation_status": dict(statuses),
        "m12_v2_export_ok_true": export_ok_t,
        "m12_v2_export_ok_false": export_ok_f,
        "export_ok_not_applicable_rows": export_ok_na,
    }


def _write_manifest_tsv(jsonl_path: Path, tsv_path: Path) -> int:
    rows: list[tuple[int, str, Any, Any, Any, str, Any]] = []
    with jsonl_path.open(encoding="utf-8") as f:
        for idx, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            o: Any = json.loads(raw)
            if not isinstance(o, dict):
                continue
            lm = o.get("ls_meta") if isinstance(o.get("ls_meta"), dict) else {}
            sid = stable_m12_corpus_line_id(o)
            st = (
                (lm.get("annotation_status") or "").strip()
                if isinstance(lm, dict)
                else ""
            )
            rows.append(
                (
                    idx,
                    sid,
                    lm.get("project_id") if isinstance(lm, dict) else None,
                    lm.get("task_id") if isinstance(lm, dict) else None,
                    lm.get("annotation_id") if isinstance(lm, dict) else None,
                    st,
                    o.get("export_ok"),
                )
            )
    rows.sort(key=lambda r: (r[3] is None, r[3] or 0, r[4] or 0))
    tsv_path.parent.mkdir(parents=True, exist_ok=True)
    with tsv_path.open("w", encoding="utf-8") as out:
        out.write(
            "row_num\tstable_id\tproject_id\ttask_id\tannotation_id\tannotation_status\texport_ok\n"
        )
        for r in rows:
            out.write("\t".join("" if x is None else str(x) for x in r) + "\n")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventaire JSONL M12 (lignes, clés stables, formats, export_ok, statuts LS)"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="JSONL",
        help="Un ou plusieurs fichiers .jsonl",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sortie JSON sur stdout (silencieux sinon humain)",
    )
    parser.add_argument(
        "--manifest-tsv",
        type=Path,
        default=None,
        metavar="PATH",
        help="Ecrit un TSV (une ligne par annotation) ; exige exactement un fichier JSONL en entree",
    )
    args = parser.parse_args()

    if args.manifest_tsv is not None and len(args.paths) != 1:
        print(
            "STOP --manifest-tsv : fournir exactement un fichier .jsonl",
            file=sys.stderr,
        )
        return 2

    reports: list[dict[str, Any]] = []
    for p in args.paths:
        if not p.is_file():
            print(f"STOP — fichier introuvable : {p}", file=sys.stderr)
            return 2
        reports.append(_scan_file(p))

    if args.manifest_tsv is not None:
        n = _write_manifest_tsv(args.paths[0], args.manifest_tsv)
        print(f"Manifeste TSV : {n} ligne(s) -> {args.manifest_tsv.resolve()}")

    if args.json:
        out = {"files": reports}
        if len(reports) == 1:
            out["summary"] = {
                "lines_non_empty": reports[0]["lines_non_empty"],
                "unique_stable_ids": reports[0]["unique_stable_ids"],
            }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    for r in reports:
        print(f"Fichier : {r['path']}")
        print(f"  Lignes non vides     : {r['lines_non_empty']}")
        print(f"  Erreurs JSON         : {r['parse_errors']}")
        print(f"  Lignes non-objet     : {r['non_dict_lines']}")
        print(f"  Objets parsés        : {r['parsed_dict_lines']}")
        print(f"  IDs stables uniques  : {r['unique_stable_ids']}")
        if r["duplicate_stable_id_values"]:
            print(
                f"  IDs stables en doublon (valeurs) : {r['duplicate_stable_id_values']}"
            )
        print(f"  Formats (export_line_kind) : {r['kinds']}")
        if r["ls_annotation_status"]:
            print(f"  ls_meta.annotation_status : {r['ls_annotation_status']}")
        print(
            f"  m12-v2 export_ok true/false : {r['m12_v2_export_ok_true']} / "
            f"{r['m12_v2_export_ok_false']} (autres lignes sans champ pertinent : "
            f"{r['export_ok_not_applicable_rows']})"
        )
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
