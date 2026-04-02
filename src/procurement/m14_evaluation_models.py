"""
M14 — Evaluation Engine models (Pydantic, extra=forbid).

ADR-M14-001. Confiance exposée : {0.6, 0.8, 1.0} via M14Confidence.
RÈGLE-09 : winner / rank / recommendation / best_offer = INTERDITS.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

M14Confidence = Literal[0.6, 0.8, 1.0]


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

    RÈGLE-09 : ne contient PAS de winner / rank / recommendation / best_offer.
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
