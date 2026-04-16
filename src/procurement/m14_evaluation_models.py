"""
M14 — Evaluation Engine models (Pydantic, extra=forbid).

ADR-M14-001. Confiance exposée : {0.6, 0.8, 1.0} via M14Confidence.
RÈGLE-09 : winner / rank / recommendation / offre_retenue = INTERDITS.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.procurement.procedure_models import (
    ScoringCriterionDetected,
    ScoringStructureDetected,
)

ProcessLinkingSource = Literal["m12_pass_sequence"]
ProcessLinkingType = Literal["evidence", "price", "technical", "missing"]

M14Confidence = Literal[0.6, 0.8, 1.0]

logger = logging.getLogger(__name__)

DAO_CRITERION_ID_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _ponderation_coherence_from_totals(
    total_w: float, *, has_criteria: bool
) -> Literal["OK", "INCOHERENT", "INCOMPLETE", "NOT_FOUND"]:
    """Cohérence des pondérations DAO (aligné extract_scoring_structure / revue Copilot)."""
    if not has_criteria:
        return "NOT_FOUND"
    if abs(total_w - 100.0) <= 0.01:
        return "OK"
    if total_w > 0.0:
        return "INCOMPLETE"
    return "INCOHERENT"


def scoring_structure_detected_from_dao_criteria_rows(
    rows: list[dict[str, Any]],
) -> ScoringStructureDetected:
    """Construit un ``ScoringStructureDetected`` M12 depuis les lignes ``dao_criteria`` DB."""
    criteria: list[ScoringCriterionDetected] = []
    total_w = 0.0
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if not rid or not DAO_CRITERION_ID_UUID_RE.match(rid):
            continue
        w = float(row.get("ponderation") or 0.0)
        total_w += w
        label = str(row.get("critere_nom") or "").strip()
        fam = str(row.get("famille") or "general")
        elim = row.get("is_eliminatory")
        ev_parts = [f"label={label}", f"famille={fam}"]
        if elim is not None:
            ev_parts.append(f"is_eliminatory={bool(elim)}")
        criteria.append(
            ScoringCriterionDetected(
                criteria_name=rid,
                weight_percent=w,
                confidence=1.0,
                evidence=", ".join(ev_parts),
            )
        )
    coherence = _ponderation_coherence_from_totals(total_w, has_criteria=bool(criteria))
    if coherence not in ("OK", "NOT_FOUND"):
        logger.warning(
            "[M14] dao_criteria ponderation sum=%s (attendu ~100.0) — %s",
            total_w,
            coherence,
        )
    return ScoringStructureDetected(
        criteria=criteria,
        total_weight=total_w,
        ponderation_coherence=coherence,
        confidence=1.0,
        evidence=[f"dao_criteria_rows={len(rows)}"],
    )


def m14_h2_scoring_structure_dict_from_dao_criteria_rows(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Grille D-003 pour ``h2_capability_skeleton['scoring_structure']`` (M14 / dao_criteria).

    Source unique : ``dao_criteria``. Chaque entrée expose à la fois les champs
    métier (criterion_id, libellé, famille, éliminatoire) et les clés attendues par
    ``EvaluationEngine._compute_technical_score`` (``criteria_name`` = UUID DAO,
    ``weight_percent``).
    """
    crits: list[dict[str, Any]] = []
    total_w = 0.0
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if not rid or not DAO_CRITERION_ID_UUID_RE.match(rid):
            continue
        w = float(row.get("ponderation") or 0.0)
        total_w += w
        label = str(row.get("critere_nom") or "").strip()
        fam = str(row.get("famille") or "general").strip().lower()
        elim = row.get("is_eliminatory")
        crits.append(
            {
                "criterion_id": rid,
                "criterion_name": label,
                "criteria_name": rid,
                "famille": fam,
                "weight_percent": w,
                "ponderation": w,
                "is_eliminatory": bool(elim) if elim is not None else False,
                "max_score": None,
                "awarded_score": None,
            }
        )
    coherence = _ponderation_coherence_from_totals(total_w, has_criteria=bool(crits))
    if coherence not in ("OK", "NOT_FOUND"):
        logger.warning(
            "[M14] dao_criteria ponderation sum=%s (attendu ~100.0) — %s",
            total_w,
            coherence,
        )
    return {
        "criteria": crits,
        "total_weight": total_w,
        "ponderation_coherence": coherence,
        "confidence": 1.0,
        "evidence": [f"dao_criteria_rows={len(rows)}"],
    }


class EligibilityCheckResult(BaseModel):
    """Résultat d'un check éliminatoire exécuté sur une offre."""

    check_id: str
    check_name: str
    result: Literal["PASS", "FAIL", "INDETERMINATE", "NOT_APPLICABLE"]
    is_eliminatory: bool = False
    evidence: list[str] = Field(default_factory=list)
    confidence: M14Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


class TechnicalCriterionScore(BaseModel):
    """Score d'un critère technique individuel."""

    criteria_name: str
    weight_percent: float | None = None
    max_score: float | None = None
    awarded_score: float | None = None
    justification: str = ""
    confidence: M14Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


class TechnicalScore(BaseModel):
    """Score technique agrégé pour une offre."""

    criteria_scores: list[TechnicalCriterionScore] = Field(default_factory=list)
    total_weighted_score: float | None = None
    technical_threshold: float | None = None
    passes_threshold: bool | None = None
    ponderation_coherence: Literal["OK", "INCOHERENT", "INCOMPLETE", "NOT_FOUND"] = (
        "NOT_FOUND"
    )
    confidence: M14Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


class PriceAnalysis(BaseModel):
    """Analyse prix pour une offre, avec référence mercuriale si disponible."""

    total_price_declared: float | None = None
    currency: str | None = None
    price_basis: Literal["HT", "TTC", "unknown"] | None = None
    currency_mismatch_alert: bool = False
    mercuriale_comparison_available: bool = False
    material_categories_checked: list[str] = Field(default_factory=list)
    price_anomaly_flags: list[str] = Field(default_factory=list)
    zone_for_reference: list[str] = Field(default_factory=list)
    confidence: M14Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


class CompletionAnalysis(BaseModel):
    """Analyse de complétude de l'offre par rapport au squelette H2."""

    expected_sections: list[str] = Field(default_factory=list)
    present_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    completeness_ratio: float = 0.0
    confidence: M14Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


class OfferEvaluation(BaseModel):
    """Évaluation complète d'une offre individuelle."""

    offer_document_id: str
    supplier_name: str | None = None
    process_role: str | None = None
    eligibility_results: list[EligibilityCheckResult] = Field(default_factory=list)
    is_eligible: bool | None = None
    completion_analysis: CompletionAnalysis | None = None
    technical_score: TechnicalScore | None = None
    price_analysis: PriceAnalysis | None = None
    compliance_results: list[EligibilityCheckResult] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    overall_confidence: M14Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


class EvaluationMeta(BaseModel):
    """Métadonnées du rapport d'évaluation M14."""

    m14_version: str = "1.0.0"
    mode: Literal["bootstrap", "production"] = "bootstrap"
    processing_timestamp: str = ""
    evaluation_method: str = "unknown"
    scoring_review_required: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class EvaluationReport(BaseModel):
    """Rapport d'évaluation comparative par dossier (case).

    RÈGLE-09 : ne contient PAS de winner / rank / recommendation / offre_retenue.
    """

    case_id: str
    evaluation_method: Literal[
        "lowest_price",
        "mieux_disant",
        "quality_cost_based",
        "fixed_budget",
        "consultant_qualification",
        "unknown",
    ]
    source_rules_document_id: str | None = None
    offer_evaluations: list[OfferEvaluation] = Field(default_factory=list)
    case_level_checks: list[EligibilityCheckResult] = Field(default_factory=list)
    total_offers_evaluated: int = 0
    eligible_offers_count: int = 0
    blueprint_ref: str | None = None
    m14_meta: EvaluationMeta = Field(default_factory=EvaluationMeta)

    model_config = ConfigDict(extra="forbid")


class ProcessLinkingEntry(BaseModel):
    """Lien documentaire minimal bundle → document → critère (Phase 2, transitoire)."""

    bundle_id: str
    document_id: str
    document_kind: str
    criterion_id: str
    link_type: ProcessLinkingType
    raw_text_present: bool
    source: ProcessLinkingSource = "m12_pass_sequence"

    model_config = ConfigDict(extra="forbid")


class M14EvaluationInput(BaseModel):
    """Entrée structurée pour le moteur M14."""

    case_id: str
    source_rules_document_id: str | None = None
    offers: list[dict[str, Any]] = Field(default_factory=list)
    h2_capability_skeleton: dict[str, Any] | None = None
    h3_market_context: dict[str, Any] | None = None
    rh1_compliance_checklist: dict[str, Any] | None = None
    rh2_evaluation_blueprint: dict[str, Any] | None = None
    process_linking_data: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Response models — typed API contract (GAP-3 / GAP-4 hardening)
# ---------------------------------------------------------------------------

EvaluationDocumentStatus = Literal["draft", "committee_review", "sealed", "exported"]


class M14StatusResponse(BaseModel):
    """GET /api/m14/status response shape."""

    module: str
    version: str

    model_config = ConfigDict(extra="forbid")


class EvaluationDocumentEnvelope(BaseModel):
    """Envelope for a persisted evaluation_documents row.

    ``scores_matrix`` is parsed back into ``EvaluationReport`` so
    clients receive a typed, self-documenting payload rather than
    opaque JSONB.
    """

    id: str
    case_id: str
    version: int
    scores_matrix: EvaluationReport
    justifications: dict[str, Any] = Field(default_factory=dict)
    status: EvaluationDocumentStatus = "draft"
    created_at: str

    model_config = ConfigDict(extra="forbid")
