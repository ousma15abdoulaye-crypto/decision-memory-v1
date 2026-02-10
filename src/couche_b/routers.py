"""
Couche B — API Endpoints (Market Intelligence)
Constitution DMS V2.1 §6
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, insert, update, func, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection
from src.db import DATABASE_URL
from src.couche_b.resolvers import normalize_text, generate_ulid, resolve_vendor, resolve_item, resolve_unit, resolve_geo

router = APIRouter(prefix="/api/couche-b", tags=["Couche B - Market Intelligence"])

# Pydantic Models

class ObservationInput(BaseModel):
    """Single observation in a market survey"""
    item_description: str = Field(..., min_length=1, max_length=500)
    unit_text: str = Field(..., min_length=1, max_length=20)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    vendor_name: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None


class MarketSurveyInput(BaseModel):
    """Market survey submission"""
    observation_date: date
    location_name: str = Field(..., min_length=1, max_length=200)
    observations: List[ObservationInput] = Field(..., min_items=1)
    source_type: Optional[str] = Field(None, max_length=50)
    source_ref: Optional[str] = Field(None, max_length=100)
    surveyor_notes: Optional[str] = None


class CatalogSearchResult(BaseModel):
    """Catalog search result item"""
    id: str
    canonical_name: str
    match_type: str  # 'exact' or 'fuzzy'
    status: Optional[str] = None


class MarketSignalDetail(BaseModel):
    """Market signal detail"""
    signal_id: str
    observation_date: date
    item: Dict[str, str]
    vendor: Optional[Dict[str, str]]
    geo: Dict[str, str]
    unit: Dict[str, str]
    quantity: Decimal
    unit_price: Decimal
    total_price: Optional[Decimal]
    validation_status: str
    created_at: datetime


class MarketStatsResponse(BaseModel):
    """Market statistics response"""
    item_id: str
    item_name: str
    geo_id: Optional[str]
    geo_name: Optional[str]
    period_from: Optional[date]
    period_to: Optional[date]
    stats: Dict[str, Any]


# Dependency to get database connection
async def get_db_connection():
    """Get async database connection"""
    if DATABASE_URL.startswith("postgresql"):
        async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(async_url, echo=False)
        async with engine.begin() as conn:
            yield conn
        await engine.dispose()
    else:
        # For SQLite, fallback to sync
        raise HTTPException(status_code=500, detail="Async endpoints require PostgreSQL")


# CATALOG SEARCH ENDPOINTS

@router.get("/catalog/vendors/search", response_model=List[CatalogSearchResult])
async def search_vendors(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50)
):
    """Autocomplete vendors (canonical + aliases)"""
    from src.couche_b.models import vendors, vendor_aliases
    from src.db import engine
    
    normalized_query = normalize_text(q)
    results = []
    
    # For simplicity, use sync engine for catalog searches
    with engine.begin() as conn:
        # Search canonical names
        stmt = select(vendors).where(
            and_(
                vendors.c.status.in_(['active', 'proposed']),
                or_(
                    vendors.c.canonical_name.ilike(f'%{q}%'),
                    func.lower(vendors.c.canonical_name).like(f'%{normalized_query}%')
                )
            )
        ).limit(limit)
        
        vendor_results = conn.execute(stmt).fetchall()
        
        for vendor in vendor_results:
            results.append(CatalogSearchResult(
                id=vendor.vendor_id,
                canonical_name=vendor.canonical_name,
                match_type='exact',
                status=vendor.status
            ))
        
        # Search aliases if we have room
        if len(results) < limit:
            stmt = select(vendor_aliases.c.vendor_id, vendor_aliases.c.alias_name).where(
                vendor_aliases.c.alias_name.ilike(f'%{q}%')
            ).limit(limit - len(results))
            
            alias_results = conn.execute(stmt).fetchall()
            
            for alias in alias_results:
                # Get the vendor
                vendor_stmt = select(vendors).where(vendors.c.vendor_id == alias.vendor_id)
                vendor = conn.execute(vendor_stmt).fetchone()
                if vendor:
                    results.append(CatalogSearchResult(
                        id=vendor.vendor_id,
                        canonical_name=f"{vendor.canonical_name} (alias: {alias.alias_name})",
                        match_type='fuzzy',
                        status=vendor.status
                    ))
    
    return results[:limit]


@router.get("/catalog/items/search", response_model=List[CatalogSearchResult])
async def search_items(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50)
):
    """Autocomplete items"""
    from src.couche_b.models import items, item_aliases
    from src.db import engine
    
    normalized_query = normalize_text(q)
    results = []
    
    with engine.begin() as conn:
        # Search canonical descriptions
        stmt = select(items).where(
            and_(
                items.c.status.in_(['active', 'proposed']),
                or_(
                    items.c.canonical_description.ilike(f'%{q}%'),
                    func.lower(items.c.canonical_description).like(f'%{normalized_query}%')
                )
            )
        ).limit(limit)
        
        item_results = conn.execute(stmt).fetchall()
        
        for item in item_results:
            results.append(CatalogSearchResult(
                id=item.item_id,
                canonical_name=item.canonical_description,
                match_type='exact',
                status=item.status
            ))
        
        # Search aliases
        if len(results) < limit:
            stmt = select(item_aliases.c.item_id, item_aliases.c.alias_description).where(
                item_aliases.c.alias_description.ilike(f'%{q}%')
            ).limit(limit - len(results))
            
            alias_results = conn.execute(stmt).fetchall()
            
            for alias in alias_results:
                item_stmt = select(items).where(items.c.item_id == alias.item_id)
                item = conn.execute(item_stmt).fetchone()
                if item:
                    results.append(CatalogSearchResult(
                        id=item.item_id,
                        canonical_name=f"{item.canonical_description} (alias: {alias.alias_description})",
                        match_type='fuzzy',
                        status=item.status
                    ))
    
    return results[:limit]


@router.get("/catalog/units/search", response_model=List[CatalogSearchResult])
async def search_units(
    q: str = Query(..., min_length=1, max_length=20),
    limit: int = Query(10, ge=1, le=50)
):
    """Autocomplete units"""
    from src.couche_b.models import units, unit_aliases
    from src.db import engine
    
    normalized_query = normalize_text(q)
    results = []
    
    with engine.begin() as conn:
        # Search canonical symbols and names
        stmt = select(units).where(
            or_(
                units.c.canonical_symbol.ilike(f'%{q}%'),
                units.c.canonical_name.ilike(f'%{q}%'),
                func.lower(units.c.canonical_name).like(f'%{normalized_query}%')
            )
        ).limit(limit)
        
        unit_results = conn.execute(stmt).fetchall()
        
        for unit in unit_results:
            results.append(CatalogSearchResult(
                id=unit.unit_id,
                canonical_name=f"{unit.canonical_symbol} ({unit.canonical_name})",
                match_type='exact'
            ))
        
        # Search aliases
        if len(results) < limit:
            stmt = select(unit_aliases.c.unit_id, unit_aliases.c.alias_symbol, unit_aliases.c.alias_name).where(
                or_(
                    unit_aliases.c.alias_symbol.ilike(f'%{q}%'),
                    unit_aliases.c.alias_name.ilike(f'%{q}%')
                )
            ).limit(limit - len(results))
            
            alias_results = conn.execute(stmt).fetchall()
            
            for alias in alias_results:
                unit_stmt = select(units).where(units.c.unit_id == alias.unit_id)
                unit = conn.execute(unit_stmt).fetchone()
                if unit:
                    alias_display = alias.alias_symbol or alias.alias_name
                    results.append(CatalogSearchResult(
                        id=unit.unit_id,
                        canonical_name=f"{unit.canonical_symbol} (alias: {alias_display})",
                        match_type='fuzzy'
                    ))
    
    return results[:limit]


@router.get("/catalog/geo/search", response_model=List[CatalogSearchResult])
async def search_geo(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50)
):
    """Autocomplete geo zones"""
    from src.couche_b.models import geo_master, geo_aliases
    from src.db import engine
    
    normalized_query = normalize_text(q)
    results = []
    
    with engine.begin() as conn:
        # Search canonical names
        stmt = select(geo_master).where(
            and_(
                geo_master.c.status.in_(['active', 'proposed']),
                or_(
                    geo_master.c.canonical_name.ilike(f'%{q}%'),
                    func.lower(geo_master.c.canonical_name).like(f'%{normalized_query}%')
                )
            )
        ).limit(limit)
        
        geo_results = conn.execute(stmt).fetchall()
        
        for geo in geo_results:
            results.append(CatalogSearchResult(
                id=geo.geo_id,
                canonical_name=geo.canonical_name,
                match_type='exact',
                status=geo.status
            ))
        
        # Search aliases
        if len(results) < limit:
            stmt = select(geo_aliases.c.geo_id, geo_aliases.c.alias_name).where(
                geo_aliases.c.alias_name.ilike(f'%{q}%')
            ).limit(limit - len(results))
            
            alias_results = conn.execute(stmt).fetchall()
            
            for alias in alias_results:
                geo_stmt = select(geo_master).where(geo_master.c.geo_id == alias.geo_id)
                geo = conn.execute(geo_stmt).fetchone()
                if geo:
                    results.append(CatalogSearchResult(
                        id=geo.geo_id,
                        canonical_name=f"{geo.canonical_name} (alias: {alias.alias_name})",
                        match_type='fuzzy',
                        status=geo.status
                    ))
    
    return results[:limit]


# MARKET SURVEY ENDPOINTS

@router.post("/market-survey")
async def create_market_survey(survey: MarketSurveyInput):
    """Create market survey with propose-only pattern
    
    Uses entity resolvers to match or create proposed entities.
    All created signals start in 'pending' validation status.
    """
    from src.couche_b.models import market_signals
    from src.db import DATABASE_URL
    
    if not DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=500, detail="Market survey requires PostgreSQL")
    
    async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False)
    
    signal_ids = []
    
    try:
        async with engine.begin() as conn:
            # Resolve geo
            try:
                geo_id = await resolve_geo(conn, survey.location_name)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Location resolution failed: {str(e)}")
            
            # Process each observation
            for obs in survey.observations:
                try:
                    # Resolve entities
                    item_id = await resolve_item(conn, obs.item_description)
                    unit_id = await resolve_unit(conn, obs.unit_text)
                    
                    vendor_id = None
                    if obs.vendor_name:
                        vendor_id = await resolve_vendor(conn, obs.vendor_name)
                    
                    # Calculate total price
                    total_price = obs.quantity * obs.unit_price
                    
                    # Create signal
                    signal_id = generate_ulid()
                    stmt = insert(market_signals).values(
                        signal_id=signal_id,
                        observation_date=survey.observation_date,
                        item_id=item_id,
                        vendor_id=vendor_id,
                        geo_id=geo_id,
                        unit_id=unit_id,
                        quantity=obs.quantity,
                        unit_price=obs.unit_price,
                        total_price=total_price,
                        validation_status='pending',
                        source_type=survey.source_type,
                        source_ref=survey.source_ref,
                        notes=obs.notes or survey.surveyor_notes
                    )
                    await conn.execute(stmt)
                    signal_ids.append(signal_id)
                    
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Observation processing failed: {str(e)}")
        
        await engine.dispose()
        
        return {
            "message": f"Market survey created with {len(signal_ids)} observations",
            "signal_ids": signal_ids,
            "status": "pending_validation"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Survey creation failed: {str(e)}")


@router.get("/market-survey/validation-queue")
async def get_validation_queue(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get pending proposals for admin validation"""
    from src.couche_b.models import market_signals, items, vendors, geo_master, units
    from src.db import engine
    
    results = []
    
    with engine.begin() as conn:
        # Get pending signals with joins
        stmt = select(
            market_signals,
            items.c.canonical_description.label('item_name'),
            geo_master.c.canonical_name.label('geo_name'),
            units.c.canonical_symbol.label('unit_symbol')
        ).select_from(
            market_signals
            .join(items, market_signals.c.item_id == items.c.item_id)
            .join(geo_master, market_signals.c.geo_id == geo_master.c.geo_id)
            .join(units, market_signals.c.unit_id == units.c.unit_id)
        ).where(
            market_signals.c.validation_status == 'pending'
        ).order_by(
            market_signals.c.created_at.desc()
        ).limit(limit).offset(offset)
        
        signals = conn.execute(stmt).fetchall()
        
        for signal in signals:
            vendor_name = None
            if signal.vendor_id:
                vendor_stmt = select(vendors.c.canonical_name).where(vendors.c.vendor_id == signal.vendor_id)
                vendor = conn.execute(vendor_stmt).fetchone()
                if vendor:
                    vendor_name = vendor.canonical_name
            
            results.append({
                'signal_id': signal.signal_id,
                'observation_date': signal.observation_date.isoformat(),
                'item': signal.item_name,
                'vendor': vendor_name,
                'geo': signal.geo_name,
                'unit': signal.unit_symbol,
                'quantity': float(signal.quantity),
                'unit_price': float(signal.unit_price),
                'total_price': float(signal.total_price) if signal.total_price else None,
                'created_at': signal.created_at.isoformat()
            })
    
    return {
        'count': len(results),
        'signals': results
    }


@router.patch("/market-survey/{signal_id}/validate")
async def validate_signal(
    signal_id: str,
    action: str = Query(..., regex="^(approve|reject)$")
):
    """Validate or reject market signal (admin)"""
    from src.couche_b.models import market_signals
    from src.db import DATABASE_URL
    
    if not DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=500, detail="Validation requires PostgreSQL")
    
    async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Check signal exists and is pending
            stmt = select(market_signals).where(
                and_(
                    market_signals.c.signal_id == signal_id,
                    market_signals.c.validation_status == 'pending'
                )
            )
            result = await conn.execute(stmt)
            signal = result.fetchone()
            
            if not signal:
                raise HTTPException(status_code=404, detail="Signal not found or already validated")
            
            # Update validation status
            new_status = 'confirmed' if action == 'approve' else 'rejected'
            stmt = update(market_signals).where(
                market_signals.c.signal_id == signal_id
            ).values(
                validation_status=new_status,
                validated_at=datetime.now(),
                validated_by='admin'  # TODO: Get from auth context
            )
            await conn.execute(stmt)
        
        await engine.dispose()
        
        return {
            'signal_id': signal_id,
            'action': action,
            'new_status': new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# MARKET INTELLIGENCE ENDPOINT

@router.get("/market-intelligence/search")
async def search_market_intelligence(
    item_id: Optional[str] = None,
    geo_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    validation_status: Optional[str] = Query('confirmed', regex="^(pending|confirmed|rejected|all)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Search market signals with filters"""
    from src.couche_b.models import market_signals, items, vendors, geo_master, units
    from src.db import engine
    
    results = []
    
    with engine.begin() as conn:
        # Build query
        stmt = select(
            market_signals,
            items.c.canonical_description.label('item_name'),
            geo_master.c.canonical_name.label('geo_name'),
            units.c.canonical_symbol.label('unit_symbol')
        ).select_from(
            market_signals
            .join(items, market_signals.c.item_id == items.c.item_id)
            .join(geo_master, market_signals.c.geo_id == geo_master.c.geo_id)
            .join(units, market_signals.c.unit_id == units.c.unit_id)
        )
        
        # Apply filters
        conditions = []
        if validation_status != 'all':
            conditions.append(market_signals.c.validation_status == validation_status)
        if item_id:
            conditions.append(market_signals.c.item_id == item_id)
        if geo_id:
            conditions.append(market_signals.c.geo_id == geo_id)
        if vendor_id:
            conditions.append(market_signals.c.vendor_id == vendor_id)
        if date_from:
            conditions.append(market_signals.c.observation_date >= date_from)
        if date_to:
            conditions.append(market_signals.c.observation_date <= date_to)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(market_signals.c.observation_date.desc()).limit(limit).offset(offset)
        
        signals = conn.execute(stmt).fetchall()
        
        for signal in signals:
            vendor_name = None
            if signal.vendor_id:
                vendor_stmt = select(vendors.c.canonical_name).where(vendors.c.vendor_id == signal.vendor_id)
                vendor = conn.execute(vendor_stmt).fetchone()
                if vendor:
                    vendor_name = vendor.canonical_name
            
            results.append({
                'signal_id': signal.signal_id,
                'observation_date': signal.observation_date.isoformat(),
                'item': {'id': signal.item_id, 'name': signal.item_name},
                'vendor': {'id': signal.vendor_id, 'name': vendor_name} if vendor_name else None,
                'geo': {'id': signal.geo_id, 'name': signal.geo_name},
                'unit': {'id': signal.unit_id, 'symbol': signal.unit_symbol},
                'quantity': float(signal.quantity),
                'unit_price': float(signal.unit_price),
                'total_price': float(signal.total_price) if signal.total_price else None,
                'validation_status': signal.validation_status
            })
    
    return {
        'count': len(results),
        'signals': results
    }


@router.get("/market-intelligence/stats", response_model=MarketStatsResponse)
async def get_market_stats(
    item_id: str,
    geo_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
):
    """Get price statistics (avg, min, max, median)"""
    from src.couche_b.models import market_signals, items, geo_master
    from src.db import engine
    
    with engine.begin() as conn:
        # Get item name
        item_stmt = select(items.c.canonical_description).where(items.c.item_id == item_id)
        item = conn.execute(item_stmt).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Get geo name if provided
        geo_name = None
        if geo_id:
            geo_stmt = select(geo_master.c.canonical_name).where(geo_master.c.geo_id == geo_id)
            geo = conn.execute(geo_stmt).fetchone()
            if geo:
                geo_name = geo.canonical_name
        
        # Build query for statistics
        stmt = select(
            func.avg(market_signals.c.unit_price).label('avg_price'),
            func.min(market_signals.c.unit_price).label('min_price'),
            func.max(market_signals.c.unit_price).label('max_price'),
            func.count(market_signals.c.signal_id).label('count')
        ).where(
            and_(
                market_signals.c.item_id == item_id,
                market_signals.c.validation_status == 'confirmed'
            )
        )
        
        if geo_id:
            stmt = stmt.where(market_signals.c.geo_id == geo_id)
        if date_from:
            stmt = stmt.where(market_signals.c.observation_date >= date_from)
        if date_to:
            stmt = stmt.where(market_signals.c.observation_date <= date_to)
        
        result = conn.execute(stmt).fetchone()
        
        # Calculate median (requires getting all prices)
        prices_stmt = select(market_signals.c.unit_price).where(
            and_(
                market_signals.c.item_id == item_id,
                market_signals.c.validation_status == 'confirmed'
            )
        )
        if geo_id:
            prices_stmt = prices_stmt.where(market_signals.c.geo_id == geo_id)
        if date_from:
            prices_stmt = prices_stmt.where(market_signals.c.observation_date >= date_from)
        if date_to:
            prices_stmt = prices_stmt.where(market_signals.c.observation_date <= date_to)
        
        prices = [row.unit_price for row in conn.execute(prices_stmt).fetchall()]
        median_price = None
        if prices:
            prices.sort()
            n = len(prices)
            median_price = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        
        return MarketStatsResponse(
            item_id=item_id,
            item_name=item.canonical_description,
            geo_id=geo_id,
            geo_name=geo_name,
            period_from=date_from,
            period_to=date_to,
            stats={
                'avg_price': float(result.avg_price) if result.avg_price else None,
                'min_price': float(result.min_price) if result.min_price else None,
                'max_price': float(result.max_price) if result.max_price else None,
                'median_price': float(median_price) if median_price else None,
                'count': result.count
            }
        )
