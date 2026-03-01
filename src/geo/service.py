"""
Service géographique — logique hiérarchique geo uniquement.
Aucune logique vendor, déduplication ou merge.
"""

from __future__ import annotations

from fastapi import HTTPException

from src.geo import repository


def list_countries() -> list[dict]:
    return repository.get_countries(active_only=True)


def list_regions(iso2: str) -> list[dict]:
    country = repository.get_country_by_iso2(iso2)
    if not country:
        raise HTTPException(
            status_code=404,
            detail=f"Pays introuvable : {iso2}",
        )
    return repository.get_regions_by_country(iso2)


def list_cercles(region_id: str) -> list[dict]:
    cercles = repository.get_cercles_by_region(region_id)
    return cercles


def list_communes(cercle_id: str) -> list[dict]:
    return repository.get_communes_by_cercle(cercle_id)


def search_communes(q: str) -> list[dict]:
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Paramètre q requis (2 caractères minimum)",
        )
    return repository.search_communes(q.strip())


def list_zones() -> list[dict]:
    return repository.get_zones(active_only=True)


def list_communes_by_zone(zone_id: str) -> list[dict]:
    return repository.get_communes_by_zone(zone_id)
