"""
PriceCheck Engine -- schemas (DMS V3.3.2 / ADR-0009).

Couche A uniquement. Descriptif pur, zéro champ décisionnel.
Interdit : rank, winner, recommendation, selected, offre_retenue,
           shortlist, classement, gagnant.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, field_validator


class PriceVerdict(StrEnum):
    WITHIN_REF = "WITHIN_REF"  # ratio <= price_ratio_acceptable
    ABOVE_REF = "ABOVE_REF"  # ratio > price_ratio_acceptable
    NO_REF = "NO_REF"  # aucune donnée mercuriale disponible


class OffreInput(BaseModel):
    """Offre soumise à analyser (descriptif, audit-ready)."""

    alias_raw: str
    prix_unitaire: float
    unite: str | None = None
    quantite: float = 1.0
    currency: str = "XOF"
    profile_code: str = "GENERIC"

    @field_validator("prix_unitaire")
    @classmethod
    def prix_positif(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("prix_unitaire must be > 0")
        return v

    @field_validator("quantite")
    @classmethod
    def quantite_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantite must be > 0")
        return v


class PriceCheckResult(BaseModel):
    """Résultat descriptif du PriceCheck (audit-ready).

    Aucun champ décisionnel : pas de rank, winner, recommendation,
    selected, offre_retenue, shortlist.
    """

    alias_raw: str
    item_id: str | None = None
    prix_total_soumis: float
    prix_ref: float | None = None
    ratio: float | None = None
    verdict: PriceVerdict
    profile_code: str
    notes: list[str]
    normalisation: object | None = None

    model_config = {"use_enum_values": True}
