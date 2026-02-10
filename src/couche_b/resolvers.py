"""
Couche B — Entity Resolvers (Canonical matching)
Constitution DMS V2.1 §5.2
"""

from typing import Optional
from sqlalchemy import text
from fuzzywuzzy import fuzz
import re
import unicodedata
from datetime import datetime
from uuid import uuid4

# TODO Session 2.1: Implémenter resolvers

def generate_ulid() -> str:
    """Generate sortable unique ID (timestamp + random)"""
    # TODO: Implement
    pass

def normalize_text(text: str) -> str:
    """Normalize text for matching (lowercase, remove accents, trim)"""
    # TODO: Implement
    pass

async def resolve_vendor(conn, vendor_name: str, threshold: int = 85) -> str:
    """
    Resolve vendor: canonical → alias → fuzzy → propose new
    Returns: vendor_id
    """
    # TODO: Implement
    # 1. Exact canonical match
    # 2. Exact alias match
    # 3. Fuzzy match (fuzzywuzzy)
    # 4. Create proposed if no match
    pass

async def resolve_item(conn, item_description: str, threshold: int = 85) -> str:
    """Resolve item: canonical → alias → fuzzy → propose new"""
    # TODO: Implement
    pass

async def resolve_unit(conn, unit_text: str) -> str:
    """Resolve unit: exact match only (no fuzzy for units)"""
    # TODO: Implement
    pass

async def resolve_geo(conn, location_name: str, threshold: int = 90) -> str:
    """Resolve geo: canonical → alias → fuzzy strict → propose new"""
    # TODO: Implement
    pass
