"""
Export Label Studio → DMS JSONL (M12)

Modes :
  - Défaut (m12-v2) : aligné sur label_studio_config.xml — extracted_json + ls_meta
  - --legacy-mandat-fields : ancien mapping doc_type / ao_ref / zones (MANDAT-LS-001-v2)

Usage API :
  LABEL_STUDIO_URL=... LABEL_STUDIO_API_KEY=... \\
  python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output out.jsonl

Usage fichier (tests / hors réseau) :
  python scripts/export_ls_to_dms_jsonl.py --from-export-json export.json --output out.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"


def _ensure_annotation_path() -> None:
    p = str(_ANNOTATION_BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


CONF_MAP = {1: 0.60, 2: 0.80, 3: 1.00}


def fetch_annotations(project_id: int, ls_url: str, ls_key: str) -> list[dict]:
    headers = {"Authorization": f"Token {ls_key}"}
    url = f"{ls_url.rstrip('/')}/api/projects/{project_id}/export"
    r = requests.get(
        url,
        headers=headers,
        params={"exportType": "JSON"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _get_text(results: list[dict], field: str) -> str | None:
    for r in results:
        if r.get("from_name") == field:
            val = r.get("value", {})
            if isinstance(val, dict) and "text" in val:
                texts = val["text"]
                return texts[0] if texts else None
            if isinstance(val, dict) and "choices" in val:
                choices = val["choices"]
                return choices[0] if choices else None
    return None


def _get_confidence(results: list[dict], field: str) -> float | None:
    for r in results:
        if r.get("from_name") == field:
            val = r.get("value", {})
            if isinstance(val, dict) and "confidence" in val:
                c = val["confidence"]
                if c in (1.0, 0.80, 0.60):
                    return c
                return 0.80
    return None


def _task_source_text(task: dict) -> str:
    data = task.get("data") or {}
    raw = data.get("text")
    if raw in (None, ""):
        raw = data.get("content")
    if raw is None:
        return ""
    return str(raw)


def _to_dms_line_legacy(ann: dict, task: dict, project_id: int) -> dict:
    """Ancien export MANDAT — champs doc_type / ao_ref / zones."""
    results = ann.get("result", [])
    task_id = task.get("id")
    task_data = task.get("data", {})

    doc_type = _get_text(results, "doc_type")
    ao_ref = _get_text(results, "ao_ref")
    evidence_ao = _get_text(results, "evidence_hint_ao_ref")
    zones_raw = _get_text(results, "zones")

    zones: list[Any] = []
    if zones_raw:
        try:
            zones = json.loads(zones_raw) if zones_raw.startswith("[") else [zones_raw]
        except json.JSONDecodeError:
            zones = [zones_raw] if zones_raw else []

    ground_truth = {
        "doc_type": {
            "value": doc_type,
            "confidence_expected": CONF_MAP.get(ann.get("completed_by", 2), 0.80),
            "evidence_hint": None,
        },
        "ao_ref": {
            "value": ao_ref,
            "confidence_expected": _get_confidence(results, "ao_ref") or 0.80,
            "evidence_hint": evidence_ao,
        },
        "zones_mentionnees": zones,
        "task_id": task_id,
        "annotation_id": ann.get("id"),
        "project_id": project_id,
        "exported_at": datetime.now(UTC).isoformat(),
    }

    content_hash = hashlib.sha256(
        json.dumps(ground_truth, sort_keys=True).encode()
    ).hexdigest()[:16]

    return {
        "export_schema_version": "m12-legacy",
        "ground_truth": ground_truth,
        "source_task": {"id": task_id, "data_keys": list(task_data.keys())},
        "content_hash": content_hash,
        "ambig_tracked": [],
    }


def ls_annotation_to_m12_v2_line(
    ann: dict,
    task: dict,
    project_id: int,
    *,
    enforce_validated_qa: bool = True,
    require_ls_attestations: bool = False,
) -> dict:
    """
    Transforme une annotation LS (résultat + tâche) en ligne JSONL m12-v2.
    """
    _ensure_annotation_path()
    from annotation_qa import (
        evidence_substring_violations,
        financial_coherence_warnings,
    )
    from pydantic import ValidationError

    from prompts.schema_validator import DMSAnnotation

    results = ann.get("result", [])
    task_id = task.get("id")
    task_data = task.get("data", {}) or {}
    raw_json = _get_text(results, "extracted_json")

    ls_meta = {
        "task_id": task_id,
        "annotation_id": ann.get("id"),
        "project_id": project_id,
        "evidence_attestation": _get_text(results, "evidence_attestation"),
        "no_invented_numbers": _get_text(results, "no_invented_numbers"),
        "routing_ok": _get_text(results, "routing_ok"),
        "financial_ok": _get_text(results, "financial_ok"),
        "annotation_notes": _get_text(results, "annotation_notes"),
        "annotation_status": _get_text(results, "annotation_status"),
        "exported_at": datetime.now(UTC).isoformat(),
    }

    export_errors: list[str] = []
    dms_annotation: dict[str, Any] | None = None

    if not raw_json or not str(raw_json).strip():
        export_errors.append("missing_extracted_json")
    else:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as e:
            export_errors.append(f"json_parse_error:{e}")
            parsed = None
        if parsed is not None:
            try:
                validated = DMSAnnotation.model_validate(parsed)
                dms_annotation = validated.model_dump(by_alias=True)
            except ValidationError as e:
                export_errors.append(f"schema_validation:{e.error_count()} errors")
            except ValueError as e:
                export_errors.append(f"schema_validation:{e!s}")

    source_text = _task_source_text(task)
    fin_warnings: list[str] = []
    ev_violations: list[str] = []

    if dms_annotation is not None:
        fin_warnings = financial_coherence_warnings(dms_annotation, task_id or 0)
        if source_text.strip():
            ev_violations = evidence_substring_violations(dms_annotation, source_text)

    status = (ls_meta.get("annotation_status") or "").strip()
    if require_ls_attestations and status == "annotated_validated":
        if not ls_meta.get("evidence_attestation"):
            export_errors.append("validated_but_missing_evidence_attestation")
        if not ls_meta.get("no_invented_numbers"):
            export_errors.append("validated_but_missing_no_invented_numbers")

    if enforce_validated_qa and status == "annotated_validated":
        if export_errors:
            export_errors.append("validated_but_export_errors")
        if fin_warnings:
            export_errors.append(f"validated_but_financial:{fin_warnings[0][:80]}")
        if ev_violations:
            export_errors.append(f"validated_but_evidence:{ev_violations[0][:80]}")

    export_ok = not export_errors

    canonical = {
        "dms_annotation": dms_annotation,
        "ls_meta": {k: v for k, v in ls_meta.items() if k != "exported_at"},
        "export_errors": sorted(set(export_errors)),
    }
    content_hash = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    line: dict[str, Any] = {
        "export_schema_version": "m12-v2",
        "content_hash": content_hash,
        "export_ok": export_ok,
        "export_errors": sorted(set(export_errors)),
        "ls_meta": ls_meta,
        "dms_annotation": dms_annotation,
        "ambig_tracked": (
            list(dms_annotation.get("ambiguites", [])) if dms_annotation else []
        ),
        "financial_warnings": fin_warnings,
        "source_task": {"id": task_id, "data_keys": list(task_data.keys())},
    }
    if ev_violations:
        line["evidence_violations"] = ev_violations
    return line


def main() -> None:
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
                line = _to_dms_line_legacy(ann, item, project_id)
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
