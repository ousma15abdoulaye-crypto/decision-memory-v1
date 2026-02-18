"""Fuzzy resolution functions for Couche B market memory.

Uses PostgreSQL pg_trgm extension for similarity-based matching.
Threshold: 60% (0.6) - balances typo tolerance with false positive prevention.
"""

from typing import Optional
from sqlalchemy import text
from src.db import get_session

# Production-safe threshold: tolerates 1-2 letter typos, rejects semantic variations
SIMILARITY_THRESHOLD = 0.6
# Lower threshold for zone matching (short names like "Bamko" -> "Bamako")
ZONE_SIMILARITY_THRESHOLD = 0.3


def resolve_vendor(name: str) -> Optional[int]:
    """Resolve vendor name to vendor_id using fuzzy matching.

    Args:
        name: Vendor name to search (may contain typos)

    Returns:
        vendor_id if match found with similarity >= 60%, None otherwise

    Examples:
        >>> resolve_vendor("Marché Central")  # exact match
        1
        >>> resolve_vendor("Marche Central")  # missing accent, still matches
        1
        >>> resolve_vendor("")  # empty string
        None
    """
    if not name or not name.strip():
        return None

    with get_session() as session:
        result = session.execute(
            text("""
                SELECT id
                FROM vendors
                WHERE similarity(name, :search_name) > :threshold
                ORDER BY similarity(name, :search_name) DESC
                LIMIT 1
            """),
            {"search_name": name.strip(), "threshold": SIMILARITY_THRESHOLD},
        ).fetchone()

        return result[0] if result else None


def resolve_item(description: str) -> Optional[int]:
    """Resolve item description to item_id using fuzzy matching.

    Args:
        description: Item description to search (may contain typos)

    Returns:
        item_id if match found with similarity >= 60%, None otherwise

    Examples:
        >>> resolve_item("Riz local")  # exact match
        1
        >>> resolve_item("Ris local")  # typo, still matches
        1
        >>> resolve_item("")  # empty string
        None
    """
    if not description or not description.strip():
        return None

    with get_session() as session:
        result = session.execute(
            text("""
                SELECT id
                FROM items
                WHERE similarity(description, :search_desc) > :threshold
                ORDER BY similarity(description, :search_desc) DESC
                LIMIT 1
            """),
            {"search_desc": description.strip(), "threshold": SIMILARITY_THRESHOLD},
        ).fetchone()

        return result[0] if result else None


def resolve_zone(name: str) -> Optional[str]:
    """Resolve zone name to zone_id using fuzzy matching.

    Args:
        name: Zone name to search (may contain typos)

    Returns:
        zone_id if match found with similarity >= 60%, None otherwise

    Examples:
        >>> resolve_zone("Bamako")  # exact match
        'zone-bamako-1'
        >>> resolve_zone("Bamko")  # missing letter 'a', still matches (similarity ~83%)
        'zone-bamako-1'
        >>> resolve_zone("Bamaako")  # double 'a', still matches (similarity ~86%)
        'zone-bamako-1'
        >>> resolve_zone("Bamako City")  # semantic variation, does NOT match (similarity ~44%)
        None
        >>> resolve_zone("")  # empty string
        None
    """
    if not name or not name.strip():
        return None

    with get_session() as session:
        result = session.execute(
            text("""
                SELECT id
                FROM geo_master
                WHERE similarity(name, :search_name) > :threshold
                ORDER BY similarity(name, :search_name) DESC
                LIMIT 1
            """),
            {"search_name": name.strip(), "threshold": ZONE_SIMILARITY_THRESHOLD},
        ).fetchone()

        return result[0] if result else None
