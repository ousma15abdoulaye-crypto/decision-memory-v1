"""add_supplier_scoring_tables

Revision ID: 67c15e17b338
Revises: 008_merge_heads
Create Date: 2026-02-17 18:00:37.519257

"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '67c15e17b338'
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
    """Crée les tables supplier_scores et supplier_eliminations."""
    bind = _get_bind(engine)
    
    # Table supplier_scores
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS supplier_scores (
            id SERIAL PRIMARY KEY,
            case_id VARCHAR(50) NOT NULL,
            supplier_name VARCHAR(255) NOT NULL,
            category VARCHAR(50) NOT NULL,
            score_value FLOAT NOT NULL,
            calculation_method VARCHAR(100),
            calculation_details JSONB,
            is_validated BOOLEAN DEFAULT FALSE,
            validated_by VARCHAR(255),
            validated_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(case_id, supplier_name, category)
        )
    """)
    
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_scores_case 
        ON supplier_scores(case_id)
    """)
    
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_scores_supplier 
        ON supplier_scores(case_id, supplier_name)
    """)
    
    # Table supplier_eliminations
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS supplier_eliminations (
            id SERIAL PRIMARY KEY,
            case_id VARCHAR(50) NOT NULL,
            supplier_name VARCHAR(255) NOT NULL,
            reason_codes JSONB NOT NULL,
            details JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_eliminations_case 
        ON supplier_eliminations(case_id)
    """)
    
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_supplier_eliminations_supplier 
        ON supplier_eliminations(case_id, supplier_name)
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Supprime les tables supplier_scores et supplier_eliminations."""
    bind = _get_bind(engine)
    
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_eliminations_supplier")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_eliminations_case")
    _execute_sql(bind, "DROP TABLE IF EXISTS supplier_eliminations CASCADE")
    
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_scores_supplier")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_scores_case")
    _execute_sql(bind, "DROP TABLE IF EXISTS supplier_scores CASCADE")
