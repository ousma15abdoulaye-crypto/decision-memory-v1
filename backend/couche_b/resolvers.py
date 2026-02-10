"""Couche B – Entity resolution (fuzzy match or create)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.couche_b.models import (
    GeoMaster,
    GeoType,
    Item,
    ItemAlias,
    Unit,
    UnitAlias,
    Vendor,
    VendorAlias,
)

__all__ = ["resolve_vendor", "resolve_item", "resolve_unit", "resolve_geo"]


async def resolve_vendor(name: str, db: AsyncSession) -> str:
    """Find vendor by canonical name or alias (case-insensitive). Create if absent."""
    norm = name.strip()
    stmt = select(Vendor).where(func.lower(Vendor.canonical_name) == norm.lower())
    vendor = (await db.execute(stmt)).scalar_one_or_none()
    if vendor:
        return vendor.id

    # Check aliases
    alias_stmt = select(VendorAlias).where(func.lower(VendorAlias.alias) == norm.lower())
    alias = (await db.execute(alias_stmt)).scalar_one_or_none()
    if alias:
        return alias.vendor_id

    # Create new vendor
    vendor = Vendor(canonical_name=norm)
    db.add(vendor)
    await db.flush()
    return vendor.id


async def resolve_item(name: str, db: AsyncSession) -> str:
    """Find item by canonical name or alias. Create if absent."""
    norm = name.strip()
    stmt = select(Item).where(func.lower(Item.canonical_name) == norm.lower())
    item = (await db.execute(stmt)).scalar_one_or_none()
    if item:
        return item.id

    alias_stmt = select(ItemAlias).where(func.lower(ItemAlias.alias) == norm.lower())
    alias = (await db.execute(alias_stmt)).scalar_one_or_none()
    if alias:
        return alias.item_id

    item = Item(canonical_name=norm)
    db.add(item)
    await db.flush()
    return item.id


async def resolve_unit(code: str, db: AsyncSession) -> str:
    """Find unit by code or alias. Create if absent."""
    norm = code.strip()
    stmt = select(Unit).where(func.lower(Unit.code) == norm.lower())
    unit = (await db.execute(stmt)).scalar_one_or_none()
    if unit:
        return unit.id

    alias_stmt = select(UnitAlias).where(func.lower(UnitAlias.alias) == norm.lower())
    alias = (await db.execute(alias_stmt)).scalar_one_or_none()
    if alias:
        return alias.unit_id

    unit = Unit(code=norm, label=norm)
    db.add(unit)
    await db.flush()
    return unit.id


async def resolve_geo(name: str, db: AsyncSession) -> str:
    """Find geo entity by name or alias. Create as country if absent."""
    norm = name.strip()
    stmt = select(GeoMaster).where(func.lower(GeoMaster.name) == norm.lower())
    geo = (await db.execute(stmt)).scalar_one_or_none()
    if geo:
        return geo.id

    from backend.couche_b.models import GeoAlias

    alias_stmt = select(GeoAlias).where(func.lower(GeoAlias.alias) == norm.lower())
    alias = (await db.execute(alias_stmt)).scalar_one_or_none()
    if alias:
        return alias.geo_id

    geo = GeoMaster(name=norm, geo_type=GeoType.country)
    db.add(geo)
    await db.flush()
    return geo.id
