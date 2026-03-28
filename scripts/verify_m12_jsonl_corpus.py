"""
Verdict lisible sur un export JSONL M12 : exploitable ou non.

Usage :
  python scripts/verify_m12_jsonl_corpus.py data/annotations/ls_smoke_export.jsonl
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.annotation.m12_export_io import (  # noqa: E402
    dms_annotation_from_line,
    export_line_kind,
    iter_m12_jsonl_lines,
)


def _scan(path: Path) -> dict[str, Any]:
    n = 0
    kinds: Counter[str] = Counter()
    dms_non_null = 0
    raw_text_present = 0
    export_ok_t = export_ok_f = export_ok_other = 0
    raw_fallback = 0
    err_prefixes: Counter[str] = Counter()

    for line in iter_m12_jsonl_lines(path):
        n += 1
        kind = export_line_kind(line)
        kinds[kind] += 1
        if dms_annotation_from_line(line) is not None:
            dms_non_null += 1
        rjt = line.get("raw_json_text")
        if isinstance(rjt, str) and rjt.strip():
            raw_text_present += 1
        if line.get("export_schema_version") == "m12-v2-raw-fallback":
            raw_fallback += 1
        ok = line.get("export_ok")
        if ok is True:
            export_ok_t += 1
        elif ok is False:
            export_ok_f += 1
        else:
            export_ok_other += 1
        errs = line.get("export_errors")
        if isinstance(errs, list):
            for e in errs:
                if not isinstance(e, str) or not e.strip():
                    continue
                prefix = e.split(":", 1)[0].strip()[:48]
                err_prefixes[prefix] += 1

    return {
        "path": str(path.resolve()),
        "lines": n,
        "kinds": dict(kinds),
        "dms_annotation_non_null": dms_non_null,
        "raw_json_text_present": raw_text_present,
        "raw_fallback_lines": raw_fallback,
        "export_ok_true": export_ok_t,
        "export_ok_false": export_ok_f,
        "export_ok_other": export_ok_other,
        "error_prefixes": err_prefixes,
    }


def _verdict(r: dict[str, Any]) -> tuple[str, list[str]]:
    notes: list[str] = []
    n = r["lines"]
    if n == 0:
        return (
            "VIDE",
            [
                "Aucune ligne — vérifier LS, --project-id, filtres (--only-finished exclut les brouillons).",
            ],
        )

    ok_t, ok_f = r["export_ok_true"], r["export_ok_false"]
    dms = r["dms_annotation_non_null"]
    raw = r["raw_json_text_present"]
    fb = r["raw_fallback_lines"]

    if ok_t == n and dms == n:
        return (
            "EXPLOITABLE",
            [
                f"Toutes les {n} ligne(s) ont export_ok=true et dms_annotation.",
            ],
        )

    if ok_t > 0:
        notes.append(
            f"{ok_t}/{n} ligne(s) export_ok=true ; {ok_f} false — corpus partiellement exploitable."
        )
    elif dms > 0:
        notes.append(
            f"Pas d'export_ok=true mais {dms} ligne(s) avec dms_annotation — réparation / QA possible."
        )
    elif raw > 0 or fb > 0:
        notes.append(
            f"Pas de DMS validé ; raw_json_text={raw}, fallback={fb} — données récupérables, schéma à corriger."
        )
    else:
        notes.append("Peu de signaux positifs — voir export_errors.")

    if ok_f > 0 and r["error_prefixes"]:
        top = r["error_prefixes"].most_common(5)
        notes.append("Erreurs fréquentes : " + ", ".join(f"{k}×{v}" for k, v in top))

    label = "PARTIEL" if (ok_t > 0 or dms > 0 or raw > 0) else "BLOQUE"
    return label, notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verdict exploitabilité d'un export JSONL M12 (LS / autosave)"
    )
    parser.add_argument(
        "jsonl",
        type=Path,
        help="Fichier .jsonl",
    )
    args = parser.parse_args()
    p = args.jsonl
    if not p.is_file():
        print(f"STOP — fichier introuvable : {p}", file=sys.stderr)
        return 2

    r = _scan(p)
    verdict, notes = _verdict(r)

    print(f"Fichier : {r['path']}")
    print(f"Lignes   : {r['lines']}")
    print(f"Formats  : {r['kinds']}")
    print(
        f"dms_annotation non null : {r['dms_annotation_non_null']} | "
        f"raw_json_text présent : {r['raw_json_text_present']} | "
        f"lignes fallback brut  : {r['raw_fallback_lines']}"
    )
    print(
        f"export_ok true / false / autre : {r['export_ok_true']} / "
        f"{r['export_ok_false']} / {r['export_ok_other']}"
    )
    if r["error_prefixes"]:
        print("Préfixes export_errors (top 12) :")
        for k, v in r["error_prefixes"].most_common(12):
            print(f"  {v}×  {k}")
    print()
    print(f"=== VERDICT : {verdict} ===")
    for line in notes:
        print(line)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
