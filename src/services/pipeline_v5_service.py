"""
Pipeline V5 — Semaine 1 : enchaîne extraction bundles → M13 → M14 → bridge M16.

Connexion synchrone ``get_connection`` (RLS tenant). Pas de nouveau moteur d’extraction.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.couche_a.extraction.criterion import _OFFER_TYPE_TO_ROLE
from src.couche_a.extraction.offer_pipeline import extract_offer_content_async
from src.couche_a.extraction.persistence import persist_tdr_result_to_db
from src.couche_a.extraction_models import Tier, make_fallback_result
from src.db import db_execute_one, db_fetchall, get_connection
from src.procurement.bundle_scoring_role import (
    ScoringRole,
    classify_bundle_scoring_role,
)
from src.procurement.document_ontology import (
    DocumentKindParent,
    DocumentLayer,
    DocumentStage,
    ProcedureType,
    ProcessRole,
    ProcurementFamily,
    ProcurementFamilySub,
    ProcurementFramework,
)
from src.procurement.handoff_builder import build_handoffs
from src.procurement.m13_engine import RegulatoryComplianceEngine
from src.procurement.m13_regulatory_profile_repository import (
    M13RegulatoryProfileRepository,
)
from src.procurement.m14_engine import EvaluationEngine
from src.procurement.m14_evaluation_models import EvaluationReport, M14EvaluationInput
from src.procurement.m14_evaluation_repository import M14EvaluationRepository
from src.procurement.procedure_models import (
    DocumentConformitySignal,
    DocumentValidity,
    M12Handoffs,
    M12Meta,
    M12Output,
    ProcedureRecognition,
    ProcessLinking,
    TracedField,
)
from src.services.m14_bridge import populate_assessments_from_m14

logger = logging.getLogger(__name__)


def procurement_framework_from_tenant_code(code: str | None) -> ProcurementFramework:
    """Résout le cadre hôte M13 à partir de ``tenants.code`` (Gate A — plan directeur).

    Pilote SCI : ``sci_mali`` / ``sci_niger`` / ``sci`` → SCI. Pas de repli silencieux
    vers DGMP ; tenant non reconnu → ``UNKNOWN`` (FAIL LOUD pipeline).
    """
    c = (code or "").strip().lower()
    if c in ("sci", "sci_mali", "sci_niger"):
        return ProcurementFramework.SCI
    return ProcurementFramework.UNKNOWN


class PipelineV5Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    case_id: str | None = None
    completed: bool = False
    stopped_at: str | None = None
    error: str | None = None
    step_1_offers_extracted: int = 0
    step_2_m12_reconstructed: bool = False
    step_3_m13_procedure_type: str | None = None
    step_4_m14_eval_doc_id: str | None = None
    step_5_assessments_created: int = 0
    duration_seconds: float = 0.0
    procedure_resolution_status: str | None = None


def _tf(
    value: Any,
    confidence: float = 0.6,
    evidence: list[str] | None = None,
) -> TracedField:
    return TracedField(value=value, confidence=confidence, evidence=evidence or [])


def build_pipeline_v5_minimal_m12(
    *, corpus_text: str, procurement_framework: ProcurementFramework
) -> M12Output:
    """M12 minimal pour enchaîner M13 (H1 via ITT + texte corpus)."""
    text = corpus_text[:500_000] if corpus_text else ""
    fw = procurement_framework
    fw_conf = 0.8
    rec = ProcedureRecognition(
        framework_detected=_tf(fw, fw_conf),
        procurement_family=_tf(ProcurementFamily.GOODS),
        procurement_family_sub=_tf(ProcurementFamilySub.GENERIC),
        document_kind=_tf(DocumentKindParent.ITT),
        document_subtype=_tf(DocumentKindParent.UNKNOWN),
        is_composite=_tf(False, 1.0),
        document_layer=_tf(DocumentLayer.SOURCE_RULES),
        document_stage=_tf(DocumentStage.SOLICITATION),
        procedure_type=_tf(ProcedureType.UNKNOWN),
        procedure_reference_detected=_tf("ABSENT"),
        issuing_entity_detected=_tf("ABSENT"),
        project_name_detected=_tf("ABSENT"),
        zone_scope_detected=_tf("ABSENT"),
        submission_deadline_detected=_tf("ABSENT"),
        submission_mode_detected=_tf("ABSENT"),
        result_type_detected=_tf("ABSENT"),
        estimated_value_detected=_tf("ABSENT"),
        currency_detected=_tf("ABSENT"),
        visit_required=_tf("NOT_APPLICABLE", 1.0),
        sample_required=_tf("NOT_APPLICABLE", 1.0),
        humanitarian_context=_tf("NOT_APPLICABLE", 1.0),
        recognition_source=_tf("pipeline_v5"),
        review_status=_tf("review_required", 0.6),
    )
    validity = DocumentValidity(
        document_validity_status=_tf("NOT_ASSESSED", 0.6, ["pipeline_v5_minimal"]),
    )
    conformity = DocumentConformitySignal(
        offer_composition_hint=_tf("ABSENT", 0.6),
        document_conformity_status=_tf("NOT_ASSESSED", 0.6),
        document_scope=_tf("case_level", 0.6),
        gates=[],
        eligibility_gates_extracted=[],
    )
    linking = ProcessLinking(
        process_role=_tf(ProcessRole.UNKNOWN),
        procedure_end_marker=_tf(False, 1.0, ["pipeline_v5"]),
    )
    hh: M12Handoffs = build_handoffs(
        DocumentKindParent.ITT,
        fw,
        fw_conf,
        ProcurementFamily.GOODS,
        ProcurementFamilySub.GENERIC,
        [],
        None,
        text,
    )
    meta = M12Meta(
        mode="bootstrap",
        confidence_ceiling=1.0,
        corpus_size_at_processing=len(text),
        processing_timestamp=datetime.now(UTC).isoformat(),
        pass_sequence=["pipeline_v5"],
    )
    return M12Output(
        procedure_recognition=rec,
        document_validity=validity,
        document_conformity_signal=conformity,
        process_linking=linking,
        handoffs=hh,
        m12_meta=meta,
    )


def build_matrix_participants_and_excluded(
    report: EvaluationReport,
    *,
    bundle_roles: dict[str, ScoringRole],
    vendor_by_bundle: dict[str, str],
    extract_failed_bundles: frozenset[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Gate C (CTO D-06) — vérité matrice vs archive M14 brute (sans toucher m14_engine).

    ``matrix_participants`` : bundles éligibles pour ``criterion_assessments``.
    ``excluded_from_matrix`` : inéligibles / indéterminés / SCORABLE hors run M14.
    """
    matrix_participants: list[dict[str, Any]] = []
    excluded_from_matrix: list[dict[str, Any]] = []

    for oe in report.offer_evaluations:
        bid = str(oe.offer_document_id)
        supplier = (oe.supplier_name or vendor_by_bundle.get(bid) or "").strip()
        elig = oe.is_eligible
        if elig is True:
            matrix_participants.append(
                {
                    "bundle_id": bid,
                    "supplier_name": supplier,
                    "is_eligible": True,
                }
            )
            continue
        failed_checks: list[str] = []
        for chk in oe.eligibility_results or []:
            if getattr(chk, "result", None) == "FAIL":
                failed_checks.append(
                    f"{getattr(chk, 'check_id', '')}:{getattr(chk, 'check_name', '')}"
                )
        if elig is False:
            reason = "ineligible"
        elif elig is None:
            reason = "eligibility_indeterminate"
        else:
            reason = "eligibility_unknown"
        excluded_from_matrix.append(
            {
                "bundle_id": bid,
                "supplier_name": supplier,
                "reason": reason,
                "failed_eligibility_checks": failed_checks,
            }
        )

    evaluated_ids = {str(oe.offer_document_id) for oe in report.offer_evaluations}
    for bid, role in bundle_roles.items():
        if bid in evaluated_ids:
            continue
        if role != ScoringRole.SCORABLE:
            continue
        reason = (
            "extraction_failed"
            if bid in extract_failed_bundles
            else "not_in_m14_offer_list"
        )
        excluded_from_matrix.append(
            {
                "bundle_id": bid,
                "supplier_name": (vendor_by_bundle.get(bid) or "").strip(),
                "reason": reason,
            }
        )

    return matrix_participants, excluded_from_matrix


def _vendor_name_by_bundle(workspace_id: str) -> dict[str, str]:
    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT id::text AS id, vendor_name_raw
            FROM supplier_bundles
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": workspace_id},
        )
    return {str(r["id"]): str(r.get("vendor_name_raw") or "") for r in rows or []}


def _bundle_scoring_roles_for_workspace(workspace_id: str) -> dict[str, ScoringRole]:
    """Rôle scoring runtime par ``supplier_bundles.id`` (CTO D-03, sans migration)."""
    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT sb.id::text AS bundle_id, sb.vendor_name_raw,
                   COALESCE(
                       array_agg(bd.doc_type::text)
                       FILTER (WHERE bd.doc_type IS NOT NULL),
                       ARRAY[]::text[]
                   ) AS doc_types
            FROM supplier_bundles sb
            LEFT JOIN bundle_documents bd ON bd.bundle_id = sb.id
            WHERE sb.workspace_id = CAST(:wid AS uuid)
            GROUP BY sb.id, sb.vendor_name_raw
            """,
            {"wid": workspace_id},
        )
    out: dict[str, ScoringRole] = {}
    for r in rows or []:
        bid = r.get("bundle_id")
        if not bid:
            continue
        raw = r.get("doc_types")
        if raw is None:
            dtypes: frozenset[str] = frozenset()
        elif isinstance(raw, list):
            dtypes = frozenset(str(x) for x in raw if x)
        else:
            dtypes = frozenset()
        out[str(bid)] = classify_bundle_scoring_role(
            vendor_name_raw=str(r.get("vendor_name_raw") or ""),
            doc_types=dtypes,
        )
    return out


def extract_offers_from_bundles(
    workspace_id: str, case_id: str
) -> tuple[int, frozenset[str]]:
    """
    Pour chaque supplier_bundle : concatène ``bundle_documents.raw_text``,
    appelle ``extract_offer_content_async`` + ``persist_tdr_result_to_db``.
    ``bundle_id`` = ``supplier_bundles.id`` (idempotent sur ``offer_extractions``).

    Returns:
        (nombre d'extractions persistées, bundle_ids SCORABLE où Mistral a échoué
        sans persistance fallback).
    """
    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT sb.id::text AS bundle_id, sb.vendor_name_raw AS vendor_name,
                   bd.raw_text, bd.doc_type
            FROM supplier_bundles sb
            LEFT JOIN bundle_documents bd ON bd.bundle_id = sb.id
            WHERE sb.workspace_id = CAST(:wid AS uuid)
            ORDER BY sb.bundle_index, bd.uploaded_at NULLS LAST
            """,
            {"wid": workspace_id},
        )

    by_bundle: dict[str, dict[str, Any]] = {}
    for r in rows:
        bid = r.get("bundle_id")
        if not bid:
            continue
        entry = by_bundle.setdefault(
            bid,
            {
                "vendor_name": r.get("vendor_name") or "",
                "chunks": [],
                "doc_types": set(),
            },
        )
        dt = r.get("doc_type")
        if dt:
            entry["doc_types"].add(str(dt))
        raw = r.get("raw_text")
        if isinstance(raw, str) and raw.strip():
            entry["chunks"].append(raw.strip())
        if r.get("doc_type") in (
            "offer_financial",
            "offer_technical",
            "offer_combined",
        ):
            entry["offer_doc_type"] = r["doc_type"]

    n_ok = 0
    failed_scorable: set[str] = set()
    for bundle_id, data in by_bundle.items():
        role = classify_bundle_scoring_role(
            vendor_name_raw=str(data.get("vendor_name") or ""),
            doc_types=frozenset(data.get("doc_types") or ()),
        )
        if role != ScoringRole.SCORABLE:
            logger.info(
                "[PIPELINE-V5] skip extraction scoring_role=%s bundle_id=%s",
                role,
                bundle_id,
            )
            continue

        text = "\n\n".join(data["chunks"])
        if not text.strip():
            logger.warning(
                "[PIPELINE-V5] bundle sans raw_text — skip extraction bundle_id=%s",
                bundle_id,
            )
            continue

        offer_key = str(data.get("offer_doc_type") or "offer_combined")
        if offer_key == "offer_financial":
            offer_type = "financiere"
        elif offer_key == "offer_technical":
            offer_type = "technique"
        else:
            offer_type = "technique"

        role = _OFFER_TYPE_TO_ROLE.get(offer_type, "technical_offer")
        logger.info(
            "[PIPELINE-V5] extract bundle_id=%s vendor=%s text_len=%s role=%s",
            bundle_id,
            (data.get("vendor_name") or "")[:80],
            len(text),
            role,
        )

        try:
            result = asyncio.run(
                extract_offer_content_async(
                    document_id=bundle_id,
                    text=text,
                    document_role=role,
                )
            )
            persist_tdr_result_to_db(
                result, case_id, bundle_id, workspace_id=workspace_id
            )
            n_ok += 1
        except Exception as exc:
            logger.exception(
                "[PIPELINE-V5] extract KO bundle_id=%s : %s", bundle_id, exc
            )
            vendor_fallback = str(data.get("vendor_name") or "").strip()
            if vendor_fallback:
                try:
                    fb = make_fallback_result(
                        bundle_id,
                        role,
                        f"extract_exception:{str(exc)[:200]}",
                        tier=Tier.T4_OFFLINE,
                    )
                    fb = replace(
                        fb,
                        raw_annotation={
                            "identifiants": {
                                "supplier_name_raw": vendor_fallback,
                                "supplier_name_normalized": vendor_fallback,
                            }
                        },
                    )
                    persist_tdr_result_to_db(
                        fb, case_id, bundle_id, workspace_id=workspace_id
                    )
                    n_ok += 1
                    logger.warning(
                        "[PIPELINE-V5] P1.6 fallback vendor_name_raw bundle_id=%s",
                        bundle_id,
                    )
                except Exception:
                    logger.exception(
                        "[PIPELINE-V5] P1.6 fallback persist KO bundle_id=%s",
                        bundle_id,
                    )
                    failed_scorable.add(bundle_id)
            else:
                failed_scorable.add(bundle_id)

    return n_ok, frozenset(failed_scorable)


def run_pipeline_v5(
    workspace_id: str,
    *,
    force_m14: bool = False,
) -> PipelineV5Result:
    t0 = time.perf_counter()
    out = PipelineV5Result(workspace_id=workspace_id)
    fw_value: ProcurementFramework = ProcurementFramework.UNKNOWN
    extract_failed_bundles: frozenset[str] = frozenset()

    try:
        with get_connection() as conn:
            ws = db_execute_one(
                conn,
                """
                SELECT w.id::text AS id, w.legacy_case_id::text AS legacy_case_id,
                       lower(t.code::text) AS tenant_code
                FROM process_workspaces w
                JOIN tenants t ON t.id = w.tenant_id
                WHERE w.id = CAST(:wid AS uuid)
                """,
                {"wid": workspace_id},
            )
            if not ws:
                out.error = "workspace_not_found"
                out.stopped_at = "precheck_workspace"
                return out

            fw_value = procurement_framework_from_tenant_code(ws.get("tenant_code"))
            if fw_value == ProcurementFramework.UNKNOWN:
                out.error = "tenant_framework_unknown"
                out.stopped_at = "precheck_framework"
                out.duration_seconds = time.perf_counter() - t0
                return out

            case_id = ws.get("legacy_case_id")
            out.case_id = case_id
            if not case_id:
                out.error = "legacy_case_id_missing"
                out.stopped_at = "precheck_case"
                return out

            ndocs = db_execute_one(
                conn,
                """
                SELECT COUNT(*)::int AS n
                FROM bundle_documents
                WHERE workspace_id = CAST(:wid AS uuid)
                  AND raw_text IS NOT NULL
                  AND trim(raw_text) <> ''
                """,
                {"wid": workspace_id},
            )
            if not ndocs or ndocs["n"] < 1:
                out.error = "no_bundle_raw_text"
                out.stopped_at = "precheck_bundles"
                return out

            ndao = db_execute_one(
                conn,
                """
                SELECT COUNT(*)::int AS n FROM dao_criteria
                WHERE workspace_id = CAST(:wid AS uuid)
                """,
                {"wid": workspace_id},
            )
            if not ndao or ndao["n"] < 1:
                out.error = "no_dao_criteria"
                out.stopped_at = "precheck_criteria"
                return out

            com = db_execute_one(
                conn,
                """
                SELECT c.committee_id::text AS id FROM committees c
                INNER JOIN process_workspaces w
                  ON w.legacy_case_id = c.case_id
                WHERE w.id = CAST(:wid AS uuid)
                LIMIT 1
                """,
                {"wid": workspace_id},
            )
            if not com:
                out.error = "no_committee_for_case"
                out.stopped_at = "precheck_committee"
                return out

        n_ext, extract_failed_bundles = extract_offers_from_bundles(
            workspace_id, case_id
        )
        out.step_1_offers_extracted = n_ext
        if n_ext < 1:
            out.error = "zero_offer_extractions"
            out.stopped_at = "step_extract"
            out.duration_seconds = time.perf_counter() - t0
            return out

        with get_connection() as conn2:
            corpus_parts = db_fetchall(
                conn2,
                """
                SELECT bd.raw_text
                FROM bundle_documents bd
                WHERE bd.workspace_id = CAST(:wid AS uuid)
                  AND bd.raw_text IS NOT NULL
                  AND trim(bd.raw_text) <> ''
                ORDER BY bd.uploaded_at
                LIMIT 200
                """,
                {"wid": workspace_id},
            )
        corpus_text = "\n\n".join(
            str(r["raw_text"]).strip() for r in corpus_parts if r.get("raw_text")
        )
    except Exception as exc:
        out.error = str(exc)[:500]
        out.stopped_at = "exception"
        out.duration_seconds = time.perf_counter() - t0
        logger.exception("[PIPELINE-V5] fatal: %s", exc)
        return out

    m12 = build_pipeline_v5_minimal_m12(
        corpus_text=corpus_text, procurement_framework=fw_value
    )
    out.step_2_m12_reconstructed = True

    doc_id = f"pipeline_v5:{workspace_id}"
    engine_m13 = RegulatoryComplianceEngine(
        repository=M13RegulatoryProfileRepository(),
    )
    try:
        m13_out = engine_m13.process_m12(case_id=case_id, document_id=doc_id, m12=m12)
        out.step_3_m13_procedure_type = m13_out.report.regime.procedure_type.value
        out.procedure_resolution_status = (
            f"{m13_out.report.regime.framework.value}"
            f":{m13_out.report.regime.procedure_type.value}"
        )
    except Exception as exc:
        out.error = f"m13_failed:{exc}"[:500]
        out.stopped_at = "step_m13"
        out.duration_seconds = time.perf_counter() - t0
        logger.exception("[PIPELINE-V5] M13: %s", exc)
        return out

    bundle_roles = _bundle_scoring_roles_for_workspace(workspace_id)
    with get_connection() as conn:
        offers_rows = db_fetchall(
            conn,
            """
            SELECT bundle_id::text AS bundle_id, supplier_name,
                   extracted_data_json
            FROM offer_extractions
            WHERE workspace_id = CAST(:wid AS uuid)
            ORDER BY created_at DESC
            """,
            {"wid": workspace_id},
        )

    offers: list[dict[str, Any]] = []
    for r in offers_rows:
        bid = str(r.get("bundle_id") or "")
        if bundle_roles.get(bid) != ScoringRole.SCORABLE:
            continue
        offers.append(
            {
                "document_id": r["bundle_id"],
                "supplier_name": r.get("supplier_name"),
                "process_role": "responds_to_bid",
            }
        )

    h2 = (
        m12.handoffs.atomic_capability_skeleton.model_dump(mode="json")
        if m12.handoffs.atomic_capability_skeleton
        else {}
    )
    h3 = (
        m12.handoffs.market_context_signal.model_dump(mode="json")
        if m12.handoffs.market_context_signal
        else {}
    )

    inp = M14EvaluationInput(
        case_id=case_id,
        source_rules_document_id=doc_id,
        offers=offers,
        h2_capability_skeleton=h2,
        h3_market_context=h3,
        rh1_compliance_checklist=m13_out.compliance_checklist.model_dump(mode="json"),
        rh2_evaluation_blueprint=m13_out.evaluation_blueprint.model_dump(mode="json"),
        process_linking_data=[],
    )

    skip_m14 = False
    if not force_m14:
        with get_connection() as conn:
            existing = db_execute_one(
                conn,
                """
                SELECT id::text AS id FROM evaluation_documents
                WHERE workspace_id = CAST(:wid AS uuid)
                LIMIT 1
                """,
                {"wid": workspace_id},
            )
            if existing:
                skip_m14 = True
                out.step_4_m14_eval_doc_id = existing["id"]
                logger.info(
                    "[PIPELINE-V5] skip M14 evaluate (document exists) wid=%s",
                    workspace_id,
                )

    if not skip_m14 and not offers:
        out.error = "no_scorable_offers_for_m14"
        out.stopped_at = "precheck_m14_offers"
        out.duration_seconds = time.perf_counter() - t0
        return out

    if not skip_m14:
        repo_m14 = M14EvaluationRepository()
        engine_m14 = EvaluationEngine(repository=repo_m14)
        try:
            report = engine_m14.evaluate(inp)
            payload = report.model_dump(mode="json")
            if out.procedure_resolution_status:
                payload["procedure_resolution_status"] = out.procedure_resolution_status
            vendor_map = _vendor_name_by_bundle(workspace_id)
            mp_list, ex_list = build_matrix_participants_and_excluded(
                report,
                bundle_roles=bundle_roles,
                vendor_by_bundle=vendor_map,
                extract_failed_bundles=extract_failed_bundles,
            )
            payload["matrix_participants"] = mp_list
            payload["excluded_from_matrix"] = ex_list
            saved = repo_m14.save_evaluation(case_id=case_id, payload=payload)
            out.step_4_m14_eval_doc_id = saved
        except Exception as exc:
            out.error = f"m14_failed:{exc}"[:500]
            out.stopped_at = "step_m14"
            out.duration_seconds = time.perf_counter() - t0
            logger.exception("[PIPELINE-V5] M14: %s", exc)
            return out

    try:
        bridge = populate_assessments_from_m14(workspace_id)
        out.step_5_assessments_created = bridge.created + bridge.updated
    except Exception as exc:
        logger.exception("[PIPELINE-V5] bridge M14→M16: %s", exc)
        out.error = f"bridge_failed:{exc}"[:500]
        out.stopped_at = "step_bridge"
        out.duration_seconds = time.perf_counter() - t0
        return out

    out.completed = True
    out.duration_seconds = time.perf_counter() - t0
    logger.info(
        "[PIPELINE-V5] terminé wid=%s offers=%s m13=%s eval=%s assessments=%s t=%.2fs",
        workspace_id,
        out.step_1_offers_extracted,
        out.step_3_m13_procedure_type,
        out.step_4_m14_eval_doc_id,
        out.step_5_assessments_created,
        out.duration_seconds,
    )
    return out
