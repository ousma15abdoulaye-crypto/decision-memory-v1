"""026 -- score_runs append-only + current_supplier_scores view (ADR-0006/INV-6)."""

from alembic import op

revision = "026_score_runs_append_only"
down_revision = "025_alter_scoring_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.score_runs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id         TEXT NOT NULL,
            supplier_name   TEXT NOT NULL,
            category        TEXT NOT NULL,
            score_value     NUMERIC(10,4) NOT NULL,
            calculation_details JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_score_runs_case_supplier_cat
        ON public.score_runs (case_id, supplier_name, category, created_at DESC)
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.score_runs_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'append-only: update/delete forbidden on score_runs';
        END;
        $$
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_score_runs_append_only'
                  AND tgrelid = 'public.score_runs'::regclass
            ) THEN
                CREATE TRIGGER trg_score_runs_append_only
                BEFORE UPDATE OR DELETE ON public.score_runs
                FOR EACH ROW EXECUTE FUNCTION public.score_runs_append_only();
            END IF;
        END $$
    """)

    op.execute("""
        CREATE OR REPLACE VIEW public.current_supplier_scores AS
        SELECT DISTINCT ON (case_id, supplier_name, category)
            id,
            case_id,
            supplier_name,
            category,
            score_value,
            calculation_details,
            created_at
        FROM public.score_runs
        ORDER BY case_id, supplier_name, category, created_at DESC
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.current_supplier_scores")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_score_runs_append_only'
                  AND tgrelid = 'public.score_runs'::regclass
            ) THEN
                DROP TRIGGER trg_score_runs_append_only ON public.score_runs;
            END IF;
        END $$
    """)
    op.execute("DROP FUNCTION IF EXISTS public.score_runs_append_only()")
    op.execute("DROP TABLE IF EXISTS public.score_runs")
