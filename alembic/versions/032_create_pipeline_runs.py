"""032 create pipeline_runs

Revision ID: 032_create_pipeline_runs
Revises: 031_committee_terminal_status
Create Date: 2026-02-24

pipeline_runs : table append-only traçant chaque exécution du pipeline A.
Trigger BEFORE UPDATE OR DELETE → exception (ADR-0012 / INV-P4).
"""

from alembic import op

revision = "032_create_pipeline_runs"
down_revision = "031_committee_terminal_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE public.pipeline_runs (
            pipeline_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id         TEXT NOT NULL,
            pipeline_type   TEXT NOT NULL
                            CHECK (pipeline_type IN ('A')),
            mode            TEXT NOT NULL
                            CHECK (mode IN ('partial', 'e2e', 'e2e_final')),
            status          TEXT NOT NULL
                            CHECK (status IN (
                                'partial_complete', 'blocked',
                                'incomplete', 'failed'
                            )),
            started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            finished_at     TIMESTAMPTZ,
            duration_ms     INTEGER CHECK (duration_ms >= 0),
            triggered_by    TEXT NOT NULL
                            CHECK (
                                char_length(triggered_by) >= 1
                                AND char_length(triggered_by) <= 255
                            ),
            result_jsonb    JSONB NOT NULL DEFAULT '{}'::jsonb,
            error_jsonb     JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        "CREATE INDEX idx_pipeline_runs_case_created "
        "ON public.pipeline_runs (case_id, created_at)"
    )

    op.execute(
        "CREATE INDEX idx_pipeline_runs_status "
        "ON public.pipeline_runs (status)"
    )

    op.execute(
        "CREATE INDEX idx_pipeline_runs_type_mode "
        "ON public.pipeline_runs (pipeline_type, mode)"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.fn_pipeline_runs_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'pipeline_runs is append-only — UPDATE/DELETE interdit (ADR-0012)';
            RETURN NULL;
        END;
        $$
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_pipeline_runs_append_only
        BEFORE UPDATE OR DELETE ON public.pipeline_runs
        FOR EACH ROW EXECUTE FUNCTION public.fn_pipeline_runs_append_only()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_pipeline_runs_append_only "
        "ON public.pipeline_runs"
    )

    op.execute(
        "DROP FUNCTION IF EXISTS public.fn_pipeline_runs_append_only()"
    )

    op.execute("DROP TABLE IF EXISTS public.pipeline_runs")
