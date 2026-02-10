"""
Couche B — Seed Data Mali
Constitution DMS V2.1 §4.4 (Geo) + §4.3 (Units)
"""

from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import create_async_engine
from src.db import DATABASE_URL, metadata
from src.couche_b.resolvers import generate_ulid
import asyncio


async def seed_couche_b():
    """
    Seed Couche B with Mali standard data:
    - 8 geo zones (Bamako, Gao, Tombouctou, Mopti, Sikasso, Ségou, Kayes, Koulikoro)
    - 9 standard units (kg, tonne, L, m³, m, m², pièce, sac, carton)
    - 3 common vendors (SOGELEC, SOMAPEP, COVEC)
    - 5 common items (Ciment, Fer 12mm, Riz, Huile, Sucre)
    """
    from src.couche_b.models import geo_master, units, unit_aliases, vendors, items
    
    # Create async engine if using PostgreSQL
    if DATABASE_URL.startswith("postgresql"):
        async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(async_url, echo=False)
    else:
        # For SQLite, we'll use sync operations
        from src.db import engine as sync_engine
        print("⚠️  Using SQLite - running in sync mode")
        
        # Sync version for SQLite
        with sync_engine.begin() as conn:
            # Create schema if not exists
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS couche_b"))
            
            # Seed geo zones - Mali
            geo_data = [
                {'geo_id': generate_ulid(), 'canonical_name': 'Bamako', 'geo_type': 'city', 'status': 'active'},
                {'geo_id': generate_ulid(), 'canonical_name': 'Gao', 'geo_type': 'city', 'status': 'active'},
                {'geo_id': generate_ulid(), 'canonical_name': 'Tombouctou', 'geo_type': 'city', 'status': 'active'},
                {'geo_id': generate_ulid(), 'canonical_name': 'Mopti', 'geo_type': 'city', 'status': 'active'},
                {'geo_id': generate_ulid(), 'canonical_name': 'Sikasso', 'geo_type': 'city', 'status': 'active'},
                {'geo_id': generate_ulid(), 'canonical_name': 'Ségou', 'geo_type': 'city', 'status': 'active'},
                {'geo_id': generate_ulid(), 'canonical_name': 'Kayes', 'geo_type': 'city', 'status': 'active'},
                {'geo_id': generate_ulid(), 'canonical_name': 'Koulikoro', 'geo_type': 'city', 'status': 'active'},
            ]
            
            for geo in geo_data:
                # Check if exists
                existing = conn.execute(
                    select(geo_master.c.geo_id).where(geo_master.c.canonical_name == geo['canonical_name'])
                ).fetchone()
                if not existing:
                    conn.execute(insert(geo_master).values(**geo))
            
            # Seed units
            units_data = [
                {'unit_id': generate_ulid(), 'canonical_symbol': 'kg', 'canonical_name': 'kilogramme', 'unit_type': 'weight'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 't', 'canonical_name': 'tonne', 'unit_type': 'weight'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 'L', 'canonical_name': 'litre', 'unit_type': 'volume'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 'm³', 'canonical_name': 'mètre cube', 'unit_type': 'volume'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 'm', 'canonical_name': 'mètre', 'unit_type': 'length'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 'm²', 'canonical_name': 'mètre carré', 'unit_type': 'area'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 'pce', 'canonical_name': 'pièce', 'unit_type': 'count'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 'sac', 'canonical_name': 'sac', 'unit_type': 'package'},
                {'unit_id': generate_ulid(), 'canonical_symbol': 'crt', 'canonical_name': 'carton', 'unit_type': 'package'},
            ]
            
            for unit in units_data:
                # Check if exists
                existing = conn.execute(
                    select(units.c.unit_id).where(units.c.canonical_symbol == unit['canonical_symbol'])
                ).fetchone()
                if not existing:
                    unit_id = unit['unit_id']
                    conn.execute(insert(units).values(**unit))
                    
                    # Add aliases
                    if unit['canonical_symbol'] == 'kg':
                        conn.execute(insert(unit_aliases).values(
                            alias_id=generate_ulid(),
                            unit_id=unit_id,
                            alias_symbol='kilo',
                            alias_name='kilogramme'
                        ))
            
            # Seed vendors
            vendors_data = [
                {'vendor_id': generate_ulid(), 'canonical_name': 'SOGELEC', 'status': 'active'},
                {'vendor_id': generate_ulid(), 'canonical_name': 'SOMAPEP', 'status': 'active'},
                {'vendor_id': generate_ulid(), 'canonical_name': 'COVEC', 'status': 'active'},
            ]
            
            for vendor in vendors_data:
                # Check if exists
                existing = conn.execute(
                    select(vendors.c.vendor_id).where(vendors.c.canonical_name == vendor['canonical_name'])
                ).fetchone()
                if not existing:
                    conn.execute(insert(vendors).values(**vendor))
            
            # Seed items
            items_data = [
                {'item_id': generate_ulid(), 'canonical_description': 'Ciment 50kg', 'category': 'construction', 'status': 'active'},
                {'item_id': generate_ulid(), 'canonical_description': 'Fer 12mm (barre)', 'category': 'construction', 'status': 'active'},
                {'item_id': generate_ulid(), 'canonical_description': 'Riz importé', 'category': 'alimentation', 'status': 'active'},
                {'item_id': generate_ulid(), 'canonical_description': 'Huile végétale', 'category': 'alimentation', 'status': 'active'},
                {'item_id': generate_ulid(), 'canonical_description': 'Sucre cristallisé', 'category': 'alimentation', 'status': 'active'},
            ]
            
            for item in items_data:
                # Check if exists
                existing = conn.execute(
                    select(items.c.item_id).where(items.c.canonical_description == item['canonical_description'])
                ).fetchone()
                if not existing:
                    conn.execute(insert(items).values(**item))
        
        print("✅ Couche B seeded (SQLite mode)")
        return
    
    # PostgreSQL async version
    async with engine.begin() as conn:
        # Import text for raw SQL
        from sqlalchemy import text
        
        # Create schema if not exists
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS couche_b"))
        
        # Seed geo zones - Mali
        geo_data = [
            {'geo_id': generate_ulid(), 'canonical_name': 'Bamako', 'geo_type': 'city', 'status': 'active'},
            {'geo_id': generate_ulid(), 'canonical_name': 'Gao', 'geo_type': 'city', 'status': 'active'},
            {'geo_id': generate_ulid(), 'canonical_name': 'Tombouctou', 'geo_type': 'city', 'status': 'active'},
            {'geo_id': generate_ulid(), 'canonical_name': 'Mopti', 'geo_type': 'city', 'status': 'active'},
            {'geo_id': generate_ulid(), 'canonical_name': 'Sikasso', 'geo_type': 'city', 'status': 'active'},
            {'geo_id': generate_ulid(), 'canonical_name': 'Ségou', 'geo_type': 'city', 'status': 'active'},
            {'geo_id': generate_ulid(), 'canonical_name': 'Kayes', 'geo_type': 'city', 'status': 'active'},
            {'geo_id': generate_ulid(), 'canonical_name': 'Koulikoro', 'geo_type': 'city', 'status': 'active'},
        ]
        
        for geo in geo_data:
            # Check if exists
            result = await conn.execute(
                select(geo_master.c.geo_id).where(geo_master.c.canonical_name == geo['canonical_name'])
            )
            existing = result.fetchone()
            if not existing:
                await conn.execute(insert(geo_master).values(**geo))
        
        # Seed units
        units_data = [
            {'unit_id': generate_ulid(), 'canonical_symbol': 'kg', 'canonical_name': 'kilogramme', 'unit_type': 'weight'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 't', 'canonical_name': 'tonne', 'unit_type': 'weight'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 'L', 'canonical_name': 'litre', 'unit_type': 'volume'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 'm³', 'canonical_name': 'mètre cube', 'unit_type': 'volume'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 'm', 'canonical_name': 'mètre', 'unit_type': 'length'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 'm²', 'canonical_name': 'mètre carré', 'unit_type': 'area'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 'pce', 'canonical_name': 'pièce', 'unit_type': 'count'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 'sac', 'canonical_name': 'sac', 'unit_type': 'package'},
            {'unit_id': generate_ulid(), 'canonical_symbol': 'crt', 'canonical_name': 'carton', 'unit_type': 'package'},
        ]
        
        for unit in units_data:
            # Check if exists
            result = await conn.execute(
                select(units.c.unit_id).where(units.c.canonical_symbol == unit['canonical_symbol'])
            )
            existing = result.fetchone()
            if not existing:
                unit_id = unit['unit_id']
                await conn.execute(insert(units).values(**unit))
                
                # Add aliases
                if unit['canonical_symbol'] == 'kg':
                    await conn.execute(insert(unit_aliases).values(
                        alias_id=generate_ulid(),
                        unit_id=unit_id,
                        alias_symbol='kilo',
                        alias_name='kilogramme'
                    ))
        
        # Seed vendors
        vendors_data = [
            {'vendor_id': generate_ulid(), 'canonical_name': 'SOGELEC', 'status': 'active'},
            {'vendor_id': generate_ulid(), 'canonical_name': 'SOMAPEP', 'status': 'active'},
            {'vendor_id': generate_ulid(), 'canonical_name': 'COVEC', 'status': 'active'},
        ]
        
        for vendor in vendors_data:
            # Check if exists
            result = await conn.execute(
                select(vendors.c.vendor_id).where(vendors.c.canonical_name == vendor['canonical_name'])
            )
            existing = result.fetchone()
            if not existing:
                await conn.execute(insert(vendors).values(**vendor))
        
        # Seed items
        items_data = [
            {'item_id': generate_ulid(), 'canonical_description': 'Ciment 50kg', 'category': 'construction', 'status': 'active'},
            {'item_id': generate_ulid(), 'canonical_description': 'Fer 12mm (barre)', 'category': 'construction', 'status': 'active'},
            {'item_id': generate_ulid(), 'canonical_description': 'Riz importé', 'category': 'alimentation', 'status': 'active'},
            {'item_id': generate_ulid(), 'canonical_description': 'Huile végétale', 'category': 'alimentation', 'status': 'active'},
            {'item_id': generate_ulid(), 'canonical_description': 'Sucre cristallisé', 'category': 'alimentation', 'status': 'active'},
        ]
        
        for item in items_data:
            # Check if exists
            result = await conn.execute(
                select(items.c.item_id).where(items.c.canonical_description == item['canonical_description'])
            )
            existing = result.fetchone()
            if not existing:
                await conn.execute(insert(items).values(**item))
    
    await engine.dispose()
    print("✅ Couche B seeded (PostgreSQL mode)")


if __name__ == "__main__":
    asyncio.run(seed_couche_b())

