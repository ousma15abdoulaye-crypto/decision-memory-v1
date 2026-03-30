"""
M12 V6 — Pydantic models for the Procurement Document & Process Recognizer.

All models use extra="forbid" (E-49).
TracedField is the universal tracing primitive: value + confidence + evidence.
Confidence internal to M12 is [0.0, 1.0]; discretized to {0.6, 0.8, 1.0} at export.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.procurement.document_ontology import (
    DocumentKindParent,
    LinkNature,
    ProcurementFamily,
    ProcurementFamilySub,
    ProcurementFramework,
)


def discretize_confidence(raw: float) -> float:
    """Map continuous confidence to the {0.6, 0.8, 1.0} grid at export boundary."""
    if raw >= 0.90:
        return 1.0
    if raw >= 0.70:
        return 0.8
    return 0.6


class TracedField(BaseModel):
    """
    Universal tracing primitive: value + confidence + evidence.

    Runtime type of `value` is validated by the consuming model context,
    not by TracedField itself (Pydantic v2 generic limitations).
    """

    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("confidence")
    @classmethod
    def _validate_confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence {v} out of [0.0, 1.0]")
        return v


class PartDetectionResult(BaseModel):
    part_name: str
    detection_level: Literal[
        "level_1_heading", "level_2_keyword", "level_3_llm", "not_detected"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class GateResult(BaseModel):
    gate_name: str
    gate_state: Literal["PASSED", "FAILED", "MISSING", "NOT_APPLICABLE", "UNKNOWN"]
    gate_value: Any | None = None
    gate_threshold: Any | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("gate_value", mode="before")
    @classmethod
    def _coerce_applicable_null(cls, v: Any, info: Any) -> Any:
        return v


class EligibilityGateExtracted(BaseModel):
    """Gate d'éligibilité extraite d'un document source_rules."""

    gate_name: str
    gate_type: Literal[
        "eligibility",
        "qualification",
        "eliminatory",
        "administrative",
        "technical_minimum",
        "financial_minimum",
    ]
    document_source_required: (
        Literal[
            "nif",
            "rccm",
            "rib",
            "quitus_fiscal",
            "cert_non_faillite",
            "id_representative",
            "sci_conditions",
            "sci_conditions_signed",
            "sanctions_cert",
            "sustainability_policy",
            "ariba_id",
            "licence",
            "attestation_visite",
            "caution_soumission",
            "other",
        ]
        | None
    ) = None
    threshold_value: str | None = None
    is_eliminatory: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = ""

    model_config = ConfigDict(extra="forbid")


class ScoringCriterionDetected(BaseModel):
    criteria_name: str
    weight_percent: float | None = None
    weight_points: float | None = None
    max_score: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = ""

    model_config = ConfigDict(extra="forbid")


class ScoringStructureDetected(BaseModel):
    criteria: list[ScoringCriterionDetected] = Field(default_factory=list)
    total_weight: float = 0.0
    ponderation_coherence: Literal["OK", "INCOHERENT", "INCOMPLETE", "NOT_FOUND"] = (
        "NOT_FOUND"
    )
    evaluation_method: (
        Literal[
            "lowest_price",
            "mieux_disant",
            "quality_cost_based",
            "fixed_budget",
            "consultant_qualification",
            "unknown",
        ]
        | None
    ) = None
    technical_threshold: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class LinkHint(BaseModel):
    target_document_id: str | None = None
    link_nature: LinkNature
    link_level: Literal[
        "EXACT_REFERENCE",
        "FUZZY_REFERENCE",
        "SUBJECT_TEMPORAL",
        "CONTEXTUAL",
        "UNRESOLVED",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class SupplierDetected(BaseModel):
    name_raw: str
    name_normalized: str | None = None
    legal_form: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = ""
    source_document_id: str | None = None

    model_config = ConfigDict(extra="forbid")


# ── BLOC 1: ProcedureRecognition (L1-L3) ──


class ProcedureRecognition(BaseModel):
    framework_detected: TracedField
    procurement_family: TracedField
    procurement_family_sub: TracedField

    document_kind: TracedField
    document_subtype: TracedField
    secondary_document_kinds: list[DocumentKindParent] = Field(default_factory=list)
    is_composite: TracedField

    document_layer: TracedField
    document_stage: TracedField

    procedure_type: TracedField
    procedure_reference_detected: TracedField

    issuing_entity_detected: TracedField
    project_name_detected: TracedField
    zone_scope_detected: TracedField

    submission_deadline_detected: TracedField
    submission_mode_detected: TracedField

    result_type_detected: TracedField

    estimated_value_detected: TracedField
    currency_detected: TracedField

    visit_required: TracedField
    sample_required: TracedField

    humanitarian_context: TracedField

    recognition_source: TracedField
    review_status: TracedField

    model_config = ConfigDict(extra="forbid")


# ── BLOC 2: DocumentValidity (L4-L5) ──


class DocumentValidity(BaseModel):
    document_validity_status: TracedField
    mandatory_detected_count: int = 0
    mandatory_total_count: int = 0
    mandatory_coverage: float = Field(ge=0.0, le=1.0, default=0.0)
    mandatory_parts_present: list[str] = Field(default_factory=list)
    mandatory_parts_missing: list[str] = Field(default_factory=list)
    mandatory_parts_detection_details: list[PartDetectionResult] = Field(
        default_factory=list
    )
    optional_parts_present: list[str] = Field(default_factory=list)
    not_applicable_parts: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ── BLOC 3: DocumentConformitySignal (L6) ──


class DocumentConformitySignal(BaseModel):
    offer_composition_hint: TracedField
    document_conformity_status: TracedField
    document_scope: TracedField

    gates: list[GateResult] = Field(default_factory=list)
    grounds: list[str] = Field(default_factory=list)

    eligibility_gates_extracted: list[EligibilityGateExtracted] = Field(
        default_factory=list
    )
    scoring_structure_extracted: ScoringStructureDetected | None = None

    model_config = ConfigDict(extra="forbid")


# ── BLOC 4: ProcessLinking (L7) ──


class ProcessLinking(BaseModel):
    process_role: TracedField
    linked_parent_hint: list[LinkHint] = Field(default_factory=list)
    linked_children_hint: list[LinkHint] = Field(default_factory=list)
    procedure_end_marker: TracedField

    suppliers_detected: list[SupplierDetected] = Field(default_factory=list)
    procedure_reference_chain: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ── BLOC 5: Handoffs ──


class RegulatoryProfileSkeleton(BaseModel):
    """Prepared by M12, completed by M13."""

    framework_detected: ProcurementFramework
    framework_confidence: float = Field(ge=0.0, le=1.0)

    sci_signals_detected: list[str] = Field(default_factory=list)
    sci_conditions_referenced: bool = False
    sci_sustainability_pct_detected: float | None = None
    sci_iapg_referenced: bool = False
    sci_sanctions_clause_present: bool = False

    dgmp_signals_detected: list[str] = Field(default_factory=list)
    dgmp_procedure_type_detected: str | None = None
    dgmp_threshold_tier_detected: str | None = None

    other_framework_signals: dict[str, list[str]] = Field(default_factory=dict)

    m13_todo: str = "Apply full regulatory profile based on these signals"

    model_config = ConfigDict(extra="forbid")


class AtomicCapabilitySkeleton(BaseModel):
    """Prepared by M12 from source_rules, filled by M14 from offers."""

    procurement_family: ProcurementFamily
    procurement_family_sub: ProcurementFamilySub

    active_capability_sections: list[str] = Field(default_factory=list)
    inactive_capability_sections: list[str] = Field(default_factory=list)

    eligibility_checklist: list[EligibilityGateExtracted] = Field(default_factory=list)
    scoring_structure: ScoringStructureDetected | None = None

    m14_todo: str = "Evaluate each offer against this skeleton"

    model_config = ConfigDict(extra="forbid")


class MarketContextSignal(BaseModel):
    """Market context detected by M12, exploited by M14."""

    prices_detected: bool = False
    currency_detected: str | None = None
    price_basis_detected: Literal["HT", "TTC", "unknown"] | None = None

    mercuriale_link_hint: str | None = None
    material_price_index_applicable: bool = False
    material_categories_detected: list[str] = Field(default_factory=list)

    zone_for_price_reference: list[str] = Field(default_factory=list)

    market_survey_linked: bool = False
    market_survey_document_id: str | None = None

    model_config = ConfigDict(extra="forbid")


class M12Handoffs(BaseModel):
    regulatory_profile_skeleton: RegulatoryProfileSkeleton | None = None
    atomic_capability_skeleton: AtomicCapabilitySkeleton | None = None
    market_context_signal: MarketContextSignal | None = None

    model_config = ConfigDict(extra="forbid")


# ── META ──


class M12Meta(BaseModel):
    m12_version: str = "6.0.0"
    annotation_schema_aligned: str = "v3.0.1d"
    mode: Literal["bootstrap", "production"]
    confidence_ceiling: float = Field(ge=0.0, le=1.0)
    corpus_size_at_processing: int = 0
    calibration_palier: int = 0
    processing_timestamp: str = ""
    pass_sequence: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ── TOP-LEVEL M12Output ──


class M12Output(BaseModel):
    """Complete M12 payload — embedded in PassOutput standard."""

    procedure_recognition: ProcedureRecognition
    document_validity: DocumentValidity
    document_conformity_signal: DocumentConformitySignal
    process_linking: ProcessLinking
    handoffs: M12Handoffs
    m12_meta: M12Meta

    model_config = ConfigDict(extra="forbid")
