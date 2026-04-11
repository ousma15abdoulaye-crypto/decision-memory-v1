"""
Pipeline V5 — Semaine 1 : enchaîne extraction bundles → M13 → M14 → bridge M16.

Connexion synchrone ``get_connection`` (RLS tenant). Pas de nouveau moteur d’extraction.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.core.config import get_settings
from src.couche_a.extraction.criterion import _OFFER_TYPE_TO_ROLE
from src.couche_a.extraction.offer_pipeline import extract_offer_content_async
from src.couche_a.extraction.persistence import persist_tdr_result_to_db
from src.db import db_execute_one, db_fetchall, get_connection
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
from src.procurement.m14_evaluation_models import M14EvaluationInput
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


def _run_coro_blocking(coro):
    """Exécute une coroutine depuis du code sync.

    Si une boucle asyncio tourne déjà (ex. ``pytest-asyncio``), ``asyncio.run``
    lève *cannot be called from a running event loop* — on isole alors un
    thread avec sa propre boucle.

    Budget temps : ``ANNOTATION_TIMEOUT`` + 30 s (aligné extraction HTTP + marge).
    """
    timeout_sec = float(get_settings().ANNOTATION_TIMEOUT) + 30.0

    async def _with_timeout():
        return await asyncio.wait_for(coro, timeout=timeout_sec)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_with_timeout())

    def _in_thread():
        return asyncio.run(_with_timeout())

    # Même plafond côté thread + petite marge pour teardown de la boucle.
    thread_cap = timeout_sec + 5.0
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_in_thread).result(timeout=thread_cap)


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


def _tf(
    value: Any,
    confidence: float = 0.6,
    evidence: list[str] | None = None,
) -> TracedField:
    return TracedField(value=value, confidence=confidence, evidence=evidence or [])


def _detect_framework_from_corpus(text: str) -> tuple[ProcurementFramework, float]:
    """Détection heuristique framework depuis corpus ITT/DAO.

    Returns: (framework, confidence)
    """
    text_lower = text.lower()

    # DGMP Mali markers
    dgmp_markers = [
        "direction générale des marchés publics",
        "dgmp",
        "république du mali",
        "code des marchés publics",
        "armp mali",
        "décret n°",
    ]
    dgmp_count = sum(1 for m in dgmp_markers if m in text_lower)

    # SCI markers
    sci_markers = [
        "save the children",
        "sci procurement",
        "humanitarian procurement",
        "donor compliance",
    ]
    sci_count = sum(1 for m in sci_markers if m in text_lower)

    if dgmp_count >= 2:
        return ProcurementFramework.DGMP_MALI, 0.8
    elif dgmp_count == 1:
        return ProcurementFramework.DGMP_MALI, 0.6
    elif sci_count >= 2:
        return ProcurementFramework.SCI, 0.8
    elif sci_count == 1:
        return ProcurementFramework.SCI, 0.6
    else:
        return ProcurementFramework.UNKNOWN, 0.6


def build_pipeline_v5_minimal_m12(*, corpus_text: str) -> M12Output:
    """M12 bootstrap pour M13 — détection framework + corpus complet.

    FIX BUG 1: framework_detected maintenant inféré du corpus (DGMP vs SCI).
    M13 peut résoudre procedure_type si framework != UNKNOWN.
    """
    text = corpus_text[:500_000] if corpus_text else ""
    framework, fw_conf = _detect_framework_from_corpus(text)

    logger.info(
        "[PIPELINE-V5] M12 build — framework=%s confidence=%.1f corpus_len=%d",
        framework.value,
        fw_conf,
        len(text),
    )

    rec = ProcedureRecognition(
        framework_detected=_tf(framework, fw_conf),
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
        recognition_source=_tf("pipeline_v5_heuristic"),
        review_status=_tf("review_required", 0.6),
    )
    validity = DocumentValidity(
        document_validity_status=_tf("NOT_ASSESSED", 0.6, ["pipeline_v5_bootstrap"]),
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
        framework,
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
        pass_sequence=["pipeline_v5_heuristic"],
    )
    return M12Output(
        procedure_recognition=rec,
        document_validity=validity,
        document_conformity_signal=conformity,
        process_linking=linking,
        handoffs=hh,
        m12_meta=meta,
    )


def extract_offers_from_bundles(workspace_id: str, case_id: str) -> int:
    """
    Pour chaque supplier_bundle : concatène ``bundle_documents.raw_text``,
    appelle ``extract_offer_content_async`` + ``persist_tdr_result_to_db``.
    ``bundle_id`` = ``supplier_bundles.id`` (idempotent sur ``offer_extractions``).
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
            {"vendor_name": r.get("vendor_name") or "", "chunks": []},
        )
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
    for bundle_id, data in by_bundle.items():
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
            result = _run_coro_blocking(
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

    return n_ok


def run_pipeline_v5(
    workspace_id: str,
    *,
    force_m14: bool = False,
) -> PipelineV5Result:
    t0 = time.perf_counter()
    out = PipelineV5Result(workspace_id=workspace_id)

    try:
        with get_connection() as conn:
            ws = db_execute_one(
                conn,
                """
                SELECT id::text AS id, legacy_case_id::text AS legacy_case_id
                FROM process_workspaces
                WHERE id = CAST(:wid AS uuid)
                """,
                {"wid": workspace_id},
            )
            if not ws:
                out.error = "workspace_not_found"
                out.stopped_at = "precheck_workspace"
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

        n_ext = extract_offers_from_bundles(workspace_id, case_id)
        out.step_1_offers_extracted = n_ext
        if n_ext < 1:
            with get_connection() as conn_sb:
                nb = db_execute_one(
                    conn_sb,
                    """
                    SELECT COUNT(*)::int AS n
                    FROM supplier_bundles
                    WHERE workspace_id = CAST(:wid AS uuid)
                    """,
                    {"wid": workspace_id},
                )
            if not nb or nb.get("n", 0) < 1:
                out.error = "zero_offer_extractions"
                out.stopped_at = "step_extract"
                out.duration_seconds = time.perf_counter() - t0
                return out
            logger.warning(
                "[PIPELINE-V5] aucune offer_extraction — poursuite M14 via bundles "
                "workspace=%s",
                workspace_id,
            )

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

    m12 = build_pipeline_v5_minimal_m12(corpus_text=corpus_text)
    out.step_2_m12_reconstructed = True

    doc_id = f"pipeline_v5:{workspace_id}"
    engine_m13 = RegulatoryComplianceEngine(
        repository=M13RegulatoryProfileRepository(),
    )
    try:
        m13_out = engine_m13.process_m12(case_id=case_id, document_id=doc_id, m12=m12)
        out.step_3_m13_procedure_type = m13_out.report.regime.procedure_type.value
    except Exception as exc:
        out.error = f"m13_failed:{exc}"[:500]
        out.stopped_at = "step_m13"
        out.duration_seconds = time.perf_counter() - t0
        logger.exception("[PIPELINE-V5] M13: %s", exc)
        return out

    from src.procurement.m14_workspace_assembler import build_m14_offers_for_workspace

    with get_connection() as conn:
        offers = build_m14_offers_for_workspace(conn, workspace_id)
    if not offers:
        out.error = "zero_m14_offers"
        out.stopped_at = "step_m14_offers"
        out.duration_seconds = time.perf_counter() - t0
        return out

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

    if not skip_m14:
        repo_m14 = M14EvaluationRepository()
        engine_m14 = EvaluationEngine(repository=repo_m14)
        try:
            engine_m14.evaluate(inp)
            with get_connection() as conn:
                row = db_execute_one(
                    conn,
                    """
                    SELECT id::text AS id FROM evaluation_documents
                    WHERE workspace_id = CAST(:wid AS uuid)
                    ORDER BY version DESC, created_at DESC
                    LIMIT 1
                    """,
                    {"wid": workspace_id},
                )
            out.step_4_m14_eval_doc_id = row["id"] if row else None
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
