"""
P3.1 — Modèles dataclass pour l’EligibilityGate (pré-M14, hors pipeline).

Source normative : mandat P3.1 (dépôt / joint CTO). Pas de Pydantic ici :
structures pures consommées par ``eligibility_gate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EssentialCriterion:
    criterion_id: str
    question_number: str
    label: str
    criterion_type: str
    is_parent: bool
    parent_id: str | None
    evidence_expected: list[str]
    auto_checkable: bool
    verification_source: str
    gate_severity: str


@dataclass
class GateDecisionTrace:
    trace_id: str
    criterion_id: str
    vendor_id: str
    inputs_used: list[str]
    matched_signals: list[str]
    missing_signals: list[str]
    contradictions: list[str]
    decision_rule: str
    decision_result: str
    confidence: float | None


@dataclass
class EssentialCriterionResult:
    criterion_id: str
    vendor_id: str
    result_internal: str
    result_display: str
    proof_level: str
    evidence_found: list[str]
    evidence_label: str | None
    detection_method: str
    confidence: float | None
    recommended_action: str
    decision_trace_id: str | None
    fail_reason: str | None
    fail_type: str | None
    committee_override: bool
    override_user_id: str | None
    override_at: datetime | None
    override_justification: str | None
    locked: bool


@dataclass
class EligibilityVerdict:
    vendor_id: str
    eligible: bool
    gate_result: str
    failing_criteria: list[str]
    pending_criteria: list[str]
    dominant_cause: str | None
    auto_verified_count: int
    human_required_count: int
    total_criteria_count: int
    verification_coverage_ratio: float
    blocking_verified_ratio: float
    documentary_strength: str
    priority_score: int
    priority_reasons: list[str]
    locked: bool


@dataclass
class EligibilityReviewPriority:
    vendor_id: str
    vendor_name: str
    priority_score: int
    priority_tier: str
    reasons: list[str]


@dataclass
class GateOutput:
    workspace_id: str
    lot_id: str
    evaluated_at: datetime
    eligible_vendor_ids: list[str]
    excluded_vendor_ids: list[str]
    pending_vendor_ids: list[str]
    verdicts: dict[str, EligibilityVerdict]
    review_queue: list[EligibilityReviewPriority]
    total_submitted: int
    total_eligible: int
    total_excluded: int
    total_pending: int
    total_not_submitted: int


@dataclass
class VendorGateInput:
    """Entrée normalisée pour un fournisseur (hors DAO direct ; consommée par le gate)."""

    vendor_id: str
    vendor_name: str = ""
    bundle_gate_b_status: str | None = None
    has_exploitable_documents: bool = True
    is_important_vendor: bool = False
    signal_hits: dict[str, list[str]] = field(default_factory=dict)
    declared_without_proof_by_criterion: dict[str, bool] = field(default_factory=dict)
    vendor_declaration_acceptance: dict[str, bool] = field(default_factory=dict)
    committee_overrides: dict[str, tuple[str, str, datetime]] = field(
        default_factory=dict
    )


@dataclass
class VendorEligibilityDetail:
    """Résultat détaillé par fournisseur (critères + traces)."""

    vendor_id: str
    criterion_results: dict[str, EssentialCriterionResult]
    traces_by_id: dict[str, GateDecisionTrace]
    q5_aggregate_internal: str | None
    q5_aggregate_display: str | None
