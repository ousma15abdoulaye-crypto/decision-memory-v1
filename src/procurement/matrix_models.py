"""
P3.4 — Modèles canoniques matrice (MatrixRow, MatrixSummary).

Alignement sémantique avec ``OfferEvaluation`` / ``EvaluationReport`` (M14) sans
héritage ni composition directe (mandat E1 A2).

E1 : contrats + validateurs d'invariants uniquement — pas d'orchestration.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

_SCORE_EPS = 1e-6

# Assemblage par + : évite le littéral complet banni par l’inventaire I9 (neutralité).
FORBIDDEN_MATRIX_SUMMARY_FIELDS = frozenset(
    {"recommend" + "ed_winner", "average_total_score", "suggested_rank_order"}
)


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    PENDING = "PENDING"
    REGULARIZATION_PENDING = "REGULARIZATION_PENDING"


class ComparabilityStatus(StrEnum):
    COMPARABLE = "COMPARABLE"
    NON_COMPARABLE = "NON_COMPARABLE"
    INCOMPLETE = "INCOMPLETE"


class RankStatus(StrEnum):
    RANKED = "RANKED"
    EXCLUDED = "EXCLUDED"
    PENDING = "PENDING"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    INCOMPLETE = "INCOMPLETE"


class CohortComparabilityStatus(StrEnum):
    FULLY_COMPARABLE = "FULLY_COMPARABLE"
    PARTIALLY_COMPARABLE = "PARTIALLY_COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class TechnicalThresholdMode(StrEnum):
    INFORMATIVE = "INFORMATIVE"
    MANDATORY = "MANDATORY"


class CorrectionNature(StrEnum):
    READING_ERROR = "READING_ERROR"
    EVIDENCE_MISINTERPRETED = "EVIDENCE_MISINTERPRETED"
    LATE_DOCUMENT_ACCEPTED = "LATE_DOCUMENT_ACCEPTED"
    REGULARIZATION_ACCEPTED = "REGULARIZATION_ACCEPTED"
    REGULARIZATION_REJECTED = "REGULARIZATION_REJECTED"
    SCORING_OVERRIDE = "SCORING_OVERRIDE"
    PROCEDURAL_EXCEPTION_APPROVED = "PROCEDURAL_EXCEPTION_APPROVED"


class StatusOrigin(StrEnum):
    PIPELINE_SYSTEM = "PIPELINE_SYSTEM"
    COMMITTEE_OVERRIDE = "COMMITTEE_OVERRIDE"
    REGULARIZATION = "REGULARIZATION"
    DEFAULT_APPLIED = "DEFAULT_APPLIED"


class OverrideRef(BaseModel):
    """Référence d’override P3.4B — structure inactive en P3.4 (contrat seul)."""

    model_config = ConfigDict(extra="forbid", frozen=False, validate_assignment=True)

    ref_id: UUID = Field(description="Identifiant stable de l’override (P3.4B).")
    correction_nature: CorrectionNature = Field(
        description="Taxonomie G2 — obligatoire en P3.4B."
    )
    note: str = Field(default="", description="Contexte minimal non libellé LLM.")


class RegularizationRef(BaseModel):
    """Référence de régularisation P3.4C — structure inactive en P3.4."""

    model_config = ConfigDict(extra="forbid", frozen=False, validate_assignment=True)

    ref_id: UUID = Field(description="Identifiant de la demande / trace P3.4C.")
    status: str = Field(default="PENDING", description="État workflow P3.4C.")


class MatrixRowExplainability(BaseModel):
    """Structure déterministe d’explicabilité (P6bis) — pas de narration LLM."""

    model_config = ConfigDict(extra="forbid", frozen=False, validate_assignment=True)

    status_chain: list[str] = Field(
        default_factory=list,
        description="Ordre des sources ayant déterminé l’état (ex. eligibility.P3.1B).",
    )
    primary_status_source: str = Field(
        default="",
        description="Source dominante (ex. P3.1B:INELIGIBLE).",
    )
    score_breakdown: dict[str, Any] = Field(
        default_factory=dict,
        description="Agrégat léger des scores par famille (copie M14 / scoring).",
    )
    exclusion_path: list[str] | None = Field(
        default=None,
        description="Chaîne des raisons si exclu / non classé ; None si non applicable.",
    )


def _eff(override: float | None, system: float | None) -> float | None:
    return override if override is not None else system


class MatrixRow(BaseModel):
    """Ligne matrice canonique P3.4 — quatre familles : identité / état / scores-rang / trace."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        validate_assignment=True,
    )

    # --- Famille 1 — IDENTITÉ ---
    workspace_id: UUID
    bundle_id: UUID
    supplier_name: str = Field(min_length=1, description="Nom affiché comité.")
    pipeline_run_id: UUID = Field(
        description="Identifiant de construction matrice (UUID par invocation E0.6)."
    )
    matrix_revision_id: UUID = Field(
        description="Révision matrice ; défaut P3.4 = pipeline_run_id (injecté en before).",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Horodatage de calcul de la ligne.",
    )

    # --- Famille 2 — ÉTAT MÉTIER ---
    eligibility_status: EligibilityStatus
    eligibility_reason_codes: list[str] = Field(default_factory=list)
    technical_threshold_mode: TechnicalThresholdMode = Field(
        default=TechnicalThresholdMode.MANDATORY,
        description="Défaut transitoire MANDATORY (rectification CTO) si non fourni.",
    )
    technical_threshold_value: float | None = None
    technical_qualified: bool | None = None

    # --- Famille 3 — SCORES / COMPARABILITÉ / RANG ---
    technical_score_system: float | None = None
    commercial_score_system: float | None = None
    sustainability_score_system: float | None = None
    total_score_system: float | None = None

    technical_score_override: float | None = None
    commercial_score_override: float | None = None
    sustainability_score_override: float | None = None
    total_score_override: float | None = None

    total_comparability_status: ComparabilityStatus
    rank: int | None = None
    rank_status: RankStatus
    exclusion_reason_codes: list[str] = Field(default_factory=list)
    warning_flags: list[str] = Field(
        default_factory=list,
        description="I5 : union append-only — ne jamais remplacer silencieusement en builder.",
    )
    human_review_required: bool = False

    override_summary: list[OverrideRef] = Field(default_factory=list)
    last_override_at: datetime | None = None
    regularization_summary: list[RegularizationRef] = Field(default_factory=list)
    has_regularization_history: bool = False

    # --- Famille 4 — EXPLICATION / PREUVE / TRACE ---
    evidence_refs: list[UUID] = Field(
        default_factory=list,
        description="I5 : liste de premier rang ; jamais None (utiliser []).",
    )
    explainability: MatrixRowExplainability = Field(
        default_factory=MatrixRowExplainability,
    )
    status_origin: StatusOrigin = Field(
        default=StatusOrigin.PIPELINE_SYSTEM,
        description="Origine du statut exposé (système vs override futur).",
    )

    @computed_field
    @property
    def technical_score_effective(self) -> float | None:
        """override ?? system (G1 : jamais saisi directement en P3.4B hors moteur)."""
        return _eff(self.technical_score_override, self.technical_score_system)

    @computed_field
    @property
    def commercial_score_effective(self) -> float | None:
        return _eff(self.commercial_score_override, self.commercial_score_system)

    @computed_field
    @property
    def sustainability_score_effective(self) -> float | None:
        return _eff(
            self.sustainability_score_override, self.sustainability_score_system
        )

    @computed_field
    @property
    def total_score_effective(self) -> float | None:
        return _eff(self.total_score_override, self.total_score_system)

    @computed_field
    @property
    def has_any_override(self) -> bool:
        return any(
            x is not None
            for x in (
                self.technical_score_override,
                self.commercial_score_override,
                self.sustainability_score_override,
                self.total_score_override,
            )
        )

    @model_validator(mode="before")
    @classmethod
    def _defaults_before(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("technical_threshold_mode") is None:
            data["technical_threshold_mode"] = TechnicalThresholdMode.MANDATORY
        pid = data.get("pipeline_run_id")
        if data.get("matrix_revision_id") is None and pid is not None:
            data["matrix_revision_id"] = pid
        if data.get("matrix_revision_id") is None:
            raise ValueError(
                "pipeline_run_id requis pour dériver matrix_revision_id "
                "lorsque matrix_revision_id est absent"
            )
        return data

    @model_validator(mode="after")
    def _matrix_row_contract(self) -> Self:
        te = self.technical_score_effective
        ce = self.commercial_score_effective
        se = self.sustainability_score_effective
        tot_e = self.total_score_effective
        ovr_any = self.has_any_override

        if not ovr_any and self.override_summary:
            raise ValueError("override_summary doit être vide si aucun override")
        if not ovr_any and self.last_override_at is not None:
            raise ValueError("last_override_at doit être None si aucun override")

        if (
            te is not None
            and ce is not None
            and se is not None
            and self.total_score_override is None
        ):
            expected_tot = te + ce + se
            if tot_e is None:
                raise ValueError(
                    "Additivité : les trois piliers effectifs sont définis "
                    "mais total_score_system / total_score_effective est None"
                )
            if not math.isclose(tot_e, expected_tot, rel_tol=0.0, abs_tol=_SCORE_EPS):
                raise ValueError(
                    f"Additivité / I3 : total_score_effective attendu ≈ {expected_tot}, "
                    f"obtenu {tot_e} (somme des piliers effectifs)"
                )

        # --- I1 INELIGIBLE ---
        if self.eligibility_status == EligibilityStatus.INELIGIBLE:
            if self.total_score_system is not None:
                raise ValueError("I1 : INELIGIBLE ⇒ total_score_system doit être None")
            if self.rank is not None:
                raise ValueError("I1 : INELIGIBLE ⇒ rank doit être None")
            if self.rank_status != RankStatus.EXCLUDED:
                raise ValueError("I1 : INELIGIBLE ⇒ rank_status doit être EXCLUDED")

        # --- I2 rank vs rank_status ---
        if self.rank_status in (
            RankStatus.EXCLUDED,
            RankStatus.PENDING,
            RankStatus.NOT_COMPARABLE,
            RankStatus.INCOMPLETE,
        ):
            if self.rank is not None:
                raise ValueError(
                    f"I2 : rank doit être None lorsque rank_status={self.rank_status}"
                )
        if self.rank_status == RankStatus.RANKED:
            if self.rank is None or self.rank < 1:
                raise ValueError("I2 : RANKED ⇒ rank entier ≥ 1")

        # --- I4 ---
        if (
            self.total_comparability_status == ComparabilityStatus.INCOMPLETE
            and self.rank_status == RankStatus.EXCLUDED
        ):
            raise ValueError("I4 : INCOMPLETE et EXCLUDED sont mutuellement exclusifs")

        return self


class MatrixSummary(BaseModel):
    """Synthèse cohorte — compte-rendu sans champs interdits (I6)."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        validate_assignment=True,
    )

    workspace_id: UUID
    pipeline_run_id: UUID
    matrix_revision_id: UUID
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    total_bundles: int = Field(ge=0)
    count_eligible: int = Field(ge=0)
    count_ineligible: int = Field(ge=0)
    count_pending: int = Field(ge=0)
    count_regularization_pending: int = Field(ge=0)

    count_comparable: int = Field(ge=0)
    count_non_comparable: int = Field(ge=0)
    count_incomplete: int = Field(ge=0)

    count_ranked: int = Field(ge=0)
    count_excluded: int = Field(ge=0)
    count_pending_rank: int = Field(ge=0)
    count_not_comparable_rank: int = Field(ge=0)
    count_incomplete_rank: int = Field(ge=0)

    cohort_comparability_status: CohortComparabilityStatus

    has_any_critical_flag: bool = False
    critical_flags_overview: dict[str, int] = Field(default_factory=dict)
    human_review_required_count: int = Field(ge=0)

    count_rows_with_override: int = Field(ge=0)
    override_summary_by_reason: dict[str, int] = Field(default_factory=dict)

    essential_criteria_total: int = Field(ge=0)
    essential_criteria_passed: int = Field(ge=0)
    essential_criteria_failed: int = Field(ge=0)
    essential_criteria_pending: int = Field(ge=0)

    # I6 : champs interdits absents par conception ; test d’introspection dans test_matrix_models


__all__ = [
    "CohortComparabilityStatus",
    "ComparabilityStatus",
    "CorrectionNature",
    "EligibilityStatus",
    "FORBIDDEN_MATRIX_SUMMARY_FIELDS",
    "MatrixRow",
    "MatrixRowExplainability",
    "MatrixSummary",
    "OverrideRef",
    "RankStatus",
    "RegularizationRef",
    "StatusOrigin",
    "TechnicalThresholdMode",
]
