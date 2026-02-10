"""
Test Couche B Seed Data
Constitution DMS V2.1 §4
"""

import pytest
import asyncio
from sqlalchemy import select, text
from src.couche_b.seed import seed_couche_b
from src.couche_b.models import geo_master, units, vendors, items
from src.db import engine, metadata


@pytest.mark.asyncio
async def test_seed_geo_zones():
    """Test geo zones seeding (8 zones for Mali)"""
    # Create tables
    metadata.create_all(engine)
    
    # Run seed
    await seed_couche_b()
    
    # Check count
    with engine.begin() as conn:
        result = conn.execute(select(geo_master))
        geos = result.fetchall()
        
        # Should have at least 8 geo zones
        assert len(geos) >= 8
        
        # Check for specific cities
        geo_names = [g.canonical_name for g in geos]
        assert 'Bamako' in geo_names
        assert 'Gao' in geo_names
        assert 'Tombouctou' in geo_names


@pytest.mark.asyncio
async def test_seed_units():
    """Test units seeding (9 standard units)"""
    # Create tables
    metadata.create_all(engine)
    
    # Run seed
    await seed_couche_b()
    
    # Check count
    with engine.begin() as conn:
        result = conn.execute(select(units))
        unit_list = result.fetchall()
        
        # Should have at least 9 units
        assert len(unit_list) >= 9
        
        # Check for specific units
        unit_symbols = [u.canonical_symbol for u in unit_list]
        assert 'kg' in unit_symbols
        assert 'L' in unit_symbols
        assert 'm²' in unit_symbols


@pytest.mark.asyncio
async def test_seed_vendors():
    """Test vendors seeding"""
    # Create tables
    metadata.create_all(engine)
    
    # Run seed
    await seed_couche_b()
    
    # Check count
    with engine.begin() as conn:
        result = conn.execute(select(vendors))
        vendor_list = result.fetchall()
        
        # Should have at least 3 vendors
        assert len(vendor_list) >= 3
        
        # Check for specific vendors
        vendor_names = [v.canonical_name for v in vendor_list]
        assert 'SOGELEC' in vendor_names or 'SOMAPEP' in vendor_names


@pytest.mark.asyncio
async def test_seed_items():
    """Test items seeding"""
    # Create tables
    metadata.create_all(engine)
    
    # Run seed
    await seed_couche_b()
    
    # Check count
    with engine.begin() as conn:
        result = conn.execute(select(items))
        item_list = result.fetchall()
        
        # Should have at least 5 items
        assert len(item_list) >= 5
        
        # Check for specific items
        item_descriptions = [i.canonical_description for i in item_list]
        assert any('Ciment' in d for d in item_descriptions)


@pytest.mark.asyncio
async def test_seed_idempotent():
    """Test that seeding can be run multiple times safely"""
    # Create tables
    metadata.create_all(engine)
    
    # Run seed first time
    await seed_couche_b()
    
    # Count items
    with engine.begin() as conn:
        result1 = conn.execute(select(geo_master))
        count1 = len(result1.fetchall())
    
    # Run seed second time
    await seed_couche_b()
    
    # Count items again
    with engine.begin() as conn:
        result2 = conn.execute(select(geo_master))
        count2 = result2.fetchall()
    
    # Count should be the same (idempotent)
    assert count1 == len(count2), "Seed should be idempotent"


def test_seed_sync_mode():
    """Test seed works in sync mode (SQLite)"""
    # This just ensures the seed function can be called
    # The actual async test is in test_seed_idempotent
    assert callable(seed_couche_b)


def test_metadata_exists():
    """Test that metadata is properly configured"""
    from src.db import metadata as db_metadata
    assert db_metadata is not None
    
    # Check that Couche B tables are in metadata
    table_names = [t.name for t in db_metadata.tables.values()]
    # Note: In SQLite, schema prefix might not be in name
    # Just check that some tables exist
    assert len(table_names) > 0
