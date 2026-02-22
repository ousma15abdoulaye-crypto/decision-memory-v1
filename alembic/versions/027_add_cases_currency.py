"""add cases.currency

Revision ID: 027_add_cases_currency
Revises: 026_score_runs_append_only
Create Date: 2026-02-22

ADR-0010 D2 -- currency portee par le Case, jamais hardcodee dans le moteur.
Constitution §1.2 -- universalite geographique.
"""

from alembic import op

revision = "027_add_cases_currency"
down_revision = "026_score_runs_append_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.cases
        ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'XOF'
    """)
    op.execute("""
        COMMENT ON COLUMN public.cases.currency IS
        'Devise du dossier -- ISO 4217 (XOF, USD, EUR, TZS...).
         Source unique : jamais hardcodee dans le moteur de scoring.
         ADR-0010 D2 -- Constitution §1.2 universalite.'
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.cases DROP COLUMN IF EXISTS currency
    """)
