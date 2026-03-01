"""
Router géographique — GET /geo/* uniquement.
Lecture seule. Aucun endpoint d'écriture.
Aucun endpoint vendor, merge ou déduplication.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.geo import service

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/countries")
def get_countries() -> list[dict]:
    """Retourne la liste des pays actifs."""
    return service.list_countries()


@router.get("/countries/{iso2}/regions")
def get_regions(iso2: str) -> list[dict]:
    """Retourne les régions actives d'un pays (par code ISO2)."""
    return service.list_regions(iso2)


@router.get("/regions/{region_id}/cercles")
def get_cercles(region_id: str) -> list[dict]:
    """Retourne les cercles actifs d'une région."""
    return service.list_cercles(region_id)


@router.get("/cercles/{cercle_id}/communes")
def get_communes(cercle_id: str) -> list[dict]:
    """Retourne les communes actives d'un cercle."""
    return service.list_communes(cercle_id)


@router.get("/communes/search")
def search_communes(q: str = Query(..., min_length=2)) -> list[dict]:
    """Recherche des communes par nom (ILIKE)."""
    return service.search_communes(q)


@router.get("/zones")
def get_zones() -> list[dict]:
    """Retourne les zones opérationnelles actives."""
    return service.list_zones()


@router.get("/zones/{zone_id}/communes")
def get_communes_by_zone(zone_id: str) -> list[dict]:
    """Retourne les communes mappées à une zone opérationnelle."""
    return service.list_communes_by_zone(zone_id)
