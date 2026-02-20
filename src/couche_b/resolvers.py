"""Fuzzy resolution functions for Couche B market memory.

Uses PostgreSQL pg_trgm extension for similarity-based matching.
Threshold: 60% (0.6) - balances typo tolerance with false positive prevention.
ADR-0003: no ORM; uses get_connection (psycopg).
"""

from __future__ import annotations

from typing import Any

from src.db import get_connection

# Production-safe threshold: tolerates 1-2 letter typos, rejects semantic variations
SIMILARITY_THRESHOLD = 0.6
# Lower threshold for zone matching (short names like "Bamko" -> "Bamako")
ZONE_SIMILARITY_THRESHOLD = 0.3


def _sql_psycopg(sql: str, params: dict[str, Any]) -> str:
    """Convert :name placeholders to %(name)s for psycopg."""
    for key in params:
        sql = sql.replace(":" + key, "%(" + key + ")s")
    return sql


def _run_one(
    cursor: Any | None, sql: str, params: dict[str, Any]
) -> dict[str, Any] | None:
    """Run query and return first row. If cursor is provided (tests), use it; else get_connection."""
    if cursor is not None:
        cursor.execute(_sql_psycopg(sql, params), params)
        row = cursor.fetchone()
        return dict(row) if row else None
    with get_connection() as conn:
        conn.execute(sql, params)
        return conn.fetchone()


def resolve_vendor(name: str, cursor: Any | None = None) -> int | None:
    """Resolve vendor name to vendor_id using fuzzy matching.

    Args:
        name: Vendor name to search (may contain typos)
        cursor: Optional psycopg cursor (for testing injection)

    Returns:
        vendor_id if match found with similarity >= 60%, None otherwise
    """
    if not name or not name.strip():
        return None
    sql = """
        SELECT id
        FROM vendors
        WHERE similarity(name, :search_name) > :threshold
        ORDER BY similarity(name, :search_name) DESC
        LIMIT 1
    """
    params = {"search_name": name.strip(), "threshold": SIMILARITY_THRESHOLD}
    row = _run_one(cursor, sql, params)
    return int(row["id"]) if row and row.get("id") is not None else None


def resolve_item(description: str, cursor: Any | None = None) -> int | None:
    """Resolve item description to item_id using fuzzy matching.

    Args:
        description: Item description to search (may contain typos)
        cursor: Optional psycopg cursor (for testing injection)

    Returns:
        item_id if match found with similarity >= 60%, None otherwise
    """
    if not description or not description.strip():
        return None
    sql = """
        SELECT id
        FROM items
        WHERE similarity(description, :search_desc) > :threshold
        ORDER BY similarity(description, :search_desc) DESC
        LIMIT 1
    """
    params = {
        "search_desc": description.strip(),
        "threshold": SIMILARITY_THRESHOLD,
    }
    row = _run_one(cursor, sql, params)
    return int(row["id"]) if row and row.get("id") is not None else None


def resolve_zone(name: str, cursor: Any | None = None) -> str | None:
    """Resolve zone name to zone_id using fuzzy matching.

    Args:
        name: Zone name to search (may contain typos)
        cursor: Optional psycopg cursor (for testing injection)

    Returns:
        zone_id if match found with similarity >= 60%, None otherwise
    """
    if not name or not name.strip():
        return None
    sql = """
        SELECT id
        FROM geo_master
        WHERE similarity(name, :search_name) > :threshold
        ORDER BY similarity(name, :search_name) DESC
        LIMIT 1
    """
    params = {"search_name": name.strip(), "threshold": ZONE_SIMILARITY_THRESHOLD}
    row = _run_one(cursor, sql, params)
    return str(row["id"]) if row and row.get("id") is not None else None
