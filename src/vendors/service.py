"""
Couche service vendor — M4.
Délègue au repository. Pas de logique métier supplémentaire en M4.
"""

from __future__ import annotations

from src.vendors import repository


def list_vendors(
    region_code: str | None = None,
    activity_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    return repository.list_vendors(
        region_code=region_code,
        activity_status=activity_status,
        limit=limit,
        offset=offset,
    )


def get_vendor_by_id(vendor_id: str) -> dict | None:
    return repository.get_vendor_by_id(vendor_id)
