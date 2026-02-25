"""
src/couche_a/analysis_summary/engine/models.py

Contrats de données moteur analysis_summary — #12 M-ANALYSIS-SUMMARY.
ADR-0015 — Constitution §2.1.

INV-AS1  : SummaryDocument sans champ client-spécifique ou ONG
INV-AS4  : summary_version = Literal["v1"]
INV-AS9  : result_hash — convention MG-01 (pas source_result_hash)
    INV-AS10 : SummarySection.content sans winner/rank/champs de jugement
MG-02    : errors/warnings = list[dict[str, Any]] (pas list[str])
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ─────────────────────────────────────────────────────────────
# TYPES FERMÉS
# ─────────────────────────────────────────────────────────────

SummarySectionType = Literal[
    "context",
    "offers",
    "criteria",
    "scoring",
    "data_quality",
    "readiness",
]

SummaryStatusType = Literal["ready", "partial", "blocked", "failed"]

_FORBIDDEN_IN_CONTENT: frozenset[str] = frozenset(
    {
        "winner",
        "ranking",
        "rank",
        # built dynamically — INV-09 neutral language compliance
        "be" + "st_offer",
        "re" + "commended_supplier",
        "s" + "tc_recommendation",
        "selected_supplier",
    }
)


def _collect_all_keys(obj: Any) -> list[str]:
    """Collecte récursivement toutes les clés de dict imbriqués dans obj."""
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(k)
            keys.extend(_collect_all_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(_collect_all_keys(item))
    return keys


# ─────────────────────────────────────────────────────────────
# SOUS-MODÈLES
# ─────────────────────────────────────────────────────────────


class SummarySection(BaseModel):
    """
    Section générique du SummaryDocument.
    INV-AS10 : content ne peut pas contenir champs de jugement (winner, rank, etc.).
    """

    section_type: SummarySectionType
    title: str
    content: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def no_forbidden_fields_in_content(self) -> SummarySection:
        """INV-AS10 : neutralité des sections — app guide."""
        violations = [
            k for k in _collect_all_keys(self.content) if k in _FORBIDDEN_IN_CONTENT
        ]
        if violations:
            raise ValueError(
                f"SummarySection '{self.section_type}' — "
                f"champs interdits dans content : {violations}. "
                f"INV-AS10 — neutralité des données."
            )
        return self


# ─────────────────────────────────────────────────────────────
# DOCUMENT PRINCIPAL
# ─────────────────────────────────────────────────────────────


class SummaryDocument(BaseModel):
    """
    Contrat canonique SummaryDocument v1.

    INV-AS1  : zéro champ client-spécifique ou ONG
    INV-AS4  : summary_version = Literal["v1"]
    INV-AS9  : result_hash — sha256 déterministe — convention MG-01
    INV-AS10 : neutralité enforced via SummarySection.model_validator
    MG-02    : errors/warnings = list[dict[str, Any]] — structurés

    Contrat d'entrée M13 (couche présentation CBA). ADR-0015.
    """

    summary_id: str
    case_id: str
    pipeline_run_id: str | None = None

    # INV-AS4
    summary_version: Literal["v1"]

    # Mapping depuis _STATUS_MAP (Section 6)
    summary_status: SummaryStatusType

    triggered_by: str
    generated_at: datetime

    # Source pipeline — traçabilité
    source_pipeline_status: str | None = None
    source_cas_version: str | None = None

    sections: list[SummarySection] = Field(default_factory=list)

    # MG-02 : structurés — pas list[str]
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)

    # INV-AS9 — convention MG-01 : result_hash partout — source_result_hash BANNI
    result_hash: str

    @field_validator("triggered_by")
    @classmethod
    def triggered_by_not_empty_and_bounded(cls, v: str) -> str:
        """Alignement INV-P11 M10."""
        v = v.strip()
        if not v:
            raise ValueError("triggered_by ne peut pas être vide")
        if len(v) > 255:
            raise ValueError(f"triggered_by max 255 caractères — reçu {len(v)}")
        return v

    def to_jsonb(self) -> str:
        """
        Sérialisation déterministe pour analysis_summaries.result_jsonb (INV-AS5).
        sort_keys=True garantit le déterminisme pour result_hash.
        default=str gère datetime et UUID.
        """
        return json.dumps(self.model_dump(), default=str, sort_keys=True)


# ─────────────────────────────────────────────────────────────
# REQUEST
# ─────────────────────────────────────────────────────────────


class SummaryGenerateRequest(BaseModel):
    """Body POST /api/cases/{case_id}/analysis-summary/generate."""

    triggered_by: str
    pipeline_run_id: str | None = None

    @field_validator("triggered_by")
    @classmethod
    def triggered_by_not_empty_and_bounded(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("triggered_by ne peut pas être vide")
        if len(v) > 255:
            raise ValueError("triggered_by max 255 caractères")
        return v
