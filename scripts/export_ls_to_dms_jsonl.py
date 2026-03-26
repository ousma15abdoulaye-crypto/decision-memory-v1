"""
Export Label Studio → DMS JSONL (M12)

Modes :
  - Défaut (m12-v2) : aligne les annotations LS sur label_studio_config.xml et produit une ligne JSON m12-v2 contenant notamment `dms_annotation` (JSON parsé/validé issu de `extracted_json`), `ls_meta` et les champs QA (`export_ok`, `export_errors`, etc.). Le `extracted_json` brut n'est pas sérialisé tel quel.
  - --legacy-mandat-fields : ancien mapping doc_type / ao_ref / zones (MANDAT-LS-001-v2)

Usage API :
  LABEL_STUDIO_URL=... LABEL_STUDIO_API_KEY=... \\
  python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output out.jsonl

Usage fichier (tests / hors réseau) :
  python scripts/export_ls_to_dms_jsonl.py --from-export-json export.json --output out.jsonl
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"


def _ensure_annotation_path() -> None:
    p = str(_ANNOTATION_BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


_ensure_annotation_path()
from m12_export_line import ls_annotation_to_m12_v2_line, to_dms_line_legacy


def main() -> None:
    from ls_client import fetch_annotations

    parser = argparse.ArgumentParser(
        description="Export Label Studio → DMS JSONL (m12-v2 ou legacy)"
    )
    parser.add_argument("--project-id", type=int, default=None)
    parser.add_argument("--output", type=str, default="m12_export.jsonl")
    parser.add_argument(
        "--legacy-mandat-fields",
        action="store_true",
        help="Ancien format doc_type / ao_ref (XML LS différent)",
    )
    parser.add_argument(
        "--from-export-json",
        type=str,
        default=None,
        help="Fichier JSON export LS (sans appel API)",
    )
    parser.add_argument(
        "--no-enforce-validated-qa",
        action="store_true",
        help="Ne pas marquer export_ok=false si annotated_validated + QA KO",
    )
    parser.add_argument(
        "--require-ls-attestations",
        action="store_true",
        help="Si annotated_validated : exiger evidence_attestation + no_invented_numbers (XML v2)",
    )
    parser.add_argument(
        "--m15-gate",
        action="store_true",
        help=(
            "DATA-M15 : exit≠0 si une ligne annotated_validated a export_ok=false "
            "(scripts/m15_export_gate.py)"
        ),
    )
    args = parser.parse_args()

    if args.from_export_json:
        with open(args.from_export_json, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = [data]
        project_id = args.project_id or 0
    else:
        ls_url = os.environ.get("LABEL_STUDIO_URL", "").rstrip("/")
        ls_key = os.environ.get("LABEL_STUDIO_API_KEY", "")
        if not ls_url or not ls_key:
            sys.exit(
                "STOP — LABEL_STUDIO_URL et LABEL_STUDIO_API_KEY requis (ou --from-export-json)"
            )
        if args.project_id is None:
            sys.exit("STOP — --project-id requis pour l'export API")
        data = fetch_annotations(args.project_id, ls_url, ls_key)
        project_id = args.project_id

    lines: list[dict] = []
    enforce = not args.no_enforce_validated_qa
    require_att = args.require_ls_attestations

    for item in data:
        annotations = item.get("annotations", [])
        if not annotations:
            continue
        for ann in annotations:
            if args.legacy_mandat_fields:
                line = to_dms_line_legacy(ann, item, project_id)
            else:
                line = ls_annotation_to_m12_v2_line(
                    ann,
                    item,
                    project_id,
                    enforce_validated_qa=enforce,
                    require_ls_attestations=require_att,
                )
            lines.append(line)

    if args.m15_gate:
        _gate_path = _SCRIPT_DIR / "m15_export_gate.py"
        if not _gate_path.is_file():
            print(
                f"STOP — m15_export_gate introuvable : {_gate_path}",
                file=sys.stderr,
            )
            sys.exit(2)
        _spec = importlib.util.spec_from_file_location("m15_export_gate", _gate_path)
        if _spec is None or _spec.loader is None:
            print(
                f"STOP — chargement m15_export_gate impossible : {_gate_path}",
                file=sys.stderr,
            )
            sys.exit(2)
        _m15 = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_m15)
        violations = _m15.collect_m15_gate_violations(lines)
        if violations:
            for idx, msg in violations[:50]:
                print(f"m15-gate ligne {idx + 1}: {msg}", file=sys.stderr)
            sys.exit(2)

    out = args.output
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"Exporté {len(lines)} lignes → {out}")


if __name__ == "__main__":
    main()
