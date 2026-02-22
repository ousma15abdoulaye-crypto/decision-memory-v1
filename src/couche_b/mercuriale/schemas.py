"""M-PARSING-MERCURIALE -- Schemas Pydantic (Couche B, memoire only).

Aucun import Couche A. Aucune influence scoring/decision.
ADR-0002 : frontiere Couche B stricte.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from src.couche_b.normalisation.schemas import NormalisationResult


class ParseStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    UNPARSEABLE = "unparseable"


class MercurialeParsedLine(BaseModel):
    """Resultat structure d'une ligne de mercuriale parsee.

    ARCH-002 : jamais None comme retour global -- status + parse_errors portent l'info.
    """

    raw_line: str  # PARSE-001 : toujours conservee
    designation_raw: str | None = None
    unite_raw: str | None = None
    price_min: float | None = None
    price_avg: float | None = None
    price_max: float | None = None
    currency: str = "XOF"
    year: int | None = None
    city: str | None = None
    normalisation: NormalisationResult | None = None
    status: ParseStatus
    parse_errors: list[str]  # PARSE-002 : jamais silencieux

    model_config = {"use_enum_values": True}


class MercurialeParseRequest(BaseModel):
    """Requete de parsing d'un batch de lignes mercuriale."""

    lines: list[str]
    persist: bool = False
    source: str | None = None
