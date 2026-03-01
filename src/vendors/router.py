"""
Router vendors — GET /vendors uniquement.
Lecture seule M4. Pas d'écriture · pas de couverture · pas de scoring.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.vendors import service

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("")
def list_vendors(
    region: str | None = Query(None, description="Code région ex: BKO"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """Liste paginée des fournisseurs actifs."""
    return service.list_vendors(
        region_code=region,
        limit=limit,
        offset=offset,
    )


@router.get("/{vendor_id}")
def get_vendor(vendor_id: str) -> dict:
    """Détail d'un fournisseur par DMS_VENDOR_ID."""
    vendor = service.get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor non trouvé")
    return vendor
