"""Tests for Couche B fuzzy resolution functions."""

import pytest
from src.couche_b.resolvers import resolve_vendor, resolve_item, resolve_zone


@pytest.fixture
def seed_zones(db_session):
    """Seed test data for geo_master table."""
    from sqlalchemy import text

    # Insert test zones (already seeded in migration, but ensure they exist)
    db_session.execute(text("""
        INSERT INTO geo_master (id, name, type, parent_id, created_at) VALUES
        ('zone-bamako-1', 'Bamako', 'city', NULL, '2026-02-13T20:00:00'),
        ('zone-kayes-1', 'Kayes', 'city', NULL, '2026-02-13T20:00:00'),
        ('zone-sikasso-1', 'Sikasso', 'city', NULL, '2026-02-13T20:00:00')
        ON CONFLICT (id) DO NOTHING
    """))
    db_session.commit()
    yield
    # Cleanup is handled by transaction rollback in conftest


@pytest.fixture
def seed_vendors(db_session):
    """Seed test data for vendors table."""
    from sqlalchemy import text

    db_session.execute(text("""
        INSERT INTO vendors (name, zone_id, created_at) VALUES
        ('Marché Central', 'zone-bamako-1', '2026-02-13T20:00:00'),
        ('Boutique Kayes', 'zone-kayes-1', '2026-02-13T20:00:00')
        ON CONFLICT DO NOTHING
    """))
    db_session.commit()
    yield


@pytest.fixture
def seed_items(db_session):
    """Seed test data for items table."""
    from sqlalchemy import text

    db_session.execute(text("""
        INSERT INTO items (description, category, unit_id, created_at) VALUES
        ('Riz local', 'Céréales', 1, '2026-02-13T20:00:00'),
        ('Tomate fraîche', 'Légumes', 1, '2026-02-13T20:00:00'),
        ('Mil', 'Céréales', 1, '2026-02-13T20:00:00')
        ON CONFLICT DO NOTHING
    """))
    db_session.commit()
    yield


def test_resolve_zone_exact_match(seed_zones):
    """Test exact zone name match."""
    zone_id = resolve_zone("Bamako")
    assert zone_id == "zone-bamako-1", "Exact match should resolve correctly"

    zone_id = resolve_zone("Kayes")
    assert zone_id == "zone-kayes-1", "Exact match should resolve correctly"


def test_resolve_zone_fuzzy_match(seed_zones):
    """Test fuzzy match with realistic typo (similarity ≥60%)"""
    # Test avec typo plausible : lettre manquante
    zone_id = resolve_zone("Bamko")  # "Bamako" avec typo: manque 'a'
    assert (
        zone_id == "zone-bamako-1"
    ), "Should resolve 'Bamko' to 'Bamako' (typo tolerance)"

    # Test avec typo plausible : lettre doublée
    zone_id = resolve_zone("Bamaako")  # "Bamako" avec double 'a'
    assert (
        zone_id == "zone-bamako-1"
    ), "Should resolve 'Bamaako' to 'Bamako' (typo tolerance)"


def test_resolve_zone_no_match(seed_zones):
    """Test that semantic variations or low similarity return None."""
    # Semantic variation: "Bamako City" has ~44% similarity, below 60% threshold
    zone_id = resolve_zone("Bamako City")
    assert zone_id is None, "Should not match 'Bamako City' (similarity too low)"

    # Completely different name
    zone_id = resolve_zone("Paris")
    assert zone_id is None, "Should not match unrelated name"


def test_resolve_zone_empty_string(seed_zones):
    """Test empty string handling."""
    assert resolve_zone("") is None, "Empty string should return None"
    assert resolve_zone("   ") is None, "Whitespace-only should return None"


def test_resolve_vendor_exact_match(seed_vendors):
    """Test exact vendor name match."""
    vendor_id = resolve_vendor("Marché Central")
    assert vendor_id is not None, "Exact match should resolve"

    vendor_id = resolve_vendor("Boutique Kayes")
    assert vendor_id is not None, "Exact match should resolve"


def test_resolve_vendor_fuzzy_match(seed_vendors):
    """Test fuzzy vendor name matching with typos."""
    # Missing accent
    vendor_id = resolve_vendor("Marche Central")
    assert vendor_id is not None, "Should match despite missing accent"


def test_resolve_vendor_no_match(seed_vendors):
    """Test vendor no match."""
    vendor_id = resolve_vendor("Boutique Inexistante")
    assert vendor_id is None, "Should not match non-existent vendor"


def test_resolve_vendor_empty_string(seed_vendors):
    """Test empty string handling for vendor."""
    assert resolve_vendor("") is None, "Empty string should return None"
    assert resolve_vendor("   ") is None, "Whitespace-only should return None"


def test_resolve_item_exact_match(seed_items):
    """Test exact item description match."""
    item_id = resolve_item("Riz local")
    assert item_id is not None, "Exact match should resolve"

    item_id = resolve_item("Mil")
    assert item_id is not None, "Exact match should resolve"


def test_resolve_item_fuzzy_match(seed_items):
    """Test fuzzy item description matching with typos."""
    # Typo: 'Ris' instead of 'Riz'
    item_id = resolve_item("Ris local")
    assert item_id is not None, "Should match despite typo"


def test_resolve_item_no_match(seed_items):
    """Test item no match."""
    item_id = resolve_item("Produit inexistant")
    assert item_id is None, "Should not match non-existent item"


def test_resolve_item_empty_string(seed_items):
    """Test empty string handling for item."""
    assert resolve_item("") is None, "Empty string should return None"
    assert resolve_item("   ") is None, "Whitespace-only should return None"
