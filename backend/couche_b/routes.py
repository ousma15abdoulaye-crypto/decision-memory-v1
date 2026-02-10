"""Couche B – FastAPI routes for market intelligence & catalog."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.couche_b.models import GeoAlias, GeoMaster, Item, ItemAlias, Unit, UnitAlias, Vendor, VendorAlias
from backend.couche_b.resolvers import resolve_geo, resolve_item, resolve_unit, resolve_vendor
from backend.couche_b.stats import get_price_stats
from backend.system.auth import UserPayload, get_current_user, require_role
from backend.system.db import get_db
from backend.system.firewall import validate_market_signal_payload

__all__ = ["router"]

router = APIRouter(tags=["couche_b"])


# ---- Catalog search endpoints -----------------------------------------------

@router.get("/api/catalog/vendors/search")
async def search_vendors(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _user: UserPayload = Depends(get_current_user),
):
    stmt = select(Vendor).where(Vendor.canonical_name.ilike(f"%{q}%")).limit(20)
    rows = (await db.execute(stmt)).scalars().all()

    alias_stmt = select(VendorAlias).where(VendorAlias.alias.ilike(f"%{q}%")).limit(20)
    alias_rows = (await db.execute(alias_stmt)).scalars().all()

    vendor_ids = {v.id for v in rows} | {a.vendor_id for a in alias_rows}
    if alias_rows:
        extra = select(Vendor).where(Vendor.id.in_([a.vendor_id for a in alias_rows]))
        extra_rows = (await db.execute(extra)).scalars().all()
        rows = list({v.id: v for v in list(rows) + list(extra_rows)}.values())

    return [{"id": v.id, "canonical_name": v.canonical_name, "country": v.country} for v in rows]


@router.get("/api/catalog/items/search")
async def search_items(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _user: UserPayload = Depends(get_current_user),
):
    stmt = select(Item).where(Item.canonical_name.ilike(f"%{q}%")).limit(20)
    rows = (await db.execute(stmt)).scalars().all()

    alias_stmt = select(ItemAlias).where(ItemAlias.alias.ilike(f"%{q}%")).limit(20)
    alias_rows = (await db.execute(alias_stmt)).scalars().all()
    if alias_rows:
        extra = select(Item).where(Item.id.in_([a.item_id for a in alias_rows]))
        extra_rows = (await db.execute(extra)).scalars().all()
        rows = list({i.id: i for i in list(rows) + list(extra_rows)}.values())

    return [{"id": i.id, "canonical_name": i.canonical_name, "category": i.category} for i in rows]


@router.get("/api/catalog/units/search")
async def search_units(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _user: UserPayload = Depends(get_current_user),
):
    stmt = select(Unit).where(or_(Unit.code.ilike(f"%{q}%"), Unit.label.ilike(f"%{q}%"))).limit(20)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": u.id, "code": u.code, "label": u.label} for u in rows]


@router.get("/api/catalog/geo/search")
async def search_geo(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _user: UserPayload = Depends(get_current_user),
):
    stmt = select(GeoMaster).where(GeoMaster.name.ilike(f"%{q}%")).limit(20)
    rows = (await db.execute(stmt)).scalars().all()

    alias_stmt = select(GeoAlias).where(GeoAlias.alias.ilike(f"%{q}%")).limit(20)
    alias_rows = (await db.execute(alias_stmt)).scalars().all()
    if alias_rows:
        extra = select(GeoMaster).where(GeoMaster.id.in_([a.geo_id for a in alias_rows]))
        extra_rows = (await db.execute(extra)).scalars().all()
        rows = list({g.id: g for g in list(rows) + list(extra_rows)}.values())

    return [{"id": g.id, "name": g.name, "geo_type": g.geo_type.value} for g in rows]


# ---- Market intelligence ----------------------------------------------------

@router.get("/api/market-intelligence/stats")
async def market_intelligence_stats(
    item_id: str = Query(...),
    geo_id: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: UserPayload = Depends(get_current_user),
):
    stats = await get_price_stats(item_id, geo_id, db)
    return stats


# ---- Market signal ingestion (admin only) -----------------------------------

class MarketSignalPayload(BaseModel):
    item_name: str
    vendor_name: str
    geo_name: str | None = None
    unit_code: str | None = None
    unit_price: float
    currency: str = "XOF"
    quantity: float | None = None
    signal_date: str | None = None
    source: str | None = None
    case_reference: str | None = None


@router.post("/api/market-signals", status_code=status.HTTP_201_CREATED)
async def ingest_market_signal(
    body: MarketSignalPayload,
    db: AsyncSession = Depends(get_db),
    user: UserPayload = Depends(require_role(["admin"])),
):
    from backend.couche_b.models import MarketSignal

    validate_market_signal_payload(body.model_dump(exclude_none=True))

    vendor_id = await resolve_vendor(body.vendor_name, db)
    item_id = await resolve_item(body.item_name, db)
    unit_id = await resolve_unit(body.unit_code, db) if body.unit_code else None
    geo_id = await resolve_geo(body.geo_name, db) if body.geo_name else None

    signal = MarketSignal(
        item_id=item_id,
        vendor_id=vendor_id,
        geo_id=geo_id,
        unit_id=unit_id,
        unit_price=body.unit_price,
        currency=body.currency,
        quantity=body.quantity,
        signal_date=body.signal_date,
        source=body.source,
        case_reference=body.case_reference,
    )
    db.add(signal)
    await db.flush()
    return {"signal_id": signal.id}
