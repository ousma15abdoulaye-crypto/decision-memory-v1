"""
M13B — hooks de persistance (Semaine 2).

Modèles déclarés maintenant ; listes vides à la persistance M13.
extra=forbid (E-49). Confiance audit : grille M13 {0.6, 0.8, 1.0}.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.procurement.m13_confidence import M13Confidence


class PolicySource(BaseModel):
    source_type: str = ""
    jurisdiction: str = ""
    framework: str = ""
    document_title: str = ""
    section_reference: str = ""
    effective_from: str | None = None
    precedence_rank: int = 0
    citation_text: str | None = None

    model_config = ConfigDict(extra="forbid")


class FrameworkConflict(BaseModel):
    framework_a: str = ""
    rule_a: str = ""
    framework_b: str = ""
    rule_b: str = ""
    conflict_type: str = ""
    resolution: str | None = None
    override_basis: str | None = None
    requires_legal_review: bool = False

    model_config = ConfigDict(extra="forbid")


class ControlObjective(BaseModel):
    objective_id: str = ""
    description: str = ""
    status: str = "not_assessed"
    evidence: list[str] = Field(default_factory=list)
    risk_if_unmet: str = ""

    model_config = ConfigDict(extra="forbid")


class Derogation(BaseModel):
    derogation_type: str = ""
    legal_basis: str = ""
    authority_required: str = ""
    authority_obtained: bool = False
    justification: str = ""
    expiry: str | None = None
    residual_risk: str = ""

    model_config = ConfigDict(extra="forbid")


class AuditAssertion(BaseModel):
    assertion_id: str = ""
    statement: str = ""
    verifiable: bool = True
    evidence_references: list[str] = Field(default_factory=list)
    confidence: M13Confidence = 0.6

    model_config = ConfigDict(extra="forbid")


class NormativeEvidence(BaseModel):
    rule_applied: str = ""
    source_document: str = ""
    section: str = ""
    exact_quote: str | None = None
    application_rationale: str = ""

    model_config = ConfigDict(extra="forbid")


class M13BHooksPayload(BaseModel):
    """Tranche M13B — toutes listes vides jusqu'à Semaine 2."""

    policy_sources: list[PolicySource] = Field(default_factory=list)
    framework_conflicts: list[FrameworkConflict] = Field(default_factory=list)
    control_objectives: list[ControlObjective] = Field(default_factory=list)
    derogations: list[Derogation] = Field(default_factory=list)
    audit_assertions: list[AuditAssertion] = Field(default_factory=list)
    normative_evidence: list[NormativeEvidence] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
