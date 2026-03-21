"""
Router vendors — GET /vendors uniquement.
Lecture seule M4. Pas d'écriture · pas de couverture · pas de scoring.

Patch M4 : filtre activity_status ajouté avec validation canonique.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.vendors import service

router = APIRouter(prefix="/vendors", tags=["vendors"])

_VALID_ACTIVITY_STATUSES = {
    "VERIFIED_ACTIVE",
    "UNVERIFIED",
    "INACTIVE",
    "GHOST_SUSPECTED",
}


@router.get("")
def list_vendors(
    _user: UserClaims = Depends(get_current_user),
    region: str | None = Query(None, description="Code région ex: BKO"),
    activity_status: str | None = Query(
        None,
        description=(
            "Filtre par statut : VERIFIED_ACTIVE · "
            "UNVERIFIED · INACTIVE · GHOST_SUSPECTED"
        ),
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """Liste paginée des fournisseurs actifs."""
    if activity_status and activity_status not in _VALID_ACTIVITY_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"activity_status invalide : {activity_status!r}. "
                f"Valeurs acceptées : {sorted(_VALID_ACTIVITY_STATUSES)}"
            ),
        )
    return service.list_vendors(
        region_code=region,
        activity_status=activity_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{vendor_id}")
def get_vendor(
    vendor_id: str,
    _user: UserClaims = Depends(get_current_user),
) -> dict:
    """Détail d'un fournisseur par DMS_VENDOR_ID."""
    vendor = service.get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor non trouvé")
    return vendor
