"""055 — Étend RLS à documents, extraction_jobs et user_tenants.

Migration chirurgicale : aucune autogenerate.
Périmètre : CHANTIER-2 plan de correction CTO-grade.

Tables couvertes après cette migration :
  - documents           : tenant_id backfillé via cases, RLS policy
  - extraction_jobs     : RLS via document_id → documents → cases
  - user_tenants        : RLS — seul son propre user_id ou admin

Revision ID: 055_extend_rls_documents_extraction_jobs
Revises    : 054_m12_correction_log
"""

from alembic import op

revision = "055_extend_rls_documents_extraction_jobs"
down_revision = "054_m12_correction_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. documents : ajout tenant_id + backfill + NOT NULL + RLS ──────────
    op.execute("ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS tenant_id TEXT;")
    op.execute("""
        UPDATE public.documents d
        SET tenant_id = c.tenant_id
        FROM public.cases c
        WHERE c.id = d.case_id
          AND (d.tenant_id IS NULL OR d.tenant_id = '');
    """)
    op.execute("""
        UPDATE public.documents SET tenant_id = 'legacy-default'
        WHERE tenant_id IS NULL OR trim(tenant_id) = '';
    """)
    op.execute(
        "ALTER TABLE public.documents ALTER COLUMN tenant_id SET DEFAULT 'legacy-default';"
    )
    op.execute("ALTER TABLE public.documents ALTER COLUMN tenant_id SET NOT NULL;")

    op.execute("ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.documents FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS documents_tenant_isolation ON public.documents;")
    op.execute("""
        CREATE POLICY documents_tenant_isolation ON public.documents
        FOR ALL
        USING (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR tenant_id = current_setting('app.tenant_id', true)
        )
        WITH CHECK (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR tenant_id = current_setting('app.tenant_id', true)
        );
    """)

    # ── 2. extraction_jobs : RLS via document_id → documents ────────────────
    op.execute("ALTER TABLE public.extraction_jobs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.extraction_jobs FORCE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS extraction_jobs_tenant_isolation ON public.extraction_jobs;"
    )
    op.execute("""
        CREATE POLICY extraction_jobs_tenant_isolation ON public.extraction_jobs
        FOR ALL
        USING (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR EXISTS (
                SELECT 1 FROM public.documents doc
                WHERE doc.id = extraction_jobs.document_id
                  AND doc.tenant_id = current_setting('app.tenant_id', true)
            )
        )
        WITH CHECK (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR EXISTS (
                SELECT 1 FROM public.documents doc
                WHERE doc.id = extraction_jobs.document_id
                  AND doc.tenant_id = current_setting('app.tenant_id', true)
            )
        );
    """)

    # ── 3. user_tenants : RLS — seul son user_id ou admin ───────────────────
    op.execute("ALTER TABLE public.user_tenants ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.user_tenants FORCE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS user_tenants_self_isolation ON public.user_tenants;"
    )
    op.execute("""
        CREATE POLICY user_tenants_self_isolation ON public.user_tenants
        FOR ALL
        USING (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR user_id::text = current_setting('app.user_id', true)
        )
        WITH CHECK (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR user_id::text = current_setting('app.user_id', true)
        );
    """)


def downgrade() -> None:
    # ── user_tenants ────────────────────────────────────────────────────────
    op.execute(
        "DROP POLICY IF EXISTS user_tenants_self_isolation ON public.user_tenants;"
    )
    op.execute("ALTER TABLE public.user_tenants NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.user_tenants DISABLE ROW LEVEL SECURITY;")

    # ── extraction_jobs ──────────────────────────────────────────────────────
    op.execute(
        "DROP POLICY IF EXISTS extraction_jobs_tenant_isolation ON public.extraction_jobs;"
    )
    op.execute("ALTER TABLE public.extraction_jobs NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.extraction_jobs DISABLE ROW LEVEL SECURITY;")

    # ── documents ────────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS documents_tenant_isolation ON public.documents;")
    op.execute("ALTER TABLE public.documents NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.documents DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.documents DROP COLUMN IF EXISTS tenant_id;")
