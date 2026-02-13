"""Add criterion_category, is_eliminatory, min_weight_pct to dao_criteria

Revision ID: 006_criteria_types
Revises: 004_users_rbac
Create Date: 2026-02-13 10:00:00
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '006_criteria_types'
down_revision = '004_users_rbac'
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None) -> Engine | Connection:
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _execute_sql(target, sql: str) -> None:
    if isinstance(target, Engine):
        with target.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    else:
        target.execute(text(sql))


def upgrade(engine: Optional[Engine] = None) -> None:
    bind = _get_bind(engine)

    # --- Ajout des colonnes à dao_criteria ---
    _execute_sql(bind, """
        ALTER TABLE dao_criteria 
        ADD COLUMN IF NOT EXISTS criterion_category TEXT,
        ADD COLUMN IF NOT EXISTS is_eliminatory BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS min_weight_pct FLOAT
    """)

    # --- Contrainte sur les catégories autorisées ---
    _execute_sql(bind, """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'check_criterion_category'
            ) THEN
                ALTER TABLE dao_criteria 
                ADD CONSTRAINT check_criterion_category 
                CHECK (criterion_category IN ('essential', 'commercial', 'capacity', 'sustainability'));
            END IF;
        END $$;
    """)

    # --- Index pour les requêtes fréquentes ---
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_dao_criteria_case_cat 
        ON dao_criteria(case_id, criterion_category)
    """)

    # --- Table de validation des pondérations ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS criteria_weighting_validation (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            commercial_weight FLOAT NOT NULL,
            sustainability_weight FLOAT NOT NULL,
            is_valid BOOLEAN NOT NULL,
            validation_errors TEXT,
            created_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_validation_case 
        ON criteria_weighting_validation(case_id)
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    bind = _get_bind(engine)
    _execute_sql(bind, "DROP TABLE IF EXISTS criteria_weighting_validation CASCADE")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_dao_criteria_case_cat")
    _execute_sql(bind, "ALTER TABLE dao_criteria DROP CONSTRAINT IF EXISTS check_criterion_category")
    _execute_sql(bind, "ALTER TABLE dao_criteria DROP COLUMN IF EXISTS min_weight_pct")
    _execute_sql(bind, "ALTER TABLE dao_criteria DROP COLUMN IF EXISTS is_eliminatory")
    _execute_sql(bind, "ALTER TABLE dao_criteria DROP COLUMN IF EXISTS criterion_category")
