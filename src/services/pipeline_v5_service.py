"""
Pipeline V5 — Semaine 1 : enchaîne extraction bundles → M13 → M14 → bridge M16.

Connexion synchrone ``get_connection`` (RLS tenant). Pas de nouveau moteur d’extraction.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.core.models import DAOCriterion
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
from src.procurement.eligibility_gate import (
    build_vendor_gate_input_from_bundle_documents,
    run_eligibility_gate,
)
from src.procurement.eligibility_models import GateOutput, VendorGateInput
from src.procurement.handoff_builder import build_handoffs
from src.procurement.m13_engine import RegulatoryComplianceEngine
from src.procurement.m13_regulatory_profile_repository import (
    M13RegulatoryProfileRepository,
)
from src.procurement.m14_engine import EvaluationEngine
from src.procurement.m14_evaluation_models import (
    DAO_CRITERION_ID_UUID_RE,
    EvaluationReport,
    M14EvaluationInput,
    ProcessLinkingEntry,
    ProcessLinkingType,
    m14_h2_scoring_structure_dict_from_dao_criteria_rows,
    scoring_structure_detected_from_dao_criteria_rows,
)
from src.procurement.m14_evaluation_repository import M14EvaluationRepository
from src.procurement.matrix_models import MatrixRow, MatrixSummary
from src.procurement.procedure_models import (
    DocumentConformitySignal,
    DocumentValidity,
    M12Handoffs,
    M12Meta,
    M12Output,
    ProcedureRecognition,
    ProcessLinking,
    ScoringStructureDetected,
    TracedField,
)
from src.services.m14_bridge import (
    PipelineError as BridgePipelineError,
)
from src.services.m14_bridge import (
    populate_assessments_from_m14,
)
from src.services.matrix_builder_service import (
    build_matrix_rows,
    build_matrix_summary,
)

logger = logging.getLogger(__name__)


class PipelineConfigurationError(RuntimeError):
    """Configuration workspace / DAO insuffisante pour exécuter le pipeline."""


class PipelineError(RuntimeError):
    """Fail-fast pipeline (prérequis H1 avant M13)."""


# P3.1B — raisons d’exclusion matrice reconnues (merge Gate C + échecs P3.1).
EXCLUSION_REASONS: frozenset[str] = frozenset(
    {
        "ineligible",
        "eligibility_indeterminate",
        "eligibility_unknown",
        "extraction_failed",
        "not_in_m14_offer_list",
        "internal_reference_bundle",
        "reference_bundle",
        "eligibility_fail",
    }
)


def run_p3_1b_eligibility_gate_phase(
    workspace_id: str,
    case_id: str | None,
    offers: list[dict[str, Any]],
    doc_groups: dict[str, list[dict[str, Any]]],
    bundle_status_by_bundle_id: dict[str, str],
    vendor_by_bundle: dict[str, str],
) -> tuple[list[dict[str, Any]], GateOutput]:
    """P3.1B — exécute EligibilityGate sur les offres Gate-B-SCORABLE ; filtre ``offers``."""
    lot_id = case_id or workspace_id
    if not offers:
        return [], run_eligibility_gate(workspace_id, lot_id, {})
    vendors_map: dict[str, VendorGateInput] = {}
    for o in offers:
        bid = str(o["document_id"])
        rows = doc_groups.get(bid) or []
        vname = str(o.get("supplier_name") or vendor_by_bundle.get(bid) or "")
        st = bundle_status_by_bundle_id.get(bid)
        vendors_map[bid] = build_vendor_gate_input_from_bundle_documents(
            bid,
            vendor_name=vname,
            rows=rows,
            bundle_gate_b_status=st,
        )
    gate_out = run_eligibility_gate(workspace_id, lot_id, vendors_map)
    elig = set(gate_out.eligible_vendor_ids)
    filtered = [o for o in offers if str(o["document_id"]) in elig]
    return filtered, gate_out


def eligibility_verdicts_summary_from_gate_output(gate: GateOutput) -> dict[str, Any]:
    """Résumé sérialisable des verdicts P3.1 (R7)."""
    summary: dict[str, Any] = {}
    for vid, ver in gate.verdicts.items():
        summary[vid] = {
            "eligible": ver.eligible,
            "gate_result": ver.gate_result,
            "failing_criteria": list(ver.failing_criteria),
            "pending_criteria": list(ver.pending_criteria),
            "dominant_cause": ver.dominant_cause,
        }
    return summary


def merge_p3_eligibility_gate_failures_into_excluded(
    excluded_from_matrix: list[dict[str, Any]],
    gate_output: GateOutput,
    vendor_by_bundle: dict[str, str],
) -> None:
    """Fusionne les échecs P3.1 (FAIL) dans ``excluded_from_matrix`` (P3.1B R2).

    Les vendors PENDING ne sont pas ajoutés ici (liste ``pending_vendor_ids`` sur le résultat).
    """
    seen = {str(x.get("bundle_id")) for x in excluded_from_matrix}
    for vid in gate_output.excluded_vendor_ids:
        if vid in seen:
            continue
        ver = gate_output.verdicts.get(vid)
        failed: list[str] = []
        if ver is not None:
            dom = ver.dominant_cause or ver.gate_result
            failed = [
                f"p3.1:{dom}",
                *[f"p3.1:failing:{c}" for c in (ver.failing_criteria or [])],
            ]
        excluded_from_matrix.append(
            {
                "bundle_id": vid,
                "supplier_name": (vendor_by_bundle.get(vid) or "").strip(),
                "reason": "eligibility_fail",
                "failed_eligibility_checks": failed,
            }
        )
        seen.add(vid)


def _ensure_m14_scoring_structure_for_scorable_offers(
    offers: list[dict[str, Any]],
    m14_scoring_h2: dict[str, Any],
) -> None:
    """D-003 — pas de scoring implicite vide quand des offres Gate B vont à M14."""
    if offers and not m14_scoring_h2.get("criteria"):
        raise PipelineError(
            "pipeline_invalid:m14_scoring_structure_empty — "
            "dao_criteria ne produit aucun critère UUID exploitable pour M14 alors "
            "que des offres scorables sont présentes (Gate B)."
        )


def _require_dao_criteria_for_pipeline(
    workspace_id: str, dao_criteria_rows: list[dict[str, Any]]
) -> None:
    if not dao_criteria_rows:
        raise PipelineConfigurationError(
            f"[PIPELINE] workspace {workspace_id} : aucun dao_criteria défini. "
            "Impossible de scorer. Arrêt."
        )


def _dao_criteria_rows_to_models(rows: list[dict[str, Any]]) -> list[DAOCriterion]:
    """Convertit les lignes ``dao_criteria`` DB en ``DAOCriterion`` pour le builder matrice."""
    out: list[DAOCriterion] = []
    for i, row in enumerate(rows):
        out.append(
            DAOCriterion(
                categorie=str(row.get("famille") or "general"),
                critere_nom=str(row.get("critere_nom") or "").strip() or "criterion",
                description="",
                ponderation=float(row.get("ponderation") or 0.0),
                type_reponse="numeric",
                seuil_elimination=None,
                ordre_affichage=i,
            )
        )
    return out


def _technical_threshold_config_for_workspace(workspace_id: str) -> dict[str, Any] | None:
    """Lit ``technical_threshold_mode`` sur ``process_workspaces`` si la colonne existe (E0.4)."""
    try:
        with get_connection() as conn:
            row = db_execute_one(
                conn,
                """
                SELECT technical_threshold_mode::text AS mode
                FROM process_workspaces
                WHERE id = CAST(:wid AS uuid)
                """,
                {"wid": workspace_id},
            )
    except Exception:
        logger.debug(
            "[PIPELINE-V5] technical_threshold_mode absent ou illisible pour wid=%s",
            workspace_id,
            exc_info=True,
        )
        return None
    if not row or row.get("mode") in (None, ""):
        return None
    return {"threshold_mode": str(row["mode"]).strip()}


def build_matrix_projection_for_pipeline(
    *,
    workspace_id: str,
    gate_output: GateOutput | None,
    report: EvaluationReport,
    dao_criteria_rows: list[dict[str, Any]],
    technical_threshold_config: dict[str, Any] | None = None,
    pipeline_run_id: UUID | None = None,
) -> tuple[list[MatrixRow], MatrixSummary, UUID]:
    """P3.4 E3 — projection matrice ; ``ValueError`` si ``gate_output`` absent."""
    if gate_output is None:
        raise ValueError("gate_output is required for matrix projection")
    rid = pipeline_run_id or uuid4()
    wid = UUID(str(workspace_id).strip())
    dao_models = _dao_criteria_rows_to_models(dao_criteria_rows)
    rows = build_matrix_rows(
        wid,
        rid,
        report.offer_evaluations,
        gate_output,
        dao_models,
        technical_threshold_config,
    )
    summary = build_matrix_summary(rows, wid, rid)
    return rows, summary, rid


def procurement_framework_from_tenant_code(code: str | None) -> ProcurementFramework:
    """Résout le cadre hôte M13 à partir de ``tenants.code`` (Gate A — plan directeur)."""
    c = (code or "").strip().lower()
    if "sci" in c:
        return ProcurementFramework.SCI
    if "dgmp" in c or "mali_gov" in c:
        return ProcurementFramework.DGMP_MALI
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
    gate_b_exclusions: list[dict[str, Any]] = Field(default_factory=list)
    gate_b_m14_bundle_count: int = 0
    # D-005 — vue canonique additive (regroupement métier) ; ne substitue pas les UUID DAO.
    merged_criteria: list[dict[str, Any]] = Field(default_factory=list)
    merged_criteria_warnings: list[str] = Field(default_factory=list)
    # Phase 1 Gate B/C traceability (CTO D-06 + mandat 2026-04-16)
    bundle_status_by_bundle_id: dict[str, str] = Field(default_factory=dict)
    offers_submitted_to_m14: list[str] = Field(default_factory=list)
    # P3.1B — post-Gate-B, pré / post EligibilityGate (R7).
    eligible_vendor_ids: list[str] = Field(default_factory=list)
    excluded_vendor_ids: list[str] = Field(default_factory=list)
    pending_vendor_ids: list[str] = Field(default_factory=list)
    eligibility_verdicts_summary: dict[str, Any] = Field(default_factory=dict)
    matrix_participants: list[dict[str, Any]] = Field(default_factory=list)
    excluded_from_matrix: list[dict[str, Any]] = Field(default_factory=list)
    matrix_rows: list[MatrixRow] = Field(default_factory=list)
    matrix_summary: MatrixSummary | None = None


def _tf(
    value: Any,
    confidence: float = 0.6,
    evidence: list[str] | None = None,
) -> TracedField:
    return TracedField(value=value, confidence=confidence, evidence=evidence or [])


def _map_doc_type_str_to_document_kind(doc_type: str | None) -> DocumentKindParent:
    """Mappe ``bundle_documents.doc_type`` → ``DocumentKindParent`` (D-001)."""
    s = (doc_type or "").strip().lower()
    if s in ("offer", "quotation", "vendor_offer"):
        return DocumentKindParent.OFFER_COMBINED
    if s == "technical_proposal":
        return DocumentKindParent.OFFER_TECHNICAL
    if s == "financial_proposal":
        return DocumentKindParent.OFFER_FINANCIAL
    if s == "rfq":
        return DocumentKindParent.RFQ
    if s == "dao":
        return DocumentKindParent.DAO
    if s == "itb":
        return DocumentKindParent.ITT
    if s in ("policy", "internal", "pv", "minutes"):
        return DocumentKindParent.TDR
    return DocumentKindParent.UNKNOWN


def _map_raw_doc_type_to_scoring_alias(doc_type: str | None) -> str:
    """Aligne les ``doc_type`` DB sur les libellés attendus par ``classify_bundle_scoring_role``."""
    s = (doc_type or "").strip().lower()
    if s in ("offer", "quotation", "vendor_offer"):
        return "offer_combined"
    if s == "technical_proposal":
        return "offer_technical"
    if s == "financial_proposal":
        return "offer_financial"
    if s in ("rfq", "dao"):
        return s
    if s == "itb":
        return "itt"
    if s in ("policy", "internal", "pv", "minutes"):
        return "tdr"
    return "__unclassified__"


def _dominant_document_kind(kinds: list[DocumentKindParent]) -> DocumentKindParent:
    """Type dominant du bundle (offre > technique > …)."""
    order = (
        DocumentKindParent.OFFER_COMBINED,
        DocumentKindParent.OFFER_TECHNICAL,
        DocumentKindParent.OFFER_FINANCIAL,
        DocumentKindParent.ITT,
        DocumentKindParent.DAO,
        DocumentKindParent.RFQ,
        DocumentKindParent.TDR,
        DocumentKindParent.UNKNOWN,
    )
    uniq = list(dict.fromkeys(kinds))
    for k in order:
        if k in uniq:
            return k
    return DocumentKindParent.UNKNOWN


def _bundle_scoring_role_for_pipeline(
    bundle_id: str,
    vendor_name_raw: str,
    raw_doc_types: frozenset[str],
) -> ScoringRole:
    """ScoringRole par bundle — D-001 + règle UNCLASSIFIED (inclusion par défaut)."""
    aliases = {
        _map_raw_doc_type_to_scoring_alias(d)
        for d in raw_doc_types
        if (d or "").strip()
    }
    unknown_raw = [
        d
        for d in raw_doc_types
        if _map_raw_doc_type_to_scoring_alias(d) == "__unclassified__"
    ]
    if unknown_raw:
        for ur in unknown_raw:
            logger.warning(
                "[M12] bundle %s : doc_type inconnu %r → UNCLASSIFIED. "
                "Inclusion dans matrix_participants par défaut.",
                bundle_id,
                ur,
            )
    mapped = frozenset(a for a in aliases if a != "__unclassified__")
    if not mapped:
        return ScoringRole.SCORABLE
    has_offer = bool(
        mapped & frozenset({"offer_technical", "offer_financial", "offer_combined"})
    )
    vendor_ok = bool((vendor_name_raw or "").strip()) and (
        (vendor_name_raw or "").strip().upper() != "ABSENT"
    )
    if has_offer and vendor_ok:
        return ScoringRole.SCORABLE
    if has_offer and not vendor_ok:
        return ScoringRole.UNUSABLE
    solicitation_only = bool(mapped) and mapped <= frozenset({"rfq", "dao", "itt"})
    if not has_offer and solicitation_only:
        return ScoringRole.REFERENCE
    return classify_bundle_scoring_role(
        vendor_name_raw=vendor_name_raw,
        doc_types=mapped,
    )


def _load_bundle_documents_grouped(
    workspace_id: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    """``bundle_id`` → documents ; ``bundle_id`` → ``vendor_name_raw``."""
    with get_connection() as conn:
        bundles = db_fetchall(
            conn,
            """
            SELECT id::text AS bundle_id, vendor_name_raw
            FROM supplier_bundles
            WHERE workspace_id = CAST(:wid AS uuid)
            ORDER BY bundle_index NULLS LAST, id::text
            """,
            {"wid": workspace_id},
        )
        docs = db_fetchall(
            conn,
            """
            SELECT bd.id::text AS id, bd.doc_type::text AS doc_type, bd.raw_text,
                   bd.bundle_id::text AS bundle_id
            FROM bundle_documents bd
            WHERE bd.workspace_id = CAST(:wid AS uuid)
            ORDER BY bd.uploaded_at NULLS LAST
            """,
            {"wid": workspace_id},
        )
    vmap = {
        str(b["bundle_id"]): str(b.get("vendor_name_raw") or "") for b in bundles or []
    }
    groups: dict[str, list[dict[str, Any]]] = {bid: [] for bid in vmap}
    for r in docs or []:
        bid = str(r.get("bundle_id") or "")
        if bid not in groups:
            groups[bid] = []
        row = dict(r)
        row["vendor_name_raw"] = vmap.get(bid, "")
        groups[bid].append(row)
    return groups, vmap


_GATE_B_OFFER_TYPES = frozenset(
    {"offer_technical", "offer_financial", "offer_combined"}
)
_GATE_B_REFERENCE_DOC_TYPES = frozenset({"rfq", "dao", "tdr"})
# Document d'appel SCI (éviter les réponses fournisseur : « … RFQ-… » puis en-tête client).
_GATE_B_REFERENCE_TEXT = re.compile(
    r"(?is)save\s+the\s+children\s*[\s_]*\brfq\b",
)
_GATE_B_INTERNAL_TEXT = re.compile(
    r"(?is)(safeguarding\s+policy|politique\s+de\s+sauvegarde|"
    r"politique\s+de\s+d[ée]?veloppement\s+durable\s+pour\s+les\s+fournisseurs|"
    r"developpement\s+durable\s+pour\s+les\s+fournisseurs|"
    r"rapport\s+narratif.{0,120}[ée']?valuation|[ée]valuation\s+des\s+offres|"
    r"rapport\s+narratif\s+d[\u2019']?[ée]valuation)",
)


def _gate_b_raw_text_present(row: dict[str, Any]) -> bool:
    rt = row.get("raw_text")
    return rt is not None and str(rt).strip() != ""


def gate_b_classify_bundle_for_m14(
    rows: list[dict[str, Any]],
) -> tuple[str, str]:
    """Gate B — statut bundle pour inclusion M14 (texte réel des ``bundle_documents``).

    Retourne ``(statut, raison)`` avec ``statut`` ∈
    ``SCORABLE`` | ``REFERENCE`` | ``INTERNAL`` | ``UNUSABLE``.
    """
    if not rows:
        return "UNUSABLE", "no_bundle_documents"

    present = [r for r in rows if _gate_b_raw_text_present(r)]
    if not present:
        return "UNUSABLE", "all_documents_empty_or_null"

    for r in present:
        dt = str(r.get("doc_type") or "").strip().lower()
        if dt in _GATE_B_REFERENCE_DOC_TYPES:
            return "REFERENCE", f"source_rules_doc_type={dt}"

    full_snip = "\n".join(str(r.get("raw_text") or "")[:4000] for r in present)[:12000]
    if _GATE_B_REFERENCE_TEXT.search(full_snip):
        return "REFERENCE", "rfq_sci_text_pattern_in_offer_slot"

    offer_present = [
        r
        for r in present
        if str(r.get("doc_type") or "").lower() in _GATE_B_OFFER_TYPES
    ]
    offer_text = "\n".join(str(r.get("raw_text") or "")[:6000] for r in offer_present)[
        :12000
    ]

    if offer_present:
        if _GATE_B_INTERNAL_TEXT.search(offer_text):
            return "INTERNAL", "internal_or_evaluation_document_in_offer_slot"
        return "SCORABLE", "supplier_offer_with_present_raw_text"

    if _GATE_B_INTERNAL_TEXT.search(full_snip):
        return "INTERNAL", "internal_document_non_offer_slot"
    return "INTERNAL", "non_offer_documents_only_present"


def _build_one_minimal_m12_output(
    *,
    bundle_id: str,
    document_kind: DocumentKindParent,
    text: str,
    procurement_framework: ProcurementFramework,
    scoring: ScoringStructureDetected | None,
    classified_pass_entries: list[str],
) -> M12Output:
    """Un ``M12Output`` minimal pour un bundle (document_kind + corpus local)."""
    snippet = text[:500_000] if text else ""
    fw = procurement_framework
    fw_conf = 0.8
    rec = ProcedureRecognition(
        framework_detected=_tf(fw, fw_conf),
        procurement_family=_tf(ProcurementFamily.GOODS),
        procurement_family_sub=_tf(ProcurementFamilySub.GENERIC),
        document_kind=_tf(document_kind),
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
        recognition_source=_tf("pipeline_v5_per_bundle"),
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
        document_kind,
        fw,
        fw_conf,
        ProcurementFamily.GOODS,
        ProcurementFamilySub.GENERIC,
        [],
        scoring,
        snippet,
    )
    seq = ["pipeline_v5", f"bundle:{bundle_id}", *classified_pass_entries]
    meta = M12Meta(
        mode="bootstrap",
        confidence_ceiling=1.0,
        corpus_size_at_processing=len(snippet),
        processing_timestamp=datetime.now(UTC).isoformat(),
        pass_sequence=seq,
    )
    return M12Output(
        procedure_recognition=rec,
        document_validity=validity,
        document_conformity_signal=conformity,
        process_linking=linking,
        handoffs=hh,
        m12_meta=meta,
    )


def build_pipeline_v5_minimal_m12(
    *,
    workspace_id: str,
    corpus_text: str,
    procurement_framework: ProcurementFramework,
    scoring: ScoringStructureDetected | None = None,
) -> dict[str, M12Output]:
    """M12 minimal **par bundle** (D-001) — ``document_kind`` + corpus par fournisseur."""
    groups, _vmap = _load_bundle_documents_grouped(workspace_id)
    out: dict[str, M12Output] = {}
    if not groups:
        out["_workspace"] = _build_one_minimal_m12_output(
            bundle_id="_workspace",
            document_kind=DocumentKindParent.ITT,
            text=corpus_text,
            procurement_framework=procurement_framework,
            scoring=scoring,
            classified_pass_entries=["bundle:_workspace:no_supplier_bundles"],
        )
        return out
    for bundle_id, rows in groups.items():
        kinds: list[DocumentKindParent] = []
        classified: list[str] = []
        for row in rows:
            dt = str(row.get("doc_type") or "")
            dk = _map_doc_type_str_to_document_kind(dt)
            kinds.append(dk)
            did = str(row.get("id") or "")
            raw = row.get("raw_text")
            sts = "present" if raw is not None and str(raw).strip() else "empty"
            classified.append(f"doc|{did}|{dk.value}|{sts}")
        dominant = (
            _dominant_document_kind(kinds) if kinds else DocumentKindParent.UNKNOWN
        )
        bundle_corpus = "\n\n".join(
            str(r.get("raw_text") or "").strip() for r in rows if r.get("raw_text")
        )
        if not bundle_corpus.strip():
            bundle_corpus = corpus_text
        out[bundle_id] = _build_one_minimal_m12_output(
            bundle_id=bundle_id,
            document_kind=dominant,
            text=bundle_corpus,
            procurement_framework=procurement_framework,
            scoring=scoring,
            classified_pass_entries=classified,
        )
    return out


def _select_m12_output_for_m13(
    m12_by_bundle: dict[str, M12Output],
    *,
    procurement_framework: ProcurementFramework,
    corpus_text: str,
    scoring: ScoringStructureDetected | None,
) -> M12Output:
    """Choisit un M12 représentatif pour M13 (H1) quand la carte est multi-bundle."""
    if not m12_by_bundle:
        return _build_one_minimal_m12_output(
            bundle_id="_workspace",
            document_kind=DocumentKindParent.ITT,
            text=corpus_text,
            procurement_framework=procurement_framework,
            scoring=scoring,
            classified_pass_entries=["m13_pick:fallback_empty"],
        )
    priority = (
        DocumentKindParent.OFFER_COMBINED,
        DocumentKindParent.OFFER_TECHNICAL,
        DocumentKindParent.OFFER_FINANCIAL,
        DocumentKindParent.ITT,
        DocumentKindParent.DAO,
        DocumentKindParent.RFQ,
        DocumentKindParent.TDR,
        DocumentKindParent.UNKNOWN,
    )
    for kind in priority:
        for m12 in m12_by_bundle.values():
            if m12.procedure_recognition.document_kind.value == kind:
                return m12
    return next(iter(m12_by_bundle.values()))


def _ensure_h1_regulatory_skeleton_present(m12: M12Output) -> None:
    """M13 ne doit pas être le premier détecteur d'absence de H1 (P0-H1)."""
    if not m12.handoffs or not m12.handoffs.regulatory_profile_skeleton:
        raise PipelineError("pipeline_invalid:H1_regulatory_profile_skeleton_missing")


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

    in_matrix = {str(x["bundle_id"]) for x in matrix_participants}
    excluded_ids = {str(x["bundle_id"]) for x in excluded_from_matrix}
    for bid, role in bundle_roles.items():
        if bid in in_matrix or bid in excluded_ids:
            continue
        if role == ScoringRole.INTERNAL:
            excluded_from_matrix.append(
                {
                    "bundle_id": bid,
                    "supplier_name": (vendor_by_bundle.get(bid) or "").strip(),
                    "reason": "internal_reference_bundle",
                }
            )
            excluded_ids.add(bid)
        elif role == ScoringRole.REFERENCE:
            excluded_from_matrix.append(
                {
                    "bundle_id": bid,
                    "supplier_name": (vendor_by_bundle.get(bid) or "").strip(),
                    "reason": "reference_bundle",
                }
            )
            excluded_ids.add(bid)

    return matrix_participants, excluded_from_matrix


def _parse_pass_sequence_doc_entry(entry: str) -> tuple[str, str, bool] | None:
    """Parse une entrée ``m12_meta.pass_sequence`` de forme ``doc|id|kind|present|empty``."""
    if not entry.startswith("doc|"):
        return None
    parts = entry.split("|")
    if len(parts) < 4:
        return None
    doc_id = parts[1].strip()
    kind_raw = parts[2].strip()
    sts = parts[3].strip().lower()
    if not doc_id:
        return None
    raw_text_present = sts == "present"
    return (doc_id, kind_raw, raw_text_present)


def _pass_kind_value_to_document_kind_name(kind_raw: str) -> str:
    """``DocumentKindParent.value`` (pass_sequence) → nom enum (ex. ``OFFER_TECHNICAL``)."""
    try:
        return DocumentKindParent(kind_raw.strip().lower()).name
    except ValueError:
        return "UNKNOWN"


def _family_to_link_type(family: str) -> ProcessLinkingType:
    norm = _normalize_scoring_family(family)
    if norm == "technical":
        return "technical"
    if norm == "commercial":
        return "price"
    return "evidence"


def _normalize_scoring_family(fam: str) -> str:
    f = (fam or "").strip().lower()
    if f in ("technical", "technique"):
        return "technical"
    if f in ("commercial", "price", "prix", "financial"):
        return "commercial"
    if f in ("sustainability", "durabilité", "durabilite", "environment"):
        return "sustainability"
    return "other"


def _document_kind_matches_family(document_kind: str, family: str) -> bool:
    """``document_kind`` = nom enum (``OFFER_TECHNICAL``) ; ``family`` = famille DAO normalisée."""
    fam = _normalize_scoring_family(family)
    dk = (document_kind or "").strip().upper()
    if fam == "technical":
        return dk in ("OFFER_TECHNICAL", "OFFER_COMBINED")
    if fam == "commercial":
        return dk in ("OFFER_FINANCIAL", "OFFER_COMBINED")
    if fam == "sustainability":
        return dk in ("OFFER_COMBINED", "UNKNOWN")
    return dk in ("OFFER_COMBINED", "UNKNOWN")


def _require_scoring_criterion_ids_are_dao_uuids(
    scoring: ScoringStructureDetected,
) -> None:
    """Précondition Phase 2 — critères = UUID ``dao_criteria.id`` uniquement."""
    for c in scoring.criteria:
        cid = str(c.criteria_name or "").strip()
        if not cid or not DAO_CRITERION_ID_UUID_RE.match(cid):
            raise PipelineConfigurationError(
                "[PIPELINE] process_linking : structure de scoring avec criterion_id "
                f"non-UUID (dao_criteria.id uniquement) : {cid!r}"
            )


def _criterion_family_by_id_from_dao_rows(
    dao_criteria_rows: list[dict[str, Any]],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in dao_criteria_rows:
        rid = str(row.get("id") or "").strip()
        if rid:
            out[rid] = str(row.get("famille") or "general")
    return out


def _filter_compatible_docs_for_criterion(
    parsed_docs: list[tuple[str, str, bool]],
    *,
    family_raw: str,
) -> list[tuple[str, str, bool]]:
    """Docs dont le kind matche la famille ; UNKNOWN exclu si fallback non nécessaire."""
    fam_norm = _normalize_scoring_family(family_raw)
    compatible = [
        p for p in parsed_docs if _document_kind_matches_family(p[1], family_raw)
    ]
    if fam_norm in ("sustainability", "other"):
        has_non_unknown = any(p[1] != "UNKNOWN" for p in compatible)
        if has_non_unknown:
            compatible = [p for p in compatible if p[1] != "UNKNOWN"]
    return compatible


def _build_process_linking_entries(
    *,
    matrix_participants: list[dict[str, Any]],
    m12_by_bundle: dict[str, M12Output],
    scoring_detected: ScoringStructureDetected,
    dao_criteria_rows: list[dict[str, Any]],
) -> list[ProcessLinkingEntry]:
    """Construit ``process_linking_data`` depuis M12 en mémoire + participants matrice."""
    if not matrix_participants:
        return []

    _require_scoring_criterion_ids_are_dao_uuids(scoring_detected)

    fam_by_criterion = _criterion_family_by_id_from_dao_rows(dao_criteria_rows)
    entries: list[ProcessLinkingEntry] = []

    for mp in matrix_participants:
        bundle_id = str(mp.get("bundle_id") or "").strip()
        if not bundle_id:
            continue
        m12 = m12_by_bundle.get(bundle_id)
        parsed_docs: list[tuple[str, str, bool]] = []
        if m12 is not None:
            for raw in m12.m12_meta.pass_sequence or []:
                parsed = _parse_pass_sequence_doc_entry(str(raw))
                if parsed is None:
                    continue
                doc_id, kind_raw, present = parsed
                kind_name = _pass_kind_value_to_document_kind_name(kind_raw)
                parsed_docs.append((doc_id, kind_name, present))

        for crit in scoring_detected.criteria:
            criterion_id = str(crit.criteria_name or "").strip()
            family_raw = fam_by_criterion.get(criterion_id, "general")
            link_type = _family_to_link_type(family_raw)
            use_docs = _filter_compatible_docs_for_criterion(
                parsed_docs, family_raw=family_raw
            )
            if use_docs:
                for doc_id, document_kind, raw_ok in use_docs:
                    entries.append(
                        ProcessLinkingEntry(
                            bundle_id=bundle_id,
                            document_id=doc_id,
                            document_kind=document_kind,
                            criterion_id=criterion_id,
                            link_type=link_type,
                            raw_text_present=raw_ok,
                            source="m12_pass_sequence",
                        )
                    )
            else:
                entries.append(
                    ProcessLinkingEntry(
                        bundle_id=bundle_id,
                        document_id="",
                        document_kind="MISSING",
                        criterion_id=criterion_id,
                        link_type="missing",
                        raw_text_present=False,
                        source="m12_pass_sequence",
                    )
                )

    return entries


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
    """Rôle scoring runtime par ``supplier_bundles.id`` (D-001 + CTO D-03)."""
    groups, vmap = _load_bundle_documents_grouped(workspace_id)
    out: dict[str, ScoringRole] = {}
    for bid, rows in groups.items():
        dtypes = frozenset(
            str(r.get("doc_type") or "") for r in rows if r.get("doc_type")
        )
        vendor = vmap.get(bid) or (rows[0].get("vendor_name_raw") if rows else "") or ""
        out[bid] = _bundle_scoring_role_for_pipeline(bid, str(vendor), dtypes)
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
    dao_criteria_rows: list[dict[str, Any]] = []

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

            dao_criteria_rows = db_fetchall(
                conn,
                """
                SELECT id::text AS id, critere_nom,
                       COALESCE(ponderation, 0)::float AS ponderation,
                       COALESCE(is_eliminatory, false) AS is_eliminatory,
                       COALESCE(NULLIF(trim(categorie::text), ''), 'general') AS famille,
                       created_at
                FROM dao_criteria
                WHERE workspace_id = CAST(:wid AS uuid)
                ORDER BY categorie NULLS LAST, ponderation DESC NULLS LAST, id::text
                """,
                {"wid": workspace_id},
            )
            _require_dao_criteria_for_pipeline(workspace_id, dao_criteria_rows)

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
    except PipelineConfigurationError:
        raise
    except Exception as exc:
        out.error = str(exc)[:500]
        out.stopped_at = "exception"
        out.duration_seconds = time.perf_counter() - t0
        logger.exception("[PIPELINE-V5] fatal: %s", exc)
        return out

    from src.procurement.merged_criteria import build_merged_criteria_result

    mc_res = build_merged_criteria_result(dao_criteria_rows)
    ser = mc_res.to_serializable()
    out.merged_criteria = ser.get("merged", [])
    out.merged_criteria_warnings = ser.get("warnings", [])

    scoring_detected = scoring_structure_detected_from_dao_criteria_rows(
        dao_criteria_rows
    )
    m14_scoring_h2 = m14_h2_scoring_structure_dict_from_dao_criteria_rows(
        dao_criteria_rows
    )
    m12_by_bundle = build_pipeline_v5_minimal_m12(
        workspace_id=workspace_id,
        corpus_text=corpus_text,
        procurement_framework=fw_value,
        scoring=scoring_detected,
    )
    out.step_2_m12_reconstructed = True

    m12_for_m13 = _select_m12_output_for_m13(
        m12_by_bundle,
        procurement_framework=fw_value,
        corpus_text=corpus_text,
        scoring=scoring_detected,
    )

    _ensure_h1_regulatory_skeleton_present(m12_for_m13)

    doc_id = f"pipeline_v5:{workspace_id}"
    engine_m13 = RegulatoryComplianceEngine(
        repository=M13RegulatoryProfileRepository(),
    )
    try:
        m13_out = engine_m13.process_m12(
            case_id=case_id, document_id=doc_id, m12=m12_for_m13
        )
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
    doc_groups, _vendor_map = _load_bundle_documents_grouped(workspace_id)
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
    gate_b_status_map: dict[str, str] = {}
    for r in offers_rows:
        bid = str(r.get("bundle_id") or "")
        if bundle_roles.get(bid) != ScoringRole.SCORABLE:
            continue
        gstatus, greason = gate_b_classify_bundle_for_m14(doc_groups.get(bid) or [])
        gate_b_status_map[bid] = gstatus
        if gstatus != "SCORABLE":
            vendor_raw = _vendor_map.get(bid) or (
                (doc_groups.get(bid) or [{}])[0].get("vendor_name_raw") or ""
            )
            out.gate_b_exclusions.append(
                {
                    "bundle_id": bid,
                    "vendor_name_raw": vendor_raw,
                    "status": gstatus,
                    "reason": greason,
                }
            )
            logger.info(
                "[PIPELINE-V5] Gate B exclude bundle_id=%s vendor=%r status=%s reason=%s",
                bid,
                vendor_raw,
                gstatus,
                greason,
            )
            continue
        offers.append(
            {
                "document_id": r["bundle_id"],
                "supplier_name": r.get("supplier_name"),
                "process_role": "responds_to_bid",
            }
        )
    out.gate_b_m14_bundle_count = len(offers)
    out.bundle_status_by_bundle_id = gate_b_status_map
    offers_pre_p3 = list(offers)
    vendor_map = _vendor_name_by_bundle(workspace_id)
    offers, gate_out = run_p3_1b_eligibility_gate_phase(
        workspace_id,
        case_id,
        offers,
        doc_groups,
        gate_b_status_map,
        vendor_map,
    )
    out.eligible_vendor_ids = list(gate_out.eligible_vendor_ids)
    out.excluded_vendor_ids = list(gate_out.excluded_vendor_ids)
    out.pending_vendor_ids = list(gate_out.pending_vendor_ids)
    out.eligibility_verdicts_summary = eligibility_verdicts_summary_from_gate_output(
        gate_out
    )
    out.offers_submitted_to_m14 = [str(o["document_id"]) for o in offers]

    # P3.1B — restreindre bundle_roles pour build_matrix_participants_and_excluded.
    # Les bundles FAIL (excluded_vendor_ids) et PENDING (pending_vendor_ids) sont
    # marqués UNUSABLE : ils ne tombent plus dans la branche "SCORABLE absent de M14"
    # (→ not_in_m14_offer_list). merge_p3_eligibility_gate_failures_into_excluded les
    # ajoute ensuite avec reason="eligibility_fail". Les PENDING n'apparaissent dans
    # aucun des deux (ils sont tracés via out.pending_vendor_ids — R3/R7).
    _p3_non_scorable = set(gate_out.excluded_vendor_ids) | set(
        gate_out.pending_vendor_ids
    )
    bundle_roles_for_matrix: dict[str, ScoringRole] = {
        bid: (ScoringRole.UNUSABLE if bid in _p3_non_scorable else role)
        for bid, role in bundle_roles.items()
    }

    _ensure_m14_scoring_structure_for_scorable_offers(offers_pre_p3, m14_scoring_h2)

    h2: dict[str, Any] = {}
    if m12_for_m13.handoffs.atomic_capability_skeleton is not None:
        h2 = m12_for_m13.handoffs.atomic_capability_skeleton.model_dump(mode="json")
    # D-003 : la grille de score M14 vient toujours de dao_criteria (pas M13).
    h2["scoring_structure"] = m14_scoring_h2
    h3 = (
        m12_for_m13.handoffs.market_context_signal.model_dump(mode="json")
        if m12_for_m13.handoffs.market_context_signal
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
    m14_final_report: EvaluationReport | None = None
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
        if offers_pre_p3:
            raise PipelineError(
                "pipeline_blocked:p3_1b_zero_eligible_after_gate — "
                "Des bundles Gate B SCORABLE ont été identifiés mais aucun fournisseur "
                "n’a passé l’EligibilityGate P3.1 (tous exclus ou aucun éligible)."
            )
        out.error = "no_scorable_offers_for_m14"
        out.stopped_at = "precheck_m14_offers"
        out.duration_seconds = time.perf_counter() - t0
        return out

    if not skip_m14:
        repo_m14 = M14EvaluationRepository()
        engine_m14 = EvaluationEngine(repository=repo_m14)
        try:
            report_matrix = EvaluationEngine(repository=None).evaluate(inp)
            mp_list, ex_list = build_matrix_participants_and_excluded(
                report_matrix,
                bundle_roles=bundle_roles_for_matrix,
                vendor_by_bundle=vendor_map,
                extract_failed_bundles=extract_failed_bundles,
            )
            linking_entries = _build_process_linking_entries(
                matrix_participants=mp_list,
                m12_by_bundle=m12_by_bundle,
                scoring_detected=scoring_detected,
                dao_criteria_rows=dao_criteria_rows,
            )
            logger.info(
                "[PIPELINE] process_linking_data: %s entries for %s bundles",
                len(linking_entries),
                len(mp_list),
            )
            if linking_entries:
                logger.debug(
                    "[PIPELINE] process_linking_data preview: %s",
                    [e.model_dump() for e in linking_entries[:2]],
                )
            inp_with_linking = inp.model_copy(
                update={
                    "process_linking_data": [e.model_dump() for e in linking_entries],
                }
            )
            # P3.1B — ``offers`` / ``inp`` sont post-EligibilityGate ; M14 ne score que l’éligible.
            report = engine_m14.evaluate(inp_with_linking)
            m14_final_report = report
            payload = report.model_dump(mode="json")
            if out.procedure_resolution_status:
                payload["procedure_resolution_status"] = out.procedure_resolution_status
            mp_list, ex_list = build_matrix_participants_and_excluded(
                report,
                bundle_roles=bundle_roles_for_matrix,
                vendor_by_bundle=vendor_map,
                extract_failed_bundles=extract_failed_bundles,
            )
            merge_p3_eligibility_gate_failures_into_excluded(
                ex_list, gate_out, vendor_map
            )
            # Phase 1 Gate C traceability — persist matrix_participants and excluded_from_matrix
            out.matrix_participants = mp_list
            out.excluded_from_matrix = ex_list
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

    # Phase 1 Gate B/C guards — prevent bridge call with invalid state (CTO D-06 mandat 2026-04-16)
    if out.matrix_participants is None:
        raise PipelineError(
            "pipeline_invalid:matrix_participants_missing — "
            "build_matrix_participants_and_excluded returned None, Gate B/C did not produce a valid participant list"
        )
    if len(out.matrix_participants) == 0:
        raise PipelineError(
            "pipeline_blocked:no_eligible_matrix_participants — "
            "All bundles failed Gate B or Gate C, no eligible supplier to score in this dossier"
        )

    try:
        bridge = populate_assessments_from_m14(
            workspace_id,
            strict_matrix_participants=True,
            strict_uuid=True,
        )
        out.step_5_assessments_created = bridge.created + bridge.updated
    except BridgePipelineError as bridge_err:
        # D-004B — m14_bridge.PipelineError (alias: conflit avec PipelineError
        # local pipeline_v5, L79).
        logger.exception("bridge_pipeline_error: %s", bridge_err)
        raise
    except Exception as exc:
        logger.exception("[PIPELINE-V5] bridge M14→M16: %s", exc)
        out.error = f"bridge_failed:{exc}"[:500]
        out.stopped_at = "step_bridge"
        out.duration_seconds = time.perf_counter() - t0
        return out

    if m14_final_report is None:
        raise PipelineError(
            "pipeline_invalid:m14_report_missing_for_matrix_projection — "
            "Évaluation M14 absente après bridge ; projection matrice impossible."
        )
    tech_cfg = _technical_threshold_config_for_workspace(workspace_id)
    rows, summary, _ = build_matrix_projection_for_pipeline(
        workspace_id=workspace_id,
        gate_output=gate_out,
        report=m14_final_report,
        dao_criteria_rows=dao_criteria_rows,
        technical_threshold_config=tech_cfg,
        pipeline_run_id=None,
    )
    out.matrix_rows = rows
    out.matrix_summary = summary

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
