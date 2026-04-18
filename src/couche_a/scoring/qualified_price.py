"""P3.3 — Contrats prix qualifié et erreur d'ambiguïté commerciale."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "TaxBasis",
    "PriceLevel",
    "QualificationConfidence",
    "QualifiedPrice",
    "PriceAmbiguousError",
]


class TaxBasis(StrEnum):
    HT = "HT"
    TTC = "TTC"


class PriceLevel(StrEnum):
    UNIT = "UNIT"
    LINE_TOTAL = "LINE_TOTAL"
    OFFER_TOTAL = "OFFER_TOTAL"


class QualificationConfidence(StrEnum):
    """Confiance prix P3.3 — grille discrète uniquement (pas de float libre)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class QualifiedPrice(BaseModel):
    """Prix qualifié pour le comparatif commercial (P3.3)."""

    model_config = ConfigDict(extra="forbid")

    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=1)
    tax_basis: TaxBasis
    price_level: PriceLevel
    quantity: float | None = None
    source_document_id: UUID | str | None = None
    evidence_refs: list[UUID | str] = Field(default_factory=list)
    confidence: QualificationConfidence
    human_review_required: bool = False
    flags: list[str] = Field(default_factory=list)


class PriceAmbiguousError(Exception):
    """Données prix contradictoires ou non qualifiables sans choix silencieux."""

    def __init__(self, message: str, *, codes: list[str] | None = None) -> None:
        super().__init__(message)
        self.codes: list[str] = list(codes or [])
        self.message = message

    def __str__(self) -> str:  # pragma: no cover - alignée sur message
        return self.message
