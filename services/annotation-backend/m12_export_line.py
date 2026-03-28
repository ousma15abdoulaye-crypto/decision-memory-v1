"""
Ligne d'export M12 v2 — partagée entre le script export_ls_to_dms_jsonl et le webhook backend.

Voir docs/adr/ADR-M12-EXPORT-V2.md
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

CONF_MAP = {1: 0.60, 2: 0.80, 3: 1.00}

# Valeurs sentinelles partagées (identiques à backend.py)
_ABSENT = "ABSENT"
_NOT_APPLICABLE = "NOT_APPLICABLE"


def _normalize_identifiants_for_ls_reimport(annotation: dict) -> None:
    """
    Ajoute supplier_phone_raw / supplier_email_raw si absents.

    ADR-013 : _build_ls_result dans backend.py supprime ces champs du JSON stocké
    dans le textarea LS pour éviter toute fuite de données sensibles. Lors du
    re-import (export LS → corpus JSONL), ils doivent être reconstruits pour que
    DMSAnnotation.model_validate réussisse (champs obligatoires dans Identifiants).

    Sans cette normalisation : schema_validation N errors sur CHAQUE annotation
    exportée depuis LS — cause racine des 30 lignes inexploitables (corpus M12).
    """
    ident = annotation.get("identifiants")
    if not isinstance(ident, dict):
        return
    if "supplier_phone_raw" not in ident:
        ident["supplier_phone_raw"] = (
            "" if isinstance(ident.get("supplier_phone"), dict) else _ABSENT
        )
    if "supplier_email_raw" not in ident:
        ident["supplier_email_raw"] = (
            "" if isinstance(ident.get("supplier_email"), dict) else _ABSENT
        )


def get_ls_result_text(results: list[dict], field: str) -> str | None:
    """Extrait texte ou choix unique depuis result[] Label Studio."""
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


def get_ls_result_confidence(results: list[dict], field: str) -> float | None:
    for r in results:
        if r.get("from_name") == field:
            val = r.get("value", {})
            if isinstance(val, dict) and "confidence" in val:
                c = val["confidence"]
                if c in (1.0, 0.80, 0.60):
                    return c
                return 0.80
    return None


def task_source_text(task: dict) -> str:
    data = task.get("data") or {}
    raw = data.get("text")
    if raw in (None, ""):
        raw = data.get("content")
    if raw is None:
        return ""
    return str(raw)


def to_dms_line_legacy(ann: dict, task: dict, project_id: int) -> dict:
    """Ancien export MANDAT — champs doc_type / ao_ref / zones."""
    results = ann.get("result", [])
    task_id = task.get("id")
    task_data = task.get("data", {})

    source_text = task_source_text(task)

    doc_type = get_ls_result_text(results, "doc_type")
    ao_ref = get_ls_result_text(results, "ao_ref")
    evidence_ao = get_ls_result_text(results, "evidence_hint_ao_ref")
    zones_raw = get_ls_result_text(results, "zones")

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
            "confidence_expected": get_ls_result_confidence(results, "ao_ref") or 0.80,
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
        "source_text": source_text,
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

    Requiert ``annotation-backend`` sur sys.path (imports annotation_qa, prompts).

    Changements enterprise (fix causes racines corpus inexploitable) :
    - raw_json_text : conserve le JSON brut extrait de LS (récupérable même si schéma KO)
    - _normalize_identifiants_for_ls_reimport : ajoute supplier_phone_raw /
      supplier_email_raw absents du textarea LS (ADR-013) → évite schema_validation
      systématique sur toutes les annotations annotated_validated.
    """
    from annotation_qa import (
        evidence_substring_violations,
        financial_coherence_warnings,
    )
    from pydantic import ValidationError

    from prompts.schema_validator import DMSAnnotation

    results = ann.get("result", [])
    task_id = task.get("id")
    task_data = task.get("data", {}) or {}
    raw_json = get_ls_result_text(results, "extracted_json")

    ls_meta = {
        "task_id": task_id,
        "annotation_id": ann.get("id"),
        "project_id": project_id,
        "evidence_attestation": get_ls_result_text(results, "evidence_attestation"),
        "no_invented_numbers": get_ls_result_text(results, "no_invented_numbers"),
        "routing_ok": get_ls_result_text(results, "routing_ok"),
        "financial_ok": get_ls_result_text(results, "financial_ok"),
        "annotation_notes": get_ls_result_text(results, "annotation_notes"),
        "annotation_status": get_ls_result_text(results, "annotation_status"),
        "exported_at": datetime.now(UTC).isoformat(),
    }

    export_errors: list[str] = []
    dms_annotation: dict[str, Any] | None = None

    # Conserver le JSON brut même si la validation échoue (récupérabilité enterprise)
    raw_json_text: str | None = None

    if not raw_json or not str(raw_json).strip():
        export_errors.append("missing_extracted_json")
    else:
        raw_json_text = str(raw_json).strip()
        try:
            parsed = json.loads(raw_json_text)
        except json.JSONDecodeError as e:
            export_errors.append(f"json_parse_error:{e}")
            parsed = None
        if parsed is not None:
            # Normalisation ADR-013 : supplier_phone_raw/email_raw supprimés du textarea LS
            _normalize_identifiants_for_ls_reimport(parsed)
            try:
                validated = DMSAnnotation.model_validate(parsed)
                dms_annotation = validated.model_dump(by_alias=True)
            except ValidationError as e:
                export_errors.append(f"schema_validation:{e.error_count()} errors")
            except ValueError as e:
                export_errors.append(f"schema_validation:{e!s}")

    source_text = task_source_text(task)
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
        # raw_json_text : JSON brut du textarea LS, préservé même si schéma KO
        # Permet récupération sans re-annotation en cas d'erreur pipeline
        "raw_json_text": raw_json_text,
        "ambig_tracked": (
            list(dms_annotation.get("ambiguites", [])) if dms_annotation else []
        ),
        "financial_warnings": fin_warnings,
        "source_text": source_text,
        "source_task": {"id": task_id, "data_keys": list(task_data.keys())},
    }
    if ev_violations:
        line["evidence_violations"] = ev_violations
    return line


def annotation_status_from_result(ann: dict) -> str | None:
    """Lit annotation_status depuis les choices LS (extracted_json non parsé ici)."""
    results = ann.get("result") or []
    return get_ls_result_text(results, "annotation_status")
