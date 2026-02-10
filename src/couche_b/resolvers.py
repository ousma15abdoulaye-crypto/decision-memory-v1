"""
Couche B — Entity Resolvers (Canonical matching)
Constitution DMS V2.1 §5.2
"""

from typing import Optional
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncConnection
from fuzzywuzzy import fuzz
import unicodedata
import secrets
from datetime import datetime


def generate_ulid() -> str:
    """Generate sortable unique ID (timestamp + random)
    
    Returns:
        20-character sortable unique ID
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')  # 14 chars
    random_part = secrets.token_hex(3).upper()  # 6 chars
    return f"{timestamp}{random_part}"


def normalize_text(text: str) -> str:
    """Normalize text for matching (lowercase, remove accents, trim)
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Remove accents
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    
    # Lowercase and strip
    text = text.lower().strip()
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text


async def resolve_vendor(conn: AsyncConnection, vendor_name: str, threshold: int = 85) -> str:
    """
    Resolve vendor: canonical → alias → fuzzy → propose new
    
    Args:
        conn: Async database connection
        vendor_name: Vendor name to resolve
        threshold: Fuzzy matching threshold (default 85%)
        
    Returns:
        vendor_id (existing or newly created proposed vendor)
    """
    from src.couche_b.models import vendors, vendor_aliases, vendor_events
    
    normalized_input = normalize_text(vendor_name)
    
    # Step 1: Exact canonical match
    stmt = select(vendors.c.vendor_id).where(
        vendors.c.status.in_(['active', 'proposed'])
    )
    result = await conn.execute(stmt)
    existing_vendors = result.fetchall()
    
    for row in existing_vendors:
        stmt = select(vendors).where(vendors.c.vendor_id == row.vendor_id)
        vendor_result = await conn.execute(stmt)
        vendor = vendor_result.fetchone()
        if vendor and normalize_text(vendor.canonical_name) == normalized_input:
            return vendor.vendor_id
    
    # Step 2: Exact alias match
    stmt = select(vendor_aliases.c.vendor_id, vendor_aliases.c.alias_name).where(
        vendor_aliases.c.vendor_id.in_([row.vendor_id for row in existing_vendors])
    )
    result = await conn.execute(stmt)
    aliases = result.fetchall()
    
    for alias in aliases:
        if normalize_text(alias.alias_name) == normalized_input:
            return alias.vendor_id
    
    # Step 3: Fuzzy match against canonical names
    best_match_id = None
    best_score = 0
    
    for row in existing_vendors:
        stmt = select(vendors).where(vendors.c.vendor_id == row.vendor_id)
        vendor_result = await conn.execute(stmt)
        vendor = vendor_result.fetchone()
        if vendor:
            score = fuzz.ratio(normalized_input, normalize_text(vendor.canonical_name))
            if score >= threshold and score > best_score:
                best_score = score
                best_match_id = vendor.vendor_id
    
    if best_match_id:
        # Create alias for fuzzy match
        alias_id = generate_ulid()
        stmt = insert(vendor_aliases).values(
            alias_id=alias_id,
            vendor_id=best_match_id,
            alias_name=vendor_name,
            confidence='ESTIMATED'
        )
        await conn.execute(stmt)
        return best_match_id
    
    # Step 4: Create proposed vendor
    new_vendor_id = generate_ulid()
    stmt = insert(vendors).values(
        vendor_id=new_vendor_id,
        canonical_name=vendor_name,
        status='proposed'
    )
    await conn.execute(stmt)
    
    # Create event for new vendor
    event_id = generate_ulid()
    stmt = insert(vendor_events).values(
        event_id=event_id,
        vendor_id=new_vendor_id,
        event_type='status_change',
        event_date=datetime.now().date(),
        details={'action': 'created', 'original_name': vendor_name}
    )
    await conn.execute(stmt)
    
    return new_vendor_id


async def resolve_item(conn: AsyncConnection, item_description: str, threshold: int = 85) -> str:
    """Resolve item: canonical → alias → fuzzy → propose new
    
    Args:
        conn: Async database connection
        item_description: Item description to resolve
        threshold: Fuzzy matching threshold (default 85%)
        
    Returns:
        item_id (existing or newly created proposed item)
    """
    from src.couche_b.models import items, item_aliases
    
    normalized_input = normalize_text(item_description)
    
    # Step 1: Exact canonical match
    stmt = select(items.c.item_id).where(
        items.c.status.in_(['active', 'proposed'])
    )
    result = await conn.execute(stmt)
    existing_items = result.fetchall()
    
    for row in existing_items:
        stmt = select(items).where(items.c.item_id == row.item_id)
        item_result = await conn.execute(stmt)
        item = item_result.fetchone()
        if item and normalize_text(item.canonical_description) == normalized_input:
            return item.item_id
    
    # Step 2: Exact alias match
    stmt = select(item_aliases.c.item_id, item_aliases.c.alias_description).where(
        item_aliases.c.item_id.in_([row.item_id for row in existing_items])
    )
    result = await conn.execute(stmt)
    aliases = result.fetchall()
    
    for alias in aliases:
        if normalize_text(alias.alias_description) == normalized_input:
            return alias.item_id
    
    # Step 3: Fuzzy match against canonical descriptions
    best_match_id = None
    best_score = 0
    
    for row in existing_items:
        stmt = select(items).where(items.c.item_id == row.item_id)
        item_result = await conn.execute(stmt)
        item = item_result.fetchone()
        if item:
            score = fuzz.ratio(normalized_input, normalize_text(item.canonical_description))
            if score >= threshold and score > best_score:
                best_score = score
                best_match_id = item.item_id
    
    if best_match_id:
        # Create alias for fuzzy match
        alias_id = generate_ulid()
        stmt = insert(item_aliases).values(
            alias_id=alias_id,
            item_id=best_match_id,
            alias_description=item_description,
            confidence='ESTIMATED'
        )
        await conn.execute(stmt)
        return best_match_id
    
    # Step 4: Create proposed item
    new_item_id = generate_ulid()
    stmt = insert(items).values(
        item_id=new_item_id,
        canonical_description=item_description,
        status='proposed'
    )
    await conn.execute(stmt)
    
    return new_item_id


async def resolve_unit(conn: AsyncConnection, unit_text: str) -> str:
    """Resolve unit: exact match only (no fuzzy for units)
    
    Args:
        conn: Async database connection
        unit_text: Unit text to resolve
        
    Returns:
        unit_id
        
    Raises:
        ValueError: If unit not found
    """
    from src.couche_b.models import units, unit_aliases
    
    normalized_input = normalize_text(unit_text)
    
    # Step 1: Exact canonical symbol match
    stmt = select(units.c.unit_id).where(
        units.c.canonical_symbol == unit_text
    )
    result = await conn.execute(stmt)
    unit = result.fetchone()
    if unit:
        return unit.unit_id
    
    # Step 2: Exact canonical name match (normalized)
    stmt = select(units)
    result = await conn.execute(stmt)
    all_units = result.fetchall()
    
    for unit in all_units:
        if normalize_text(unit.canonical_name) == normalized_input:
            return unit.unit_id
    
    # Step 3: Exact alias match
    stmt = select(unit_aliases.c.unit_id, unit_aliases.c.alias_symbol, unit_aliases.c.alias_name)
    result = await conn.execute(stmt)
    aliases = result.fetchall()
    
    for alias in aliases:
        if alias.alias_symbol and alias.alias_symbol == unit_text:
            return alias.unit_id
        if alias.alias_name and normalize_text(alias.alias_name) == normalized_input:
            return alias.unit_id
    
    # No fuzzy matching for units - raise error
    raise ValueError(f"Unit '{unit_text}' not found. Units must match exactly.")


async def resolve_geo(conn: AsyncConnection, location_name: str, threshold: int = 90) -> str:
    """Resolve geo: canonical → alias → fuzzy strict → propose new
    
    Args:
        conn: Async database connection
        location_name: Location name to resolve
        threshold: Fuzzy matching threshold (default 90%, stricter than other entities)
        
    Returns:
        geo_id (existing or newly created proposed geo)
    """
    from src.couche_b.models import geo_master, geo_aliases
    
    normalized_input = normalize_text(location_name)
    
    # Step 1: Exact canonical match
    stmt = select(geo_master.c.geo_id).where(
        geo_master.c.status.in_(['active', 'proposed'])
    )
    result = await conn.execute(stmt)
    existing_geos = result.fetchall()
    
    for row in existing_geos:
        stmt = select(geo_master).where(geo_master.c.geo_id == row.geo_id)
        geo_result = await conn.execute(stmt)
        geo = geo_result.fetchone()
        if geo and normalize_text(geo.canonical_name) == normalized_input:
            return geo.geo_id
    
    # Step 2: Exact alias match
    stmt = select(geo_aliases.c.geo_id, geo_aliases.c.alias_name).where(
        geo_aliases.c.geo_id.in_([row.geo_id for row in existing_geos])
    )
    result = await conn.execute(stmt)
    aliases = result.fetchall()
    
    for alias in aliases:
        if normalize_text(alias.alias_name) == normalized_input:
            return alias.geo_id
    
    # Step 3: Fuzzy match with strict threshold (90%)
    best_match_id = None
    best_score = 0
    
    for row in existing_geos:
        stmt = select(geo_master).where(geo_master.c.geo_id == row.geo_id)
        geo_result = await conn.execute(stmt)
        geo = geo_result.fetchone()
        if geo:
            score = fuzz.ratio(normalized_input, normalize_text(geo.canonical_name))
            if score >= threshold and score > best_score:
                best_score = score
                best_match_id = geo.geo_id
    
    if best_match_id:
        # Create alias for fuzzy match
        alias_id = generate_ulid()
        stmt = insert(geo_aliases).values(
            alias_id=alias_id,
            geo_id=best_match_id,
            alias_name=location_name,
            confidence='ESTIMATED'
        )
        await conn.execute(stmt)
        return best_match_id
    
    # Step 4: Create proposed geo
    new_geo_id = generate_ulid()
    stmt = insert(geo_master).values(
        geo_id=new_geo_id,
        canonical_name=location_name,
        geo_type='city',  # Default to city
        status='proposed'
    )
    await conn.execute(stmt)
    
    return new_geo_id
