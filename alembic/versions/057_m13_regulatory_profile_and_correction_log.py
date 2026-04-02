"""057 — M13 regulatory profile snapshots + append-only correction log.

Revision ID: 057_m13_regulatory_profile_and_correction_log
Revises    : 056_evaluation_documents
"""

from alembic import op

revision = "057_m13_regulatory_profile_and_correction_log"
down_revision = "056_evaluation_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS public.m13_regulatory_profile_versions (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        case_id         TEXT NOT NULL REFERENCES public.cases(id),
        version         INTEGER NOT NULL DEFAULT 1,
        payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uix_m13_reg_profile_case_version
    ON public.m13_regulatory_profile_versions (case_id, version);
    """)
    op.execute(
        "ALTER TABLE public.m13_regulatory_profile_versions ENABLE ROW LEVEL SECURITY;"
    )
    op.execute(
        "ALTER TABLE public.m13_regulatory_profile_versions FORCE ROW LEVEL SECURITY;"
    )
    op.execute(
        "DROP POLICY IF EXISTS m13_reg_profile_tenant_isolation"
        " ON public.m13_regulatory_profile_versions;"
    )
    op.execute("""
    CREATE POLICY m13_reg_profile_tenant_isolation
    ON public.m13_regulatory_profile_versions
    FOR ALL
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR EXISTS (
            SELECT 1 FROM public.cases c
            WHERE c.id = m13_regulatory_profile_versions.case_id
              AND c.tenant_id = current_setting('app.tenant_id', true)
        )
    )
    WITH CHECK (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR EXISTS (
            SELECT 1 FROM public.cases c
            WHERE c.id = m13_regulatory_profile_versions.case_id
              AND c.tenant_id = current_setting('app.tenant_id', true)
        )
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS public.m13_correction_log (
        id                  BIGSERIAL PRIMARY KEY,
        case_id             TEXT NOT NULL,
        field_path          TEXT NOT NULL,
        value_predicted     TEXT,
        value_corrected     TEXT,
        layer_origin        TEXT,
        confidence_was      DOUBLE PRECISION,
        correction_source   TEXT,
        corpus_size_at_correction INTEGER,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("""
    CREATE OR REPLACE FUNCTION m13_correction_log_no_modify()
        RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'm13_correction_log is append-only: % not allowed', TG_OP;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute(
        "DROP TRIGGER IF EXISTS trg_m13_correction_log_no_update ON m13_correction_log;"
    )
    op.execute("""
    CREATE TRIGGER trg_m13_correction_log_no_update
        BEFORE UPDATE ON m13_correction_log
        FOR EACH ROW EXECUTE FUNCTION m13_correction_log_no_modify();
    """)
    op.execute(
        "DROP TRIGGER IF EXISTS trg_m13_correction_log_no_delete ON m13_correction_log;"
    )
    op.execute("""
    CREATE TRIGGER trg_m13_correction_log_no_delete
        BEFORE DELETE ON m13_correction_log
        FOR EACH ROW EXECUTE FUNCTION m13_correction_log_no_modify();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_m13_correction_log_no_delete ON m13_correction_log;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_m13_correction_log_no_update ON m13_correction_log;"
    )
    op.execute("DROP FUNCTION IF EXISTS m13_correction_log_no_modify();")
    op.execute("DROP TABLE IF EXISTS public.m13_correction_log;")
    op.execute(
        "DROP POLICY IF EXISTS m13_reg_profile_tenant_isolation"
        " ON public.m13_regulatory_profile_versions;"
    )
    op.execute("DROP TABLE IF EXISTS public.m13_regulatory_profile_versions;")
