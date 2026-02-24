"""033 create pipeline_step_runs

Revision ID: 033_create_pipeline_step_runs
Revises: 032_create_pipeline_runs
Create Date: 2026-02-24

pipeline_step_runs : table append-only traçant chaque step d'un pipeline_run.
FK sur pipeline_runs ON DELETE RESTRICT.
Trigger BEFORE UPDATE OR DELETE → exception (ADR-0012 / INV-P4).
"""

from alembic import op

revision = "033_create_pipeline_step_runs"
down_revision = "032_create_pipeline_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE public.pipeline_step_runs (
            step_run_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pipeline_run_id  UUID NOT NULL
                             REFERENCES public.pipeline_runs(pipeline_run_id)
                             ON DELETE RESTRICT,
            step_name        TEXT NOT NULL
                             CHECK (step_name IN (
                                 'preflight',
                                 'extraction_summary',
                                 'criteria_summary',
                                 'normalization_summary',
                                 'scoring'
                             )),
            status           TEXT NOT NULL
                             CHECK (status IN (
                                 'ok', 'blocked', 'incomplete',
                                 'failed', 'skipped'
                             )),
            started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            finished_at      TIMESTAMPTZ,
            duration_ms      INTEGER CHECK (duration_ms >= 0),
            reason_code      TEXT,
            reason_message   TEXT,
            meta_jsonb       JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        "CREATE INDEX idx_pipeline_step_runs_run_id "
        "ON public.pipeline_step_runs (pipeline_run_id)"
    )

    op.execute(
        "CREATE INDEX idx_pipeline_step_runs_step_name "
        "ON public.pipeline_step_runs (step_name)"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.fn_pipeline_step_runs_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'pipeline_step_runs is append-only — UPDATE/DELETE interdit (ADR-0012)';
            RETURN NULL;
        END;
        $$
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_pipeline_step_runs_append_only
        BEFORE UPDATE OR DELETE ON public.pipeline_step_runs
        FOR EACH ROW EXECUTE FUNCTION public.fn_pipeline_step_runs_append_only()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_pipeline_step_runs_append_only "
        "ON public.pipeline_step_runs"
    )

    op.execute(
        "DROP FUNCTION IF EXISTS public.fn_pipeline_step_runs_append_only()"
    )

    op.execute("DROP TABLE IF EXISTS public.pipeline_step_runs")
