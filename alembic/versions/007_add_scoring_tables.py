"""Add submission_scores table for M3B scoring engine.

Revision ID: 007_add_submission_scores
Revises: 006_criteria_types
Create Date: 2026-02-14 11:30:00
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '007_add_submission_scores'
down_revision = '006_criteria_types'
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

    # ============================================
    # 1. SUBMISSION_SCORES TABLE - Stockage des notes par offre
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS submission_scores (
            id TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL REFERENCES offer_extractions(id) ON DELETE CASCADE,
            essential_pass BOOLEAN,
            capacity_score FLOAT,
            commercial_score FLOAT,
            sustainability_score FLOAT,
            missing_fields TEXT,
            computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_submission_scores_submission 
        ON submission_scores(submission_id)
    """)
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_submission_scores_essential 
        ON submission_scores(essential_pass)
    """)

    # ============================================
    # 2. SCORING_CONFIGS TABLE - Configuration par profil (mise à jour)
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS scoring_configs (
            id TEXT PRIMARY KEY,
            profile_code TEXT NOT NULL UNIQUE,
            commercial_formula TEXT NOT NULL DEFAULT 'price_lowest_100',
            commercial_weight FLOAT NOT NULL DEFAULT 0.5,
            capacity_formula TEXT NOT NULL DEFAULT 'capacity_experience',
            capacity_weight FLOAT NOT NULL DEFAULT 0.3,
            sustainability_formula TEXT NOT NULL DEFAULT 'sustainability_certifications',
            sustainability_weight FLOAT NOT NULL DEFAULT 0.1,
            essentials_weight FLOAT NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Seed scoring configs from evaluation profiles
    _execute_sql(bind, """
        INSERT INTO scoring_configs 
        (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, 
         sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at)
        VALUES
        ('scoring_generic', 'GENERIC', 'price_lowest_100', 0.50, 'capacity_experience', 0.30, 'sustainability_certifications', 0.10, 0.0, 
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_health', 'HEALTH', 'price_lowest_100', 0.40, 'capacity_experience', 0.40, 'sustainability_certifications', 0.10, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_constr', 'CONSTR', 'price_lowest_100', 0.40, 'capacity_experience', 0.40, 'sustainability_certifications', 0.10, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_it', 'IT', 'price_lowest_100', 0.50, 'capacity_experience', 0.35, 'sustainability_certifications', 0.15, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_travel', 'TRAVEL', 'price_lowest_100', 0.60, 'capacity_experience', 0.25, 'sustainability_certifications', 0.10, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_property', 'PROPERTY', 'price_lowest_100', 0.50, 'capacity_experience', 0.35, 'sustainability_certifications', 0.10, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_labor', 'LABOR', 'price_lowest_100', 0.45, 'capacity_experience', 0.40, 'sustainability_certifications', 0.10, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_cva', 'CVA', 'price_lowest_100', 0.50, 'capacity_experience', 0.35, 'sustainability_certifications', 0.10, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_fleet', 'FLEET', 'price_lowest_100', 0.45, 'capacity_experience', 0.35, 'sustainability_certifications', 0.15, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z'),
        ('scoring_insurance', 'INSURANCE', 'price_lowest_100', 0.70, 'capacity_experience', 0.20, 'sustainability_certifications', 0.10, 0.0,
         '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z')
        ON CONFLICT (profile_code) DO NOTHING
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    bind = _get_bind(engine)
    
    # Drop tables in reverse order
    _execute_sql(bind, "DROP TABLE IF EXISTS scoring_configs CASCADE")
    _execute_sql(bind, "DROP TABLE IF EXISTS submission_scores CASCADE")
    
    # Drop indexes
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_submission_scores_submission")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_submission_scores_essential")
