"""
M13 V5 — modèles Pydantic (R1–R4, RH1, RH2).

extra=forbid (E-49). Confiance exposée : {0.6, 0.8, 1.0} via m13_discretize_confidence.
"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.procurement.compliance_models import (
    ComplianceVerdict,
    EliminatoryGateCheck,
    RegulatoryComplianceReport,
)
from src.procurement.document_ontology import ProcurementFamily, ProcurementFramework
from src.procurement.m13_confidence import M13Confidence


@unique
class RegulatoryProcedureType(StrEnum):
    OPEN_NATIONAL = "open_national"
    OPEN_INTERNATIONAL = "open_international"
    RESTRICTED = "restricted"
    SIMPLIFIED = "simplified"
    DIRECT_PURCHASE = "direct_purchase"
    REQUEST_FOR_QUOTATION = "request_for_quotation"
    FRAMEWORK_AGREEMENT = "framework_agreement"
    SOLE_SOURCE = "sole_source"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


class NormativeReference(BaseModel):
    framework: str
    article: str | None = None
    section: str | None = None
    description: str = ""
    url: str | None = None

    model_config = ConfigDict(extra="forbid")


class ThresholdTier(BaseModel):
    tier_name: str
    min_value: float
    max_value: float | None = None
    currency: str
    procedure_required: str
    source: NormativeReference

    model_config = ConfigDict(extra="forbid")


class RegulatoryRegime(BaseModel):
    framework: ProcurementFramework
    procurement_family: ProcurementFamily
    estimated_value: float | None = None
    currency: str | None = None
    threshold_tier: ThresholdTier
    procedure_type: RegulatoryProcedureType
    is_mixed_framework: bool = False
    mixed_resolution_strategy: str | None = None
    normative_references: list[NormativeReference] = Field(default_factory=list)
    confidence: M13Confidence = 0.6
    evidence: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RequiredDocument(BaseModel):
    document_name: str
    admin_subtype: str | None = None
    is_mandatory: bool = True
    is_eliminatory: bool = False
    applicable_stages: list[str] = Field(default_factory=list)
    normative_reference: NormativeReference = Field(
        default_factory=lambda: NormativeReference(framework="")
    )
    validity_rule_ref: str | None = None
    notes: str = ""

    model_config = ConfigDict(extra="forbid")


class RequiredDocumentSet(BaseModel):
    buyer_documents: list[RequiredDocument] = Field(default_factory=list)
    supplier_documents: list[RequiredDocument] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class TimelineRequirements(BaseModel):
    publication_delay_days: int | None = None
    submission_period_days: int | None = None
    bid_validity_period_days: int | None = None
    evaluation_max_days: int | None = None
    standstill_period_days: int | None = None
    contract_signature_max_days: int | None = None
    humanitarian_override: bool = False
    humanitarian_reduction_pct: float | None = None
    normative_references: list[NormativeReference] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ControlOrgan(BaseModel):
    organ_name: str
    organ_role: Literal[
        "opening_committee",
        "evaluation_committee",
        "approval_authority",
        "oversight_body",
        "procurement_unit",
        "budget_authority",
        "technical_committee",
        "other",
    ]
    required_for_procedure: list[str] = Field(default_factory=list)
    quorum_rule: str | None = None
    composition_rule: str | None = None
    normative_reference: NormativeReference = Field(
        default_factory=lambda: NormativeReference(framework="")
    )

    model_config = ConfigDict(extra="forbid")


class EvaluationRequirements(BaseModel):
    evaluation_method: Literal[
        "lowest_price",
        "mieux_disant",
        "quality_cost_based",
        "fixed_budget",
        "consultant_qualification",
        "unknown",
    ]
    technical_weight: float | None = None
    financial_weight: float | None = None
    sustainability_weight: float | None = None
    technical_threshold: float | None = None
    scoring_criteria_from_m12: list[Any] | None = None
    normative_reference: NormativeReference = Field(
        default_factory=lambda: NormativeReference(framework="")
    )

    model_config = ConfigDict(extra="forbid")


class GuaranteeRequirements(BaseModel):
    bid_guarantee_required: bool = False
    bid_guarantee_pct: float | None = None
    bid_guarantee_fixed: float | None = None
    performance_guarantee_required: bool = False
    performance_guarantee_pct: float | None = None
    retention_guarantee_required: bool = False
    retention_guarantee_pct: float | None = None
    normative_references: list[NormativeReference] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ApprovalStep(BaseModel):
    step_name: str
    authority: str
    threshold_applies: bool = False
    is_mandatory: bool = True
    normative_reference: NormativeReference = Field(
        default_factory=lambda: NormativeReference(framework="")
    )

    model_config = ConfigDict(extra="forbid")


class MinimumBidsRequirement(BaseModel):
    minimum_bids: int = 1
    consequence_if_below: Literal[
        "cancel_and_relaunch",
        "justify_and_proceed",
        "automatic_sole_source",
        "not_specified",
    ] = "not_specified"
    normative_reference: NormativeReference = Field(
        default_factory=lambda: NormativeReference(framework="")
    )

    model_config = ConfigDict(extra="forbid")


class RegulatoryDocumentValidityRule(BaseModel):
    framework: str
    admin_subtype: str
    document_name: str
    validity_period_months: int | None = None
    validity_period_days: int | None = None
    no_expiry: bool = False
    validity_from: Literal[
        "issue_date", "fiscal_year_end", "calendar_year_end", "custom"
    ] = "issue_date"
    validity_note: str = ""
    expiry_consequence: Literal["rejection", "regularization", "warning"]
    grace_period_days: int = 0
    renewal_instruction: str = ""
    renewal_typical_duration_days: int | None = None
    normative_reference: NormativeReference = Field(
        default_factory=lambda: NormativeReference(framework="")
    )

    model_config = ConfigDict(extra="forbid")


class ProcedureRequirements(BaseModel):
    regime: RegulatoryRegime
    required_documents: RequiredDocumentSet
    timeline_requirements: TimelineRequirements
    control_organs: list[ControlOrgan] = Field(default_factory=list)
    evaluation_requirements: EvaluationRequirements
    guarantee_requirements: GuaranteeRequirements
    approval_chain: list[ApprovalStep] = Field(default_factory=list)
    minimum_bids: MinimumBidsRequirement
    document_validity_rules: list[RegulatoryDocumentValidityRule] = Field(
        default_factory=list
    )

    model_config = ConfigDict(extra="forbid")


class ComplianceGateSource(StrEnum):
    DOCUMENT_DETECTED = "document_detected"
    REGULATORY_REQUIRED = "regulatory_required"
    BOTH = "both"


class ReconciliationStatus(StrEnum):
    MATCHED = "matched"
    DOCUMENT_ONLY = "document_only"
    REGULATION_ONLY = "regulation_only"
    CONFLICT = "conflict"


class VerificationMethod(StrEnum):
    DOCUMENT_PRESENCE = "document_presence"
    DOCUMENT_VALIDITY = "document_validity"
    VALUE_CHECK = "value_check"
    DATE_CHECK = "date_check"
    THRESHOLD_CHECK = "threshold_check"
    COMPOSITE_CHECK = "composite_check"
    EXPIRY_CHECK = "expiry_check"
    MANUAL_REVIEW = "manual_review"


class ComplianceGateAssembled(BaseModel):
    gate_id: str
    gate_name: str
    gate_category: Literal[
        "eligibility",
        "administrative",
        "technical_minimum",
        "financial_minimum",
        "qualification",
        "document_validity",
    ]
    source: ComplianceGateSource
    reconciliation: ReconciliationStatus
    is_eliminatory: bool
    is_regularizable: bool = False
    verification_method: VerificationMethod
    expected_admin_subtype: str | None = None
    expected_value: str | None = None
    expected_threshold: str | None = None
    normative_reference: NormativeReference | None = None
    confidence: M13Confidence = 0.6
    evidence: list[str] = Field(default_factory=list)
    conflict_requires_human_resolution: bool = False
    conflict_description: str | None = None

    model_config = ConfigDict(extra="forbid")


class GatesSummary(BaseModel):
    total_gates: int = 0
    eliminatory_gates: int = 0
    regularizable_gates: int = 0
    matched_gates: int = 0
    regulation_only_gates: int = 0
    document_only_gates: int = 0
    conflict_gates: int = 0
    document_validity_gates: int = 0

    model_config = ConfigDict(extra="forbid")


class DerogationType(StrEnum):
    HUMANITARIAN_EMERGENCY = "humanitarian_emergency"
    SOLE_SOURCE_JUSTIFIED = "sole_source_justified"
    SECURITY_CONTEXT = "security_context"
    FRAMEWORK_AGREEMENT_CALL = "framework_agreement_call"
    BELOW_THRESHOLD_SIMPLIFIED = "below_threshold_simplified"
    OTHER = "other"


class DerogationAssessment(BaseModel):
    derogation_type: DerogationType
    is_applicable: bool
    approval_required: str = ""
    approval_authority: str = ""
    parameters_modified: dict[str, Any] = Field(default_factory=dict)
    normative_reference: NormativeReference = Field(
        default_factory=lambda: NormativeReference(framework="")
    )
    evidence: list[str] = Field(default_factory=list)
    confidence: M13Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


@unique
class ProcurementPrinciple(StrEnum):
    COMPETITION = "competition"
    TRANSPARENCY = "transparency"
    FAIRNESS = "fairness"
    ECONOMY = "economy"
    EFFICIENCY = "efficiency"
    INTEGRITY = "integrity"
    FIT_FOR_PURPOSE = "fit_for_purpose"
    VALUE_FOR_MONEY = "value_for_money"
    SUSTAINABILITY = "sustainability"


class ImplementingRule(BaseModel):
    rule_name: str
    description: str
    contribution: Literal["strong", "medium", "weak"]
    active_in_this_case: bool = True
    condition: str | None = None

    model_config = ConfigDict(extra="forbid")


class DurabilityAssessment(BaseModel):
    applicable: bool = False
    applicable_families: list[str] = Field(default_factory=lambda: ["works", "goods"])
    durability_rules_active: list[ImplementingRule] = Field(default_factory=list)
    durability_coverage: Literal["full", "partial", "minimal", "none"] = "none"
    durability_gap: str | None = None
    durability_note: str = ""

    model_config = ConfigDict(extra="forbid")


class PrincipleAssessment(BaseModel):
    principle: ProcurementPrinciple
    status: Literal[
        "fully_addressed",
        "partially_addressed",
        "minimally_addressed",
        "not_addressed",
        "not_assessable",
    ]
    implementing_rules: list[ImplementingRule] = Field(default_factory=list)
    gap_description: str | None = None
    normative_references: list[NormativeReference] = Field(default_factory=list)
    durability_assessment: DurabilityAssessment | None = None

    model_config = ConfigDict(extra="forbid")


class PrinciplesComplianceMap(BaseModel):
    principles: list[PrincipleAssessment]
    executive_summary_lines: list[str] = Field(default_factory=list)
    sustainability_highlight: str = ""
    durability_highlight: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("principles")
    @classmethod
    def _nine_principles(
        cls, v: list[PrincipleAssessment]
    ) -> list[PrincipleAssessment]:
        if len(v) != 9:
            raise ValueError("PrinciplesComplianceMap requires exactly 9 principles")
        names = {p.principle for p in v}
        if ProcurementPrinciple.SUSTAINABILITY not in names:
            raise ValueError("SUSTAINABILITY principle required")
        return v


class OCDSPhaseCoverage(BaseModel):
    phase: Literal["planning", "tender", "award", "contract", "implementation"]
    covered: bool = False
    covered_by: str | None = None
    applicable_release_tags: list[str] = Field(default_factory=list)
    notes: str = ""

    model_config = ConfigDict(extra="forbid")


class OCDSProcessCoverage(BaseModel):
    phases: list[OCDSPhaseCoverage] = Field(default_factory=list)
    total_phases: int = 5
    covered_phases: int = 0
    coverage_ratio: float = 0.0

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def build_default(cls) -> OCDSProcessCoverage:
        phases = [
            OCDSPhaseCoverage(
                phase="planning",
                covered=True,
                covered_by="M12+M13",
                applicable_release_tags=["planning"],
                notes="Need definition, TDR, market survey",
            ),
            OCDSPhaseCoverage(
                phase="tender",
                covered=True,
                covered_by="M12+M13+M14",
                applicable_release_tags=["tender", "tenderAmendment", "tenderUpdate"],
                notes="Solicitation, submission, evaluation",
            ),
            OCDSPhaseCoverage(
                phase="award",
                covered=True,
                covered_by="M14",
                applicable_release_tags=["award", "awardUpdate"],
                notes="Award decision, notification",
            ),
            OCDSPhaseCoverage(
                phase="contract",
                covered=False,
                covered_by=None,
                applicable_release_tags=["contract", "contractAmendment"],
                notes="Reserved M17",
            ),
            OCDSPhaseCoverage(
                phase="implementation",
                covered=False,
                covered_by=None,
                applicable_release_tags=["implementation"],
                notes="Reserved M18",
            ),
        ]
        covered = sum(1 for p in phases if p.covered)
        return cls(
            phases=phases,
            covered_phases=covered,
            coverage_ratio=covered / 5.0,
        )


class M13Meta(BaseModel):
    m13_version: str = "5.0.0"
    mode: Literal["bootstrap", "production"] = "bootstrap"
    mode_transition_eligible: bool = False
    benchmark_status_summary: str | None = None
    processing_timestamp: str = ""
    framework_resolved: str = ""
    confidence_floor: M13Confidence = 0.6
    review_required: bool = False

    model_config = ConfigDict(extra="forbid")


class M13RegulatoryComplianceReport(BaseModel):
    regime: RegulatoryRegime
    procedure_requirements: ProcedureRequirements
    compliance_gates: list[ComplianceGateAssembled] = Field(default_factory=list)
    gates_summary: GatesSummary = Field(default_factory=GatesSummary)
    applicable_derogations: list[DerogationAssessment] = Field(default_factory=list)
    principles_compliance_map: PrinciplesComplianceMap
    ocds_process_coverage: OCDSProcessCoverage
    m13_meta: M13Meta

    model_config = ConfigDict(extra="forbid")


class ComplianceCheckItem(BaseModel):
    check_id: str
    check_name: str
    check_scope: Literal["per_offer", "case_level"]
    verification_method: VerificationMethod
    is_eliminatory: bool = False
    is_regularizable: bool = False
    expected_value: str | None = None
    expected_threshold: str | None = None
    normative_reference: NormativeReference | None = None
    expiry_rule: RegulatoryDocumentValidityRule | None = None
    m14_execution_hint: str = ""

    model_config = ConfigDict(extra="forbid")


class ComplianceChecklist(BaseModel):
    case_id: str
    framework: str
    procedure_type: str
    per_offer_checks: list[ComplianceCheckItem] = Field(default_factory=list)
    case_level_checks: list[ComplianceCheckItem] = Field(default_factory=list)
    total_checks: int = 0
    eliminatory_checks: int = 0
    regularizable_checks: int = 0
    expiry_checks: int = 0
    m14_instruction: str = (
        "Execute each check in order. For per_offer_checks, execute "
        "against each submitted offer. For case_level_checks, execute "
        "once for the entire case. Expiry checks require document date "
        "extraction. If date not extractable, flag as INDETERMINATE "
        "not FAILED. Grace periods are defined per document type."
    )

    model_config = ConfigDict(extra="forbid")


class EvaluationBlueprint(BaseModel):
    evaluation_method: Literal[
        "lowest_price",
        "mieux_disant",
        "quality_cost_based",
        "fixed_budget",
        "consultant_qualification",
        "unknown",
    ]
    technical_weight: float | None = None
    financial_weight: float | None = None
    sustainability_weight: float | None = None
    minimum_bids: int = 1
    ocds_process_coverage: OCDSProcessCoverage
    principles_summary: list[str] = Field(default_factory=list)
    document_validity_rules: list[RegulatoryDocumentValidityRule] = Field(
        default_factory=list
    )
    procedure_requirements_ref: str = ""
    blueprint_version: str = "5.0.0"
    m14_instruction: str = (
        "This blueprint provides evaluation FRAMING only. "
        "For execution details (scoring grids, guarantee amounts, "
        "organ composition, timeline specifics, approval chains), "
        "M14 MUST read procedure_requirements at the ref above. "
        "Do NOT treat this blueprint as a self-sufficient evaluation spec."
    )

    model_config = ConfigDict(extra="forbid")


class M13Output(BaseModel):
    report: M13RegulatoryComplianceReport
    compliance_checklist: ComplianceChecklist
    evaluation_blueprint: EvaluationBlueprint

    model_config = ConfigDict(extra="forbid")


def legacy_compliance_report_from_m13(
    *,
    document_id: str,
    m13: M13RegulatoryComplianceReport,
) -> RegulatoryComplianceReport:
    """Dérive le rapport legacy (verdict + checks) depuis le rapport moteur V5."""
    fw = m13.regime.framework
    tier = m13.regime.threshold_tier.tier_name
    meta = m13.m13_meta
    gates = m13.compliance_gates

    eliminatory: list[EliminatoryGateCheck] = []
    for g in gates:
        if not g.is_eliminatory:
            continue
        status: Literal["present", "absent", "not_applicable"]
        if g.reconciliation == ReconciliationStatus.MATCHED:
            status = "present"
        elif g.reconciliation == ReconciliationStatus.REGULATION_ONLY:
            status = "absent"
        else:
            status = "not_applicable"
        eliminatory.append(
            EliminatoryGateCheck(
                gate_name=g.gate_name,
                status=status,
                evidence="; ".join(g.evidence)[:2000],
            )
        )

    verdict: ComplianceVerdict
    reasons: list[str] = []
    if meta.review_required or fw == ProcurementFramework.UNKNOWN:
        verdict = (
            ComplianceVerdict.NOT_ASSESSABLE
            if fw == ProcurementFramework.UNKNOWN
            else ComplianceVerdict.REVIEW_REQUIRED
        )
        if fw == ProcurementFramework.UNKNOWN:
            reasons.append("framework UNKNOWN — rules not fully applicable")
        if meta.review_required:
            reasons.append("m13_meta.review_required")
    elif any(x.status == "absent" for x in eliminatory):
        verdict = ComplianceVerdict.NON_COMPLIANT
    else:
        verdict = ComplianceVerdict.COMPLIANT

    sus = m13.procedure_requirements.evaluation_requirements.sustainability_weight
    sustainability_check = None
    if sus is not None:
        sustainability_check = sus >= 0.10

    return RegulatoryComplianceReport(
        document_id=document_id,
        framework_applied=fw,
        verdict=verdict,
        eliminatory_checks=eliminatory,
        threshold_tier=tier,
        sustainability_check=sustainability_check,
        review_reasons=reasons,
        produced_by="M13",
    )
