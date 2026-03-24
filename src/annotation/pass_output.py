"""
Annotation pipeline — enveloppe commune des sorties de passe (PASS_OUTPUT_STANDARD).

Toute passe produit un AnnotationPassOutput ; le détail métier est dans output_data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PassRunStatus(StrEnum):
    """Statuts normalisés pour une exécution de passe."""

    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"


class PassError(BaseModel):
    """Erreur structurée — jamais silencieuse."""

    code: str = Field(..., min_length=1, description="Code machine stable, ex. OCR_TIMEOUT")
    message: str = Field(..., min_length=1, description="Message humain court")
    detail: dict[str, Any] | None = Field(
        default=None,
        description="Contexte optionnel (non PII par défaut)",
    )


class AnnotationPassOutput(BaseModel):
    """
    Contrat unique entre passes et orchestrateur (PASS_OUTPUT_STANDARD.md).

    Les champs métier par passe vivent dans output_data selon PASS_*_CONTRACT.md.
    """

    pass_name: str = Field(..., min_length=1)
    pass_version: str = Field(..., min_length=1, pattern=r"^\d+\.\d+\.\d+")
    document_id: str = Field(..., min_length=1)
    run_id: UUID
    started_at: datetime
    completed_at: datetime
    status: PassRunStatus
    output_data: dict[str, Any] = Field(default_factory=dict)
    errors: list[PassError] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="model_used, token counts, cost_estimate_usd, duration_ms, …",
    )

    model_config = {"extra": "forbid"}

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(UTC)
