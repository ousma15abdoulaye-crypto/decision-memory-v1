"""058 — Index sur m13_correction_log(case_id) pour les jointures FK.

Revision ID: 058_m13_correction_log_case_id_index
Revises    : 057_m13_regulatory_profile_and_correction_log
"""

from alembic import op

revision = "058_m13_correction_log_case_id_index"
down_revision = "057_m13_regulatory_profile_and_correction_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_m13_correction_log_case_id
    ON public.m13_correction_log(case_id);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.idx_m13_correction_log_case_id;")
