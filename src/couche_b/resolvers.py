"""Fuzzy resolution functions for Couche B market memory.

Uses PostgreSQL pg_trgm extension for similarity-based matching.
Threshold: 60% (0.6) - balances typo tolerance with false positive prevention.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db import get_session

# Production-safe threshold: tolerates 1-2 letter typos, rejects semantic variations
SIMILARITY_THRESHOLD = 0.6
# Lower threshold for zone matching (short names like "Bamko" -> "Bamako")
ZONE_SIMILARITY_THRESHOLD = 0.3


def resolve_vendor(name: str, session: Session | None = None) -> int | None:
    """Resolve vendor name to vendor_id using fuzzy matching.

    Args:
        name: Vendor name to search (may contain typos)
        session: Optional SQLAlchemy session (for testing)

    Returns:
        vendor_id if match found with similarity >= 60%, None otherwise
    """
    if not name or not name.strip():
        return None

    def _query(s: Session) -> int | None:
        result = s.execute(
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

    if session is not None:
        return _query(session)

    with get_session() as s:
        return _query(s)


def resolve_item(description: str, session: Session | None = None) -> int | None:
    """Resolve item description to item_id using fuzzy matching.

    Args:
        description: Item description to search (may contain typos)
        session: Optional SQLAlchemy session (for testing)

    Returns:
        item_id if match found with similarity >= 60%, None otherwise
    """
    if not description or not description.strip():
        return None

    def _query(s: Session) -> int | None:
        result = s.execute(
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

    if session is not None:
        return _query(session)

    with get_session() as s:
        return _query(s)


def resolve_zone(name: str, session: Session | None = None) -> str | None:
    """Resolve zone name to zone_id using fuzzy matching.

    Args:
        name: Zone name to search (may contain typos)
        session: Optional SQLAlchemy session (for testing)

    Returns:
        zone_id if match found with similarity >= 60%, None otherwise
    """
    if not name or not name.strip():
        return None

    def _query(s: Session) -> str | None:
        result = s.execute(
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

    if session is not None:
        return _query(session)

    with get_session() as s:
        return _query(s)