#!/usr/bin/env python3
"""
Valide un fichier JSONL d'annotations DMS (schéma v3.0.1d + QA optionnelle).

Chaque ligne :
  - soit un JSON DMSAnnotation complet (défaut)
  - soit un objet avec clé \"dms_annotation\" (--wrapped, ex. export m12-v2)

Sortie : code 0 si tout OK, 1 sinon.

Usage :
  python scripts/validate_annotation.py data/annotations/fixtures/golden_dms_line.jsonl
  python scripts/validate_annotation.py export.jsonl --wrapped --strict-financial
  python scripts/validate_annotation.py lines.jsonl --wrapped --require-evidence-substring
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"
if str(_ANNOTATION_BACKEND) not in sys.path:
    sys.path.insert(0, str(_ANNOTATION_BACKEND))

from annotation_qa import (  # noqa: E402
    evidence_substring_violations,
    financial_coherence_warnings,
)
from pydantic import ValidationError  # noqa: E402

from prompts.schema_validator import DMSAnnotation  # noqa: E402


def _load_dms_dict(line_obj: dict, wrapped: bool) -> dict | None:
    if wrapped:
        inner = line_obj.get("dms_annotation")
        if inner is None:
            return None
        if not isinstance(inner, dict):
            return None
        return inner
    return line_obj


def _source_for_evidence(line_obj: dict, wrapped: bool) -> str:
    if not wrapped:
        return ""
    # Export m12-v2 : source_text présent quand l’export vient de m12_export_line (LS)
    return str(line_obj.get("source_text") or "")


def validate_file(
    path: Path,
    *,
    wrapped: bool,
    strict_financial: bool,
    require_evidence_substring: bool,
) -> tuple[int, list[str]]:
    errors: list[str] = []
    line_no = 0

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line_no += 1
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                errors.append(f"L{line_no}: invalid_json {e}")
                continue
            if not isinstance(obj, dict):
                errors.append(f"L{line_no}: line_not_object")
                continue

            dms = _load_dms_dict(obj, wrapped)
            if dms is None:
                errors.append(f"L{line_no}: missing_dms_annotation")
                continue

            try:
                validated = DMSAnnotation.model_validate(dms)
                dms_dump = validated.model_dump(by_alias=True)
            except (ValidationError, ValueError) as e:
                errors.append(f"L{line_no}: schema {e!s}")
                continue

            if strict_financial:
                fw = financial_coherence_warnings(dms_dump, line_no)
                if fw:
                    errors.append(f"L{line_no}: financial {fw}")

            if require_evidence_substring:
                src = _source_for_evidence(obj, wrapped)
                if not src.strip():
                    errors.append(
                        f"L{line_no}: require_evidence_substring but no source_text"
                    )
                else:
                    ev = evidence_substring_violations(dms_dump, src)
                    if ev:
                        errors.append(f"L{line_no}: evidence {ev[:3]}")

    return (0 if not errors else 1), errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Valide JSONL annotations DMS")
    parser.add_argument("jsonl_path", type=Path)
    parser.add_argument(
        "--wrapped",
        action="store_true",
        help="Chaque ligne contient dms_annotation (export m12-v2)",
    )
    parser.add_argument(
        "--strict-financial",
        action="store_true",
        help="Échoue si financial_coherence_warnings non vide",
    )
    parser.add_argument(
        "--require-evidence-substring",
        action="store_true",
        help="Exige source_text sur la ligne (wrapped) et evidence vérifiable",
    )
    args = parser.parse_args()

    if not args.jsonl_path.is_file():
        print(f"Fichier introuvable : {args.jsonl_path}", file=sys.stderr)
        return 1

    code, errs = validate_file(
        args.jsonl_path,
        wrapped=args.wrapped,
        strict_financial=args.strict_financial,
        require_evidence_substring=args.require_evidence_substring,
    )
    for e in errs:
        print(e, file=sys.stderr)
    if errs:
        print(f"Échec : {len(errs)} erreur(s)", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
