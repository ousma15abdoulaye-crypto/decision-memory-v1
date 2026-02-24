"""034 add force_recompute pipeline_runs

Revision ID: 034_pipeline_force_recompute
Revises: 033_create_pipeline_step_runs
Create Date: 2026-02-24

Ajoute pipeline_runs.force_recompute BOOLEAN NOT NULL DEFAULT FALSE.
Migration stricte : pas de IF NOT EXISTS (detection fantomes via preflight 0-D).
ADR-0013 — INV-P14/P15A/P18
"""

from alembic import op

revision = "034_pipeline_force_recompute"
down_revision = "033_create_pipeline_step_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.pipeline_runs
        ADD COLUMN force_recompute BOOLEAN NOT NULL DEFAULT FALSE
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN public.pipeline_runs.force_recompute IS
        'False=tentative reutilisation scoring (INV-P14); True=calcul force (INV-P15A). ADR-0013.'
        """
    )

    op.execute(
        """
        CREATE INDEX idx_pipeline_runs_force_recompute
        ON public.pipeline_runs (force_recompute)
        WHERE force_recompute = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pipeline_runs_force_recompute")

    op.execute(
        "ALTER TABLE public.pipeline_runs DROP COLUMN force_recompute"
    )
