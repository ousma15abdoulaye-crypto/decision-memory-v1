"""Add procurement_references, categories, lots, thresholds, is_late flag

Revision ID: 003_add_procurement_extensions
Revises: 002_add_couche_a
Create Date: 2026-02-12
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '003_add_procurement_extensions'
down_revision = '002_add_couche_a'
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
    """Ajoute les tables procurement_references, procurement_categories, lots, procurement_thresholds
    et les colonnes is_late (artifacts) et lot_id (offers).
    """
    bind = _get_bind(engine)
    
    # --- procurement_references (séquence d'ID métier) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS procurement_references (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            ref_type TEXT NOT NULL,
            ref_number TEXT UNIQUE NOT NULL,
            year INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # --- procurement_categories (catalogue) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS procurement_categories (
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            threshold_usd NUMERIC(12, 2),
            requires_technical_eval BOOLEAN DEFAULT true,
            min_suppliers INTEGER DEFAULT 3,
            created_at TEXT NOT NULL
        )
    """)
    
    # --- lots (liés à cases) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS lots (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            lot_number TEXT NOT NULL,
            description TEXT,
            estimated_value NUMERIC(12, 2),
            created_at TEXT NOT NULL,
            UNIQUE (case_id, lot_number)
        )
    """)
    
    # --- procurement_thresholds (seuils procédures) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS procurement_thresholds (
            id SERIAL PRIMARY KEY,
            procedure_type TEXT UNIQUE NOT NULL,
            min_amount_usd NUMERIC(12, 2),
            max_amount_usd NUMERIC(12, 2),
            min_suppliers INTEGER
        )
    """)
    
    # --- Ajout colonne is_late dans artifacts (si elle n'existe pas) ---
    _execute_sql(bind, """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='artifacts' AND column_name='is_late'
            ) THEN
                ALTER TABLE artifacts ADD COLUMN is_late BOOLEAN DEFAULT false;
            END IF;
        END $$;
    """)
    
    # --- Ajout colonne lot_id dans offers (si elle n'existe pas) ---
    _execute_sql(bind, """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='offers' AND column_name='lot_id'
            ) THEN
                ALTER TABLE offers ADD COLUMN lot_id TEXT REFERENCES lots(id);
            END IF;
        END $$;
    """)
    
    # --- Données initiales (seuils Save the Children) ---
    _execute_sql(bind, """
        INSERT INTO procurement_thresholds (procedure_type, min_amount_usd, max_amount_usd, min_suppliers)
        VALUES
        ('RFQ', 0, 10000, 3),
        ('RFP', 10001, 100000, 5),
        ('DAO', 100001, NULL, 5)
        ON CONFLICT (procedure_type) DO NOTHING
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Supprime les tables et colonnes ajoutées."""
    bind = _get_bind(engine)
    
    # Supprimer colonnes ajoutées
    _execute_sql(bind, """
        ALTER TABLE offers DROP COLUMN IF EXISTS lot_id;
    """)
    
    _execute_sql(bind, """
        ALTER TABLE artifacts DROP COLUMN IF EXISTS is_late;
    """)
    
    # Supprimer tables
    _execute_sql(bind, """
        DROP TABLE IF EXISTS procurement_thresholds CASCADE;
    """)
    
    _execute_sql(bind, """
        DROP TABLE IF EXISTS lots CASCADE;
    """)
    
    _execute_sql(bind, """
        DROP TABLE IF EXISTS procurement_categories CASCADE;
    """)
    
    _execute_sql(bind, """
        DROP TABLE IF EXISTS procurement_references CASCADE;
    """)
