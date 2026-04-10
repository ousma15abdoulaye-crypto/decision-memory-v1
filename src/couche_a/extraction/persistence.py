"""
DB persistence for TDRExtractionResult → public.offer_extractions.

Tactique M-FIX-PERSISTENCE-BRIDGE — pas le writer canonique final.
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from src.couche_a.extraction_models import TDRExtractionResult
from src.db import db_execute, db_execute_one, get_connection

logger = logging.getLogger(__name__)


def _resolve_workspace_id_for_case(case_id: str) -> str | None:
    """Résout ``process_workspaces.id`` depuis ``legacy_case_id`` (schéma V4.2+)."""
    with get_connection() as conn:
        row = db_execute_one(
            conn,
            """
            SELECT id::text AS wid FROM public.process_workspaces
            WHERE legacy_case_id = :cid
            LIMIT 1
            """,
            {"cid": case_id},
        )
    return str(row["wid"]) if row and row.get("wid") else None


def _offer_extraction_column_flags(conn) -> tuple[bool, bool]:
    """(has_workspace_id, has_case_id) sur ``public.offer_extractions``."""
    row = db_execute_one(
        conn,
        """
        SELECT
            EXISTS(
                SELECT 1 FROM information_schema.columns c
                WHERE c.table_schema = 'public' AND c.table_name = 'offer_extractions'
                  AND c.column_name = 'workspace_id'
            ) AS has_ws,
            EXISTS(
                SELECT 1 FROM information_schema.columns c
                WHERE c.table_schema = 'public' AND c.table_name = 'offer_extractions'
                  AND c.column_name = 'case_id'
            ) AS has_case
        """,
        {},
    )
    if not row:
        return False, False
    return bool(row.get("has_ws")), bool(row.get("has_case"))


def tdr_result_to_offer_extraction_row(
    result: TDRExtractionResult,
    case_id: str,
    artifact_id: str,
) -> dict[str, str]:
    """
    Mapper explicite TDRExtractionResult → payload ``offer_extractions``.

    Règle de priorité ``supplier_name`` :
      1. raw_annotation.identifiants.supplier_name_raw
      2. raw_annotation.identifiants.supplier_name_normalized
      3. champ extrait dans fields (field_name == "supplier_name")
      4. ABSENT
    """
    supplier_name = "ABSENT"
    if result.raw_annotation:
        identifiants = result.raw_annotation.get("identifiants", {}) or {}
        supplier_name = (
            identifiants.get("supplier_name_raw")
            or identifiants.get("supplier_name_normalized")
            or supplier_name
        )
    if supplier_name == "ABSENT":
        supplier_name = next(
            (
                f.value
                for f in result.fields
                if f.field_name == "supplier_name"
                and f.value not in (None, "", "ABSENT")
            ),
            "ABSENT",
        )

    tier_val = (
        result.tier_used.value
        if hasattr(result.tier_used, "value")
        else str(result.tier_used)
    )

    extracted_payload = {
        "schema_version": result.schema_version,
        "document_role": result.document_role,
        "family_main": result.family_main,
        "family_sub": result.family_sub,
        "taxonomy_core": result.taxonomy_core,
        "extraction_ok": result.extraction_ok,
        "review_required": result.review_required,
        "tier_used": tier_val,
        "latency_ms": result.latency_ms,
        "fields": [
            {
                "name": f.field_name,
                "value": f.value,
                "confidence": f.confidence,
                "evidence": f.evidence,
            }
            for f in result.fields
        ],
        "line_items": [
            {
                "item_line_no": li.item_line_no,
                "item_description_raw": li.item_description_raw,
                "unit_raw": li.unit_raw,
                "unit_price": li.unit_price,
                "quantity": li.quantity,
                "line_total": li.line_total,
                "line_total_check": li.line_total_check,
                "confidence": li.confidence,
            }
            for li in result.line_items
        ],
        "gates": result.gates,
        "ambiguites": result.ambiguites,
        "error_reason": result.error_reason,
    }

    critical_fields = {
        "supplier_name",
        "total_amount",
        "currency",
        "deadline",
        "family_main",
        "family_sub",
        "taxonomy_core",
    }
    missing: list[str] = [
        f.field_name
        for f in result.fields
        if f.field_name in critical_fields and f.value in (None, "ABSENT", "")
    ]
    if supplier_name == "ABSENT":
        missing.append("supplier_name")
    if result.family_main in (None, "ABSENT", ""):
        missing.append("family_main")
    if result.family_sub in (None, "ABSENT", ""):
        missing.append("family_sub")
    if result.taxonomy_core in (None, "ABSENT", ""):
        missing.append("taxonomy_core")
    seen: set[str] = set()
    missing_unique = []
    for m in missing:
        if m not in seen:
            seen.add(m)
            missing_unique.append(m)

    return {
        "id": str(uuid.uuid4()),
        "cid": case_id,
        "aid": artifact_id,
        "supplier": str(supplier_name),
        "extracted": json.dumps(extracted_payload, ensure_ascii=False),
        "missing": json.dumps(missing_unique, ensure_ascii=False),
        "ts": datetime.now(UTC).isoformat(),
    }


def persist_tdr_result_to_db(
    result: TDRExtractionResult,
    case_id: str,
    artifact_id: str,
    *,
    workspace_id: str | None = None,
) -> None:
    """
    Persistance ``TDRExtractionResult`` → ``public.offer_extractions``.

    Schéma V4.2 (migration 074) : ``workspace_id`` NOT NULL, plus de ``case_id``.
    Si ``workspace_id`` est absent, résolution via ``process_workspaces.legacy_case_id``.

    PRE-FLIGHT repo (alembic ``002_add_couche_a``) : pas de UNIQUE sur
    ``artifact_id`` → upsert applicatif.
    """
    row = tdr_result_to_offer_extraction_row(result, case_id, artifact_id)
    wid = workspace_id or _resolve_workspace_id_for_case(case_id)
    with get_connection() as conn:
        has_ws, has_case = _offer_extraction_column_flags(conn)
        existing = db_execute_one(
            conn,
            """
            SELECT id FROM public.offer_extractions
            WHERE artifact_id = :aid
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"aid": artifact_id},
        )
        if existing:
            db_execute(
                conn,
                """
                UPDATE public.offer_extractions SET
                    supplier_name = :supplier,
                    extracted_data_json = :extracted,
                    missing_fields_json = :missing
                WHERE id = :existing_id
                """,
                {
                    "supplier": row["supplier"],
                    "extracted": row["extracted"],
                    "missing": row["missing"],
                    "existing_id": existing["id"],
                },
            )
            logger.info(
                "[BRIDGE] Mis à jour — artifact_id=%s supplier=%s",
                artifact_id,
                row["supplier"],
            )
            return

        if has_ws:
            if not wid:
                logger.error(
                    "[BRIDGE] INSERT refusé — pas de workspace_id pour case_id=%s",
                    case_id,
                )
                return
            db_execute(
                conn,
                """
                INSERT INTO public.offer_extractions
                  (id, workspace_id, artifact_id, supplier_name,
                   extracted_data_json, missing_fields_json, created_at)
                VALUES (:id, CAST(:wid AS uuid), :aid, :supplier, :extracted, :missing, :ts)
                """,
                {
                    "id": row["id"],
                    "wid": wid,
                    "aid": artifact_id,
                    "supplier": row["supplier"],
                    "extracted": row["extracted"],
                    "missing": row["missing"],
                    "ts": row["ts"],
                },
            )
            logger.info(
                "[BRIDGE] Inséré (workspace_id) — artifact_id=%s supplier=%s",
                artifact_id,
                row["supplier"],
            )
        elif has_case:
            db_execute(
                conn,
                """
                INSERT INTO public.offer_extractions
                  (id, case_id, artifact_id, supplier_name,
                   extracted_data_json, missing_fields_json, created_at)
                VALUES (:id, :cid, :aid, :supplier, :extracted, :missing, :ts)
                """,
                row,
            )
            logger.info(
                "[BRIDGE] Inséré (case_id legacy) — artifact_id=%s supplier=%s",
                artifact_id,
                row["supplier"],
            )
        else:
            logger.error(
                "[BRIDGE] offer_extractions sans colonne workspace_id ni case_id"
            )
