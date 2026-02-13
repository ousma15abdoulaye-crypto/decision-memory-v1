"""Add Couche B market memory tables with pg_trgm fuzzy matching

Revision ID: 005_add_couche_b
Revises: 004_users_rbac
Create Date: 2026-02-13 20:00:00
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '005_add_couche_b'
down_revision = '004_users_rbac'
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None) -> Engine | Connection:
    """Retourne la connexion/engine approprié."""
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _execute_sql(target, sql: str) -> None:
    """Exécute du SQL brut."""
    if isinstance(target, Engine):
        with target.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    else:
        target.execute(text(sql))


def upgrade(engine: Optional[Engine] = None) -> None:
    """Crée tables Couche B + active pg_trgm pour fuzzy matching."""
    bind = _get_bind(engine)
    timestamp = datetime.utcnow().isoformat()
    
    # --- Enable pg_trgm extension for fuzzy matching ---
    _execute_sql(bind, """
        CREATE EXTENSION IF NOT EXISTS pg_trgm
    """)
    
    # --- Table units (unités de mesure) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            name VARCHAR(50) NOT NULL UNIQUE,
            symbol VARCHAR(10),
            created_at TEXT NOT NULL
        )
    """)
    
    # Seed unités communes
    _execute_sql(bind, f"""
        INSERT INTO units (name, symbol, created_at) VALUES
        ('Kilogramme', 'kg', '{timestamp}'),
        ('Gramme', 'g', '{timestamp}'),
        ('Litre', 'L', '{timestamp}'),
        ('Pièce', 'pce', '{timestamp}'),
        ('Sac', 'sac', '{timestamp}'),
        ('Tonne', 't', '{timestamp}')
        ON CONFLICT (name) DO NOTHING
    """)
    
    # --- Table geo_master (zones géographiques) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS geo_master (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            type VARCHAR(50) NOT NULL,
            parent_id VARCHAR(50) REFERENCES geo_master(id),
            created_at TEXT NOT NULL
        )
    """)
    
    # Create trigram index for fuzzy name matching
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_geo_master_name_trgm 
        ON geo_master USING gin(name gin_trgm_ops)
    """)
    
    # Seed zones test (Bamako, Kayes, Sikasso)
    _execute_sql(bind, f"""
        INSERT INTO geo_master (id, name, type, parent_id, created_at) VALUES
        ('zone-bamako-1', 'Bamako', 'city', NULL, '{timestamp}'),
        ('zone-kayes-1', 'Kayes', 'city', NULL, '{timestamp}'),
        ('zone-sikasso-1', 'Sikasso', 'city', NULL, '{timestamp}')
        ON CONFLICT (id) DO NOTHING
    """)
    
    # --- Table vendors (fournisseurs/marchands) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            name VARCHAR(200) NOT NULL,
            zone_id VARCHAR(50) REFERENCES geo_master(id),
            created_at TEXT NOT NULL
        )
    """)
    
    # Create trigram index for fuzzy name matching
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_vendors_name_trgm 
        ON vendors USING gin(name gin_trgm_ops)
    """)
    
    # Seed vendors test
    _execute_sql(bind, f"""
        INSERT INTO vendors (name, zone_id, created_at) VALUES
        ('Marché Central', 'zone-bamako-1', '{timestamp}'),
        ('Boutique Kayes', 'zone-kayes-1', '{timestamp}')
        ON CONFLICT DO NOTHING
    """)
    
    # --- Table items (produits/marchandises) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            description VARCHAR(500) NOT NULL,
            category VARCHAR(100),
            unit_id INTEGER REFERENCES units(id),
            created_at TEXT NOT NULL
        )
    """)
    
    # Create trigram index for fuzzy description matching
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_items_description_trgm 
        ON items USING gin(description gin_trgm_ops)
    """)
    
    # Seed items test
    _execute_sql(bind, f"""
        INSERT INTO items (description, category, unit_id, created_at) VALUES
        ('Riz local', 'Céréales', 1, '{timestamp}'),
        ('Tomate fraîche', 'Légumes', 1, '{timestamp}'),
        ('Mil', 'Céréales', 1, '{timestamp}')
        ON CONFLICT DO NOTHING
    """)
    
    # --- Table market_signals (signaux marché) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS market_signals (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            vendor_id INTEGER REFERENCES vendors(id),
            item_id INTEGER REFERENCES items(id),
            zone_id VARCHAR(50) REFERENCES geo_master(id),
            price NUMERIC(10, 2),
            quantity NUMERIC(10, 2),
            unit_id INTEGER REFERENCES units(id),
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_signals_vendor ON market_signals(vendor_id)")
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_signals_item ON market_signals(item_id)")
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_signals_zone ON market_signals(zone_id)")
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_signals_observed ON market_signals(observed_at)")


def downgrade(engine: Optional[Engine] = None) -> None:
    """Supprime les tables Couche B."""
    bind = _get_bind(engine)
    
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_signals_observed")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_signals_zone")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_signals_item")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_signals_vendor")
    _execute_sql(bind, "DROP TABLE IF EXISTS market_signals")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_items_description_trgm")
    _execute_sql(bind, "DROP TABLE IF EXISTS items")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_vendors_name_trgm")
    _execute_sql(bind, "DROP TABLE IF EXISTS vendors")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_geo_master_name_trgm")
    _execute_sql(bind, "DROP TABLE IF EXISTS geo_master")
    _execute_sql(bind, "DROP TABLE IF EXISTS units")
    # Note: ne supprime pas l'extension pg_trgm (peut être utilisée ailleurs)
