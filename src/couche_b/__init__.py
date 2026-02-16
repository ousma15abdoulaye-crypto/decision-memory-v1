"""Couche B: Market Memory & Fuzzy Resolution

Module for managing market data and fuzzy matching of vendors, items, and zones
using PostgreSQL pg_trgm extension.
"""

from .resolvers import resolve_item, resolve_vendor, resolve_zone

__all__ = ['resolve_vendor', 'resolve_item', 'resolve_zone']
