"""
Couche B — Market Intelligence Layer
Constitution DMS V2.1 §3-§5
"""

from .models import (
    vendors,
    vendor_aliases,
    vendor_events,
    items,
    item_aliases,
    units,
    unit_aliases,
    geo_master,
    geo_aliases,
    market_signals,
)

from .resolvers import (
    resolve_vendor,
    resolve_item,
    resolve_unit,
    resolve_geo,
)

from .routers import router as couche_b_router

__all__ = [
    # Tables
    "vendors",
    "vendor_aliases",
    "vendor_events",
    "items",
    "item_aliases",
    "units",
    "unit_aliases",
    "geo_master",
    "geo_aliases",
    "market_signals",
    # Resolvers
    "resolve_vendor",
    "resolve_item",
    "resolve_unit",
    "resolve_geo",
    # Router
    "couche_b_router",
]
