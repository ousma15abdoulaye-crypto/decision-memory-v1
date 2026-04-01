"""
M13 — Regulatory Compliance Engine : modèles de sortie.

RegulatoryComplianceReport est le payload produit par M13 à partir du
RegulatoryProfileSkeleton (H1) fourni par M12 Pass 1C.

Autorité : Plan Directeur DMS V4.1 — CONTEXT_ANCHOR.md — M12_M13_HANDOFF_CONTRACT.md
Règles   : extra=forbid (E-49), confidence {0.6, 0.8, 1.0} (KILL LIST)
"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.procurement.document_ontology import ProcurementFramework


@unique
class ComplianceVerdict(StrEnum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REVIEW_REQUIRED = "review_required"
    NOT_ASSESSABLE = "not_assessable"
    PIPELINE_ERROR = "pipeline_error"


class EliminatoryGateCheck(BaseModel):
    """Résultat d'un critère éliminatoire SCI §5.2 (NIF, RCCM, RIB, clauses…)."""

    gate_name: str = Field(
        description="Nom du critère éliminatoire (ex. 'nif', 'sci_conditions')"
    )
    status: Literal["present", "absent", "not_applicable"]
    evidence: str = Field(
        default="",
        description="Fragment textuel ou motif regex ayant déclenché la détection",
    )

    model_config = ConfigDict(extra="forbid")


class RegulatoryComplianceReport(BaseModel):
    """
    Sortie M13 — Rapport de conformité réglementaire.

    Produit par le Regulatory Compliance Engine (M13) à partir du
    RegulatoryProfileSkeleton (H1) fourni par M12 Pass 1C.

    Valeurs autorisées pour verdict :
      - compliant         : tous critères éliminatoires présents, seuils respectés
      - non_compliant     : au moins un critère éliminatoire absent ou seuil violé
      - review_required   : framework_confidence < 0.60 ou ambiguïté détectée
      - not_assessable    : framework_detected = UNKNOWN — règles inapplicables
      - pipeline_error    : H1 None sur document source_rules, ou exception inattendue

    Conditions par verdict :
      COMPLIANT         → tous eliminatory_checks status "present" ou "not_applicable"
                          ET threshold_tier cohérent avec procédure détectée
      NON_COMPLIANT     → ≥1 check status "absent"
      REVIEW_REQUIRED   → framework_confidence < 0.60 OU ambiguïté multi-framework
      NOT_ASSESSABLE    → framework_detected = UNKNOWN
      PIPELINE_ERROR    → H1 None sur document kind in SOURCE_RULES_KINDS
    """

    document_id: str = Field(
        description="ID du document analysé (case_document ou corpus ref)"
    )
    framework_applied: ProcurementFramework = Field(
        description="Framework utilisé pour l'évaluation"
    )
    verdict: ComplianceVerdict
    eliminatory_checks: list[EliminatoryGateCheck] = Field(
        default_factory=list,
        description="Liste des critères éliminatoires vérifiés (SCI §5.2, DGMP Art. 45-46…)",
    )
    threshold_tier: str | None = Field(
        default=None,
        description="Palier seuil procédure détecté (ex. 'below_100k', 'above_100k')",
    )
    sustainability_check: bool | None = Field(
        default=None,
        description="True si pondération durabilité ≥ 10% (SCI §4.2), None si non applicable",
    )
    review_reasons: list[str] = Field(
        default_factory=list,
        description="Raisons du verdict review_required ou non_compliant",
    )
    produced_by: str = Field(
        default="M13", description="Identifiant du module producteur"
    )

    model_config = ConfigDict(extra="forbid")
