"""
Modèles Pydantic v2 pour le référentiel géographique.
Lecture seule — M3 ne produit aucun modèle d'écriture public.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GeoCountry(BaseModel):
    id: UUID
    iso2: str
    iso3: str
    name_fr: str
    name_en: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeoRegion(BaseModel):
    id: UUID
    country_id: UUID
    code: str
    name_fr: str
    name_en: str | None
    capitale: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeoCercle(BaseModel):
    id: UUID
    region_id: UUID
    code: str
    name_fr: str
    capitale: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeoCommune(BaseModel):
    id: UUID
    cercle_id: UUID
    code_instat: str
    name_fr: str
    type_commune: str
    chef_lieu: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeoLocalite(BaseModel):
    id: UUID
    commune_id: UUID
    name_fr: str
    type_localite: str
    latitude: float | None
    longitude: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeoZoneOperationnelle(BaseModel):
    id: UUID
    code: str
    name_fr: str
    description: str | None
    organisation: str
    type_zone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
