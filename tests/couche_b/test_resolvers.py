"""Tests for Couche B fuzzy resolution functions."""

import pytest

from src.couche_b.resolvers import resolve_item, resolve_vendor, resolve_zone

_INSERT_ZONES = """
    INSERT INTO geo_master (id, name, type, parent_id, created_at) VALUES
    ('zone-bamako-1', 'Bamako', 'city', NULL, '2026-02-13T20:00:00'),
    ('zone-kayes-1', 'Kayes', 'city', NULL, '2026-02-13T20:00:00'),
    ('zone-sikasso-1', 'Sikasso', 'city', NULL, '2026-02-13T20:00:00')
    ON CONFLICT (id) DO NOTHING
"""
_INSERT_VENDORS = """
    INSERT INTO vendors (name, zone_id, created_at) VALUES
    ('Marché Central', 'zone-bamako-1', '2026-02-13T20:00:00'),
    ('Boutique Kayes', 'zone-kayes-1', '2026-02-13T20:00:00')
    ON CONFLICT DO NOTHING
"""
_INSERT_ITEMS = """
    INSERT INTO items (description, category, unit_id, created_at) VALUES
    ('Riz local', 'Céréales', 1, '2026-02-13T20:00:00'),
    ('Tomate fraîche', 'Légumes', 1, '2026-02-13T20:00:00'),
    ('Mil', 'Céréales', 1, '2026-02-13T20:00:00')
    ON CONFLICT DO NOTHING
"""


@pytest.fixture
def seed_zones(db_cursor):
    """Seed test data for geo_master table."""
    db_cursor.execute(_INSERT_ZONES)
    yield


@pytest.fixture
def seed_vendors(db_cursor):
    """Seed test data for vendors table."""
    db_cursor.execute(_INSERT_VENDORS)
    yield


@pytest.fixture
def seed_items(db_cursor):
    """Seed test data for items table."""
    db_cursor.execute(_INSERT_ITEMS)
    yield


def test_resolve_zone_exact_match(seed_zones, db_cursor):
    """Test exact zone name match."""
    zone_id = resolve_zone("Bamako", cursor=db_cursor)
    assert zone_id == "zone-bamako-1", "Exact match should resolve correctly"

    zone_id = resolve_zone("Kayes", cursor=db_cursor)
    assert zone_id == "zone-kayes-1", "Exact match should resolve correctly"


def test_resolve_zone_fuzzy_match(seed_zones, db_cursor):
    """Test fuzzy match with realistic typo (similarity ≥60%)"""
    # Test avec typo plausible : lettre manquante
    zone_id = resolve_zone("Bamko", cursor=db_cursor)  # "Bamako" avec typo: manque 'a'
    assert zone_id == "zone-bamako-1", (
        "Should resolve 'Bamko' to 'Bamako' (typo tolerance)"
    )

    # Test avec typo plausible : lettre doublée
    zone_id = resolve_zone("Bamaako", cursor=db_cursor)  # "Bamako" avec double 'a'
    assert zone_id == "zone-bamako-1", (
        "Should resolve 'Bamaako' to 'Bamako' (typo tolerance)"
    )


def test_resolve_zone_no_match(seed_zones, db_cursor):
    """Test that unrelated or clearly non-matching names return None (Constitution: neutralité)."""
    # Noms sans lien avec les zones seedées → doivent retourner None
    zone_id = resolve_zone("Paris", cursor=db_cursor)
    assert zone_id is None, "Should not match unrelated name 'Paris'"

    zone_id = resolve_zone("NonExistentZoneXYZ", cursor=db_cursor)
    assert zone_id is None, "Should not match non-existent zone"


def test_resolve_zone_empty_string(seed_zones, db_cursor):
    """Test empty string handling."""
    assert resolve_zone("", cursor=db_cursor) is None, "Empty string should return None"
    assert resolve_zone("   ", cursor=db_cursor) is None, (
        "Whitespace-only should return None"
    )


def test_resolve_vendor_exact_match(seed_vendors, db_cursor):
    """Test exact vendor name match."""
    vendor_id = resolve_vendor("Marché Central", cursor=db_cursor)
    assert vendor_id is not None, "Exact match should resolve"

    vendor_id = resolve_vendor("Boutique Kayes", cursor=db_cursor)
    assert vendor_id is not None, "Exact match should resolve"


def test_resolve_vendor_fuzzy_match(seed_vendors, db_cursor):
    """Test fuzzy vendor name matching with typos."""
    # Missing accent
    vendor_id = resolve_vendor("Marche Central", cursor=db_cursor)
    assert vendor_id is not None, "Should match despite missing accent"


def test_resolve_vendor_no_match(seed_vendors, db_cursor):
    """Test vendor no match."""
    vendor_id = resolve_vendor("Boutique Inexistante", cursor=db_cursor)
    assert vendor_id is None, "Should not match non-existent vendor"


def test_resolve_vendor_empty_string(seed_vendors, db_cursor):
    """Test empty string handling for vendor."""
    assert resolve_vendor("", cursor=db_cursor) is None, (
        "Empty string should return None"
    )
    assert resolve_vendor("   ", cursor=db_cursor) is None, (
        "Whitespace-only should return None"
    )


def test_resolve_item_exact_match(seed_items, db_cursor):
    """Test exact item description match."""
    item_id = resolve_item("Riz local", cursor=db_cursor)
    assert item_id is not None, "Exact match should resolve"

    item_id = resolve_item("Mil", cursor=db_cursor)
    assert item_id is not None, "Exact match should resolve"


def test_resolve_item_fuzzy_match(seed_items, db_cursor):
    """Test fuzzy item description matching with typos."""
    # Typo: 'Ris' instead of 'Riz'
    item_id = resolve_item("Ris local", cursor=db_cursor)
    assert item_id is not None, "Should match despite typo"


def test_resolve_item_no_match(seed_items, db_cursor):
    """Test item no match."""
    item_id = resolve_item("Produit inexistant", cursor=db_cursor)
    assert item_id is None, "Should not match non-existent item"


def test_resolve_item_empty_string(seed_items, db_cursor):
    """Test empty string handling for item."""
    assert resolve_item("", cursor=db_cursor) is None, "Empty string should return None"
    assert resolve_item("   ", cursor=db_cursor) is None, (
        "Whitespace-only should return None"
    )
