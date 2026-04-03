"""059 — M14 audit tables: score_history + elimination_log (append-only, RLS).

CLASSIFICATION : TENANT_SCOPED (via public.cases.id)
Révision   : 059_m14_score_history_elimination_log
Revises    : 058_m13_correction_log_case_id_index

Zéro autogenerate — op.execute() uniquement.
Triggers append-only : fn_reject_mutation() (créée en 036_db_hardening).
"""

from alembic import op

revision = "059_m14_score_history_elimination_log"
down_revision = "058_m13_correction_log_case_id_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.score_history (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id              TEXT NOT NULL REFERENCES public.cases(id),
            offer_document_id    TEXT NOT NULL,
            criterion_key        TEXT NOT NULL,
            score_value          NUMERIC(15, 4),
            max_score            NUMERIC(15, 4),
            confidence           REAL NOT NULL,
            evidence             TEXT,
            scored_by            TEXT NOT NULL DEFAULT 'system:m14',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_score_history_case_offer
        ON public.score_history (case_id, offer_document_id);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS public.elimination_log (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id              TEXT NOT NULL REFERENCES public.cases(id),
            offer_document_id    TEXT NOT NULL,
            check_id             TEXT NOT NULL DEFAULT '',
            check_name           TEXT NOT NULL DEFAULT '',
            reason               TEXT NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_elimination_log_case_offer
        ON public.elimination_log (case_id, offer_document_id);
    """)

    for table in ("score_history", "elimination_log"):
        op.execute(
            f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;"
        )
        op.execute(
            f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {table}_tenant_isolation ON public.{table};"
        )
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation
            ON public.{table}
            FOR ALL
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR EXISTS (
                    SELECT 1 FROM public.cases c
                    WHERE c.id = {table}.case_id
                      AND c.tenant_id = current_setting('app.tenant_id', true)
                )
            )
            WITH CHECK (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR EXISTS (
                    SELECT 1 FROM public.cases c
                    WHERE c.id = {table}.case_id
                      AND c.tenant_id = current_setting('app.tenant_id', true)
                )
            );
        """)

        op.execute(f"""
            DO $$ BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE p.proname = 'fn_reject_mutation' AND n.nspname = 'public'
              ) THEN
                EXECUTE 'DROP TRIGGER IF EXISTS trg_{table}_append_only ON public.{table}';
                EXECUTE 'CREATE TRIGGER trg_{table}_append_only
                  BEFORE DELETE OR UPDATE ON public.{table}
                  FOR EACH ROW
                  EXECUTE FUNCTION public.fn_reject_mutation()';
              END IF;
            END $$;
        """)


def downgrade() -> None:
    for table in ("elimination_log", "score_history"):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON public.{table};"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {table}_tenant_isolation ON public.{table};"
        )
        op.execute(
            f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY;"
        )
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP INDEX IF EXISTS public.idx_elimination_log_case_offer;")
    op.execute("DROP TABLE IF EXISTS public.elimination_log;")
    op.execute("DROP INDEX IF EXISTS public.idx_score_history_case_offer;")
    op.execute("DROP TABLE IF EXISTS public.score_history;")
