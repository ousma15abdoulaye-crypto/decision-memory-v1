"""
Couche B — API Endpoints (Market Intelligence)
Constitution DMS V2.1 §6
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

router = APIRouter(prefix="/api", tags=["Couche B - Market Intelligence"])

# TODO Session 3.1: Implémenter endpoints

# CATALOG SEARCH (autocomplete)
@router.get("/catalog/vendors/search")
async def search_vendors(q: str = Query(..., min_length=1)):
    """Autocomplete vendors (canonical + aliases)"""
    # TODO: Implement fuzzy search
    pass

@router.get("/catalog/items/search")
async def search_items(q: str = Query(..., min_length=1)):
    """Autocomplete items"""
    # TODO: Implement
    pass

@router.get("/catalog/units/search")
async def search_units(q: str = Query(..., min_length=1)):
    """Autocomplete units"""
    # TODO: Implement
    pass

@router.get("/catalog/geo/search")
async def search_geo(q: str = Query(..., min_length=1)):
    """Autocomplete geo zones"""
    # TODO: Implement
    pass

# MARKET SURVEY
@router.post("/market-survey")
async def create_market_survey():
    """Create market survey with propose-only pattern"""
    # TODO Session 3.1: Implement
    pass

@router.get("/market-survey/validation-queue")
async def get_validation_queue():
    """Get pending proposals for admin validation"""
    # TODO: Implement
    pass

@router.patch("/market-survey/{signal_id}/validate")
async def validate_signal(signal_id: str, action: str):
    """Validate or reject market signal (admin)"""
    # TODO: Implement
    pass

# MARKET INTELLIGENCE
@router.get("/market-intelligence/search")
async def search_market_intelligence(
    item: Optional[str] = None,
    geo: Optional[str] = None,
    vendor: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Search market signals with filters"""
    # TODO: Implement
    pass

@router.get("/market-intelligence/stats")
async def get_market_stats(item_id: str, geo_id: Optional[str] = None):
    """Get price statistics (avg, min, max, median)"""
    # TODO: Implement
    pass
