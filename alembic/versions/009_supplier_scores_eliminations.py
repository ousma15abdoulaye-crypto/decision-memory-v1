"""Add supplier_scores and supplier_eliminations for M3B engine.

Revision ID: 009_supplier_scores_eliminations
Revises: 008_merge_heads
Create Date: 2026-02-17

Constitution V3.3.2: tables used by ScoringEngine._save_scores_to_db and save_eliminations_to_db.
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = "009_supplier_scores_eliminations"
down_revision = "008_merge_heads"
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None):
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _execute_sql(target, sql: str) -> None:
    if hasattr(target, "execute"):
        target.execute(text(sql))
        if hasattr(target, "commit"):
            target.commit()
    else:
        with target.connect() as conn:
            conn.execute(text(sql))
            conn.commit()


def upgrade(engine: Optional[Engine] = None) -> None:
    bind = _get_bind(engine)

    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS supplier_scores (
            case_id TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            category TEXT NOT NULL,
            score_value FLOAT NOT NULL,
            calculation_method TEXT NOT NULL,
            calculation_details JSONB,
            is_validated BOOLEAN NOT NULL DEFAULT FALSE,
            validated_by TEXT,
            validated_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            PRIMARY KEY (case_id, supplier_name, category)
        )
    """)
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_supplier_scores_case ON supplier_scores(case_id)")

    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS supplier_eliminations (
            case_id TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            reason_codes JSONB NOT NULL,
            details JSONB NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
    """)
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_supplier_eliminations_case ON supplier_eliminations(case_id)")


def downgrade(engine: Optional[Engine] = None) -> None:
    bind = _get_bind(engine)
    _execute_sql(bind, "DROP TABLE IF EXISTS supplier_eliminations CASCADE")
    _execute_sql(bind, "DROP TABLE IF EXISTS supplier_scores CASCADE")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_eliminations_case")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_supplier_scores_case")
