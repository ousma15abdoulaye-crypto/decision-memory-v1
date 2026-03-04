"""
Modèles Pydantic — Mercuriale Ingest · DMS V4.1.0
RÈGLE-29 : ingestion brute · pas de normalisation
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class MercurialeSourceCreate(BaseModel):
    filename: str
    sha256: str
    year: int = Field(ge=2000, le=2100)
    source_type: Literal[
        "official_dgmp",
        "official_ministry",
        "ong_reference",
        "corporate_survey",
        "custom",
    ]
    extraction_engine: str = "llamacloud"
    notes: str | None = None


class MercurialLineCreate(BaseModel):
    source_id: uuid.UUID
    item_code: str | None = None
    item_canonical: str = Field(min_length=1)
    group_label: str | None = None

    price_min: Decimal = Field(ge=0)
    price_avg: Decimal = Field(ge=0)
    price_max: Decimal = Field(ge=0)
    unit_price: Decimal = Field(ge=0, default=Decimal("0"))

    currency: str = "XOF"
    unit_raw: str | None = None
    unit_id: uuid.UUID | None = None
    zone_raw: str | None = None
    zone_id: str | None = None  # TEXT en DB (geo_master.id est VARCHAR)
    year: int = Field(ge=2000, le=2100)
    item_id: uuid.UUID | None = None

    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    review_required: bool = False
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def set_unit_price_and_flags(self) -> MercurialLineCreate:
        """
        unit_price = price_avg (référence marché · RÈGLE-29).
        Violations price_order et confidence < 0.80 → review_required + flag metadata.
        Pas d'exception : la data entre dans l'état où elle est.
        """
        self.unit_price = self.price_avg

        if not (self.price_min <= self.price_avg <= self.price_max):
            self.review_required = True
            self.extraction_metadata["price_order_violation"] = True
            self.extraction_metadata["raw_prices"] = {
                "min": float(self.price_min),
                "avg": float(self.price_avg),
                "max": float(self.price_max),
            }

        if self.confidence < 0.80:
            self.review_required = True

        return self


class ImportReport(BaseModel):
    filename: str
    year: int
    sha256: str
    total_rows_parsed: int = 0
    inserted: int = 0
    review_required: int = 0
    skipped_low_confidence: int = 0
    skipped_empty: int = 0
    skipped_price_invalid: int = 0
    zones_resolved: int = 0
    zones_unresolved: int = 0
    already_imported: bool = False
    dry_run: bool = False
    errors: list[str] = Field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        if self.total_rows_parsed == 0:
            return 0.0
        return round(self.inserted / self.total_rows_parsed * 100, 1)
