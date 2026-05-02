"""Canonical workspace-scoped assembler for M14 ``offers[]`` inputs."""

from __future__ import annotations

import json
from typing import Any

from src.db import db_fetchall


class M14OfferReadinessError(RuntimeError):
    """Raised when workspace offers are not safe to submit to M14."""

    def __init__(self, blockers: list[str]) -> None:
        self.blockers = blockers
        super().__init__("; ".join(blockers))


def _parse_json_object(
    raw: Any, *, bundle_id: str, blockers: list[str]
) -> dict[str, Any]:
    if raw in (None, "", {}, []):
        blockers.append(f"{bundle_id}:extracted_data_json_absent_or_empty")
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        blockers.append(f"{bundle_id}:extracted_data_json_invalid_type")
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        blockers.append(f"{bundle_id}:extracted_data_json_invalid_json")
        return {}
    if not isinstance(parsed, dict) or not parsed:
        blockers.append(f"{bundle_id}:extracted_data_json_empty_envelope")
        return {}
    return parsed


def _parse_missing_fields(raw: Any) -> list[str]:
    if raw in (None, "", [], {}):
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return [raw]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return [str(raw)]


def _field_value_present(field: dict[str, Any]) -> bool:
    return "value" in field and field.get("value") not in (None, "")


def _validate_fields(
    fields: Any, *, bundle_id: str, blockers: list[str]
) -> list[dict[str, Any]]:
    if not isinstance(fields, list) or not fields:
        blockers.append(f"{bundle_id}:fields_empty")
        return []
    valid: list[dict[str, Any]] = []
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            blockers.append(f"{bundle_id}:field_{index}_invalid_type")
            continue
        missing_keys = [
            key
            for key in ("name", "value", "confidence", "evidence")
            if key not in field
        ]
        if missing_keys or not _field_value_present(field):
            blockers.append(
                f"{bundle_id}:field_{index}_missing_"
                + "_".join(missing_keys or ["value"])
            )
            continue
        valid.append(field)
    return valid


def _evidence_map(fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {str(field.get("name")): field.get("evidence") for field in fields}


def _capability_sections_present(fields: list[dict[str, Any]]) -> list[str]:
    present: list[str] = []
    for field in fields:
        name = str(field.get("name") or "")
        value = field.get("value")
        if value not in (None, "", "ABSENT", [], {}):
            present.append(name)
    return list(dict.fromkeys(present))


def _field_lookup(fields: list[dict[str, Any]], *names: str) -> Any:
    wanted = {name.lower() for name in names}
    for field in fields:
        if str(field.get("name") or "").lower() in wanted:
            value = field.get("value")
            if value not in (None, "", "ABSENT"):
                return value
    return None


def _dao_criteria_are_ready(conn: Any, workspace_id: str) -> tuple[bool, str | None]:
    rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id, COALESCE(ponderation, 0)::float AS ponderation
        FROM dao_criteria
        WHERE workspace_id = CAST(:wid AS uuid)
        """,
        {"wid": workspace_id},
    )
    if not rows:
        return False, "dao_criteria_empty"
    total = sum(float(row.get("ponderation") or 0.0) for row in rows)
    if abs(total - 100.0) > 0.01:
        return False, "dao_criteria_ponderation_incoherent"
    return True, None


def _existing_evaluation_documents_count(conn: Any, workspace_id: str) -> int:
    rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id
        FROM evaluation_documents
        WHERE workspace_id = CAST(:wid AS uuid)
        LIMIT 1
        """,
        {"wid": workspace_id},
    )
    return len(rows or [])


def _stale_assessments_exist(
    conn: Any, workspace_id: str, current_bundle_ids: set[str]
) -> bool:
    rows = db_fetchall(
        conn,
        """
        SELECT bundle_id::text AS bundle_id
        FROM criterion_assessments
        WHERE workspace_id = CAST(:wid AS uuid)
        LIMIT 200
        """,
        {"wid": workspace_id},
    )
    return any(
        str(row.get("bundle_id") or "") not in current_bundle_ids for row in rows or []
    )


def _bundle_context_by_id(conn: Any, workspace_id: str) -> dict[str, dict[str, Any]]:
    rows = db_fetchall(
        conn,
        """
        SELECT sb.id::text AS bundle_id,
               sb.gate_b_role,
               bd.m12_doc_kind
        FROM supplier_bundles sb
        LEFT JOIN bundle_documents bd
          ON bd.bundle_id = sb.id
         AND bd.workspace_id = sb.workspace_id
        WHERE sb.workspace_id = CAST(:wid AS uuid)
        """,
        {"wid": workspace_id},
    )
    return {str(row.get("bundle_id")): dict(row) for row in rows or []}


def _taxonomy_warning(payload: dict[str, Any], context: dict[str, Any]) -> str | None:
    taxonomy = str(payload.get("taxonomy_core") or "").strip().lower()
    m12 = str(context.get("m12_doc_kind") or "").strip().lower()
    gate_b = str(context.get("gate_b_role") or "").strip().lower()
    if (
        gate_b == "scorable"
        and m12.startswith("offer")
        and taxonomy
        and not taxonomy.startswith("offer")
    ):
        return "taxonomy_core_divergent"
    return None


def _offer_from_extraction(
    row: dict[str, Any],
    *,
    bundle_context: dict[str, dict[str, Any]],
    duplicate_latest_selected: bool,
) -> tuple[dict[str, Any] | None, list[str]]:
    bundle_id = str(row.get("bundle_id") or "").strip()
    blockers: list[str] = []
    if not bundle_id:
        blockers.append("bundle_id_absent")
    supplier_name = str(row.get("supplier_name") or "").strip()
    if not supplier_name or supplier_name.upper() == "ABSENT":
        blockers.append(f"{bundle_id}:supplier_name_absent")
    extraction_id = str(row.get("id") or "").strip()
    if not extraction_id:
        blockers.append(f"{bundle_id}:extraction_id_absent")

    payload = _parse_json_object(
        row.get("extracted_data_json"), bundle_id=bundle_id, blockers=blockers
    )
    if payload.get("extraction_ok") is not True:
        blockers.append(f"{bundle_id}:extraction_ok_not_true")
    fields = _validate_fields(
        payload.get("fields"), bundle_id=bundle_id, blockers=blockers
    )

    if blockers:
        return None, blockers

    warnings: list[str] = []
    warning = _taxonomy_warning(payload, bundle_context.get(bundle_id, {}))
    if warning:
        warnings.append(warning)
    if duplicate_latest_selected:
        warnings.append("duplicate_offer_extractions_latest_selected")

    missing_fields = _parse_missing_fields(row.get("missing_fields_json"))
    line_items = (
        payload.get("line_items") if isinstance(payload.get("line_items"), list) else []
    )
    offer = {
        "document_id": bundle_id,
        "supplier_name": supplier_name,
        "process_role": "responds_to_bid",
        "extraction_id": extraction_id,
        "extraction_ok": True,
        "review_required": bool(payload.get("review_required", False)),
        "taxonomy_core": payload.get("taxonomy_core"),
        "family_main": payload.get("family_main"),
        "family_sub": payload.get("family_sub"),
        "document_role": payload.get("document_role"),
        "schema_version": payload.get("schema_version"),
        "extracted_fields": fields,
        "evidence_map": _evidence_map(fields),
        "missing_fields": missing_fields,
        "line_items": line_items,
        "present_admin_subtypes": [],
        "capability_sections_present": _capability_sections_present(fields),
        "currency": _field_lookup(fields, "currency", "devise"),
        "total_price": _field_lookup(fields, "total_price", "total_amount"),
        "readiness_status": "ready",
        "readiness_blockers": [],
        "readiness_warnings": warnings,
    }
    return offer, []


def build_m14_offers_for_workspace(
    conn: Any,
    workspace_id: str,
    *,
    allow_existing_evaluation_documents: bool = False,
    allow_stale_criterion_assessments: bool = False,
) -> list[dict[str, Any]]:
    """Build fail-closed M14 offers from ``offer_extractions`` only."""
    dao_ready, dao_blocker = _dao_criteria_are_ready(conn, workspace_id)
    if not dao_ready and dao_blocker:
        raise M14OfferReadinessError([dao_blocker])
    if (
        not allow_existing_evaluation_documents
        and _existing_evaluation_documents_count(conn, workspace_id) > 0
    ):
        raise M14OfferReadinessError(["evaluation_documents_existing_skip_risk"])

    rows = db_fetchall(
        conn,
        """
        SELECT id::text AS id,
               bundle_id::text AS bundle_id,
               supplier_name,
               extracted_data_json,
               missing_fields_json,
               created_at
        FROM offer_extractions
        WHERE workspace_id = CAST(:wid AS uuid)
        ORDER BY bundle_id::text, created_at DESC NULLS LAST, id::text DESC
        """,
        {"wid": workspace_id},
    )
    if not rows:
        raise M14OfferReadinessError(["offer_extractions_empty"])

    bundle_context = _bundle_context_by_id(conn, workspace_id)
    offers: list[dict[str, Any]] = []
    blockers: list[str] = []
    seen_bundle_ids: set[str] = set()
    bundle_counts: dict[str, int] = {}
    for r in rows:
        bundle_id = str(r.get("bundle_id") or "")
        bundle_counts[bundle_id] = bundle_counts.get(bundle_id, 0) + 1
    for r in rows:
        bundle_id = str(r.get("bundle_id") or "")
        if bundle_id in seen_bundle_ids:
            continue
        seen_bundle_ids.add(bundle_id)
        offer, row_blockers = _offer_from_extraction(
            dict(r),
            bundle_context=bundle_context,
            duplicate_latest_selected=bundle_counts.get(bundle_id, 0) > 1,
        )
        if row_blockers:
            blockers.extend(row_blockers)
        elif offer is not None:
            offers.append(offer)
    if not offers and not blockers:
        blockers.append("no_ready_offer_extractions")
    if blockers:
        raise M14OfferReadinessError(blockers)
    if not allow_stale_criterion_assessments and _stale_assessments_exist(
        conn, workspace_id, {str(offer["document_id"]) for offer in offers}
    ):
        raise M14OfferReadinessError(["criterion_assessments_stale_bundle_set"])
    return offers
