"""Add supplier_scores and supplier_eliminations tables for M3B scoring.

Revision ID: 009_add_supplier_scoring_tables
Revises: 008_merge_heads
Create Date: 2026-02-17 19:30:00
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '009_add_supplier_scoring_tables'
down_revision = '008_merge_heads'
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
    """Create supplier_scores and supplier_eliminations tables."""
    bind = _get_bind(engine)

    # ============================================
    # 1. SUPPLIER_SCORES TABLE - Stockage des scores par fournisseur
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS supplier_scores (
            id SERIAL PRIMARY KEY,
            case_id TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            category TEXT NOT NULL,
            score_value FLOAT NOT NULL,
            calculation_method TEXT NOT NULL,
            calculation_details JSONB DEFAULT '{}'::jsonb,
            is_validated BOOLEAN DEFAULT FALSE,
            validated_by TEXT,
            validated_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(case_id, supplier_name, category)
        )
    """)

    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_scores_case 
        ON supplier_scores(case_id)
    """)

    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_scores_supplier 
        ON supplier_scores(supplier_name)
    """)

    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_scores_category 
        ON supplier_scores(category)
    """)

    # ============================================
    # 2. SUPPLIER_ELIMINATIONS TABLE - Stockage des éliminations
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS supplier_eliminations (
            id SERIAL PRIMARY KEY,
            case_id TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            criterion_id TEXT NOT NULL,
            criterion_name TEXT NOT NULL,
            criterion_category TEXT NOT NULL,
            failure_reason TEXT NOT NULL,
            eliminated_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_eliminations_case 
        ON supplier_eliminations(case_id)
    """)

    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_eliminations_supplier 
        ON supplier_eliminations(supplier_name)
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Drop supplier_scores and supplier_eliminations tables."""
    bind = _get_bind(engine)
    
    # Drop indexes
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_eliminations_supplier")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_eliminations_case")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_scores_category")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_scores_supplier")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_scores_case")
    
    # Drop tables in reverse order
    _execute_sql(bind, "DROP TABLE IF EXISTS supplier_eliminations CASCADE")
    _execute_sql(bind, "DROP TABLE IF EXISTS supplier_scores CASCADE")
