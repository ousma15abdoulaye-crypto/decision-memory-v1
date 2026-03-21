"""051 — tenant_id sur cases, user_tenants, RLS (isolation DB).

Revision ID: 051_cases_tenant_user_tenants_rls
Revises: 050_documents_sha256_not_null
"""

from alembic import op

revision = "051_cases_tenant_user_tenants_rls"
down_revision = "050_documents_sha256_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.user_tenants (
            user_id INTEGER PRIMARY KEY
                REFERENCES public.users(id) ON DELETE CASCADE,
            tenant_id TEXT NOT NULL
        );
    """)

    op.execute("""
        INSERT INTO public.user_tenants (user_id, tenant_id)
        SELECT
            u.id,
            COALESCE(NULLIF(trim(u.organization), ''), 'tenant-' || u.id::text)
        FROM public.users u
        ON CONFLICT (user_id) DO NOTHING;
    """)

    op.execute("""
        ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS tenant_id TEXT;
    """)
    op.execute("""
        UPDATE public.cases c
        SET tenant_id = ut.tenant_id
        FROM public.user_tenants ut
        WHERE c.owner_id = ut.user_id
          AND (c.tenant_id IS NULL OR c.tenant_id = '');
    """)
    op.execute("""
        UPDATE public.cases SET tenant_id = 'legacy-default'
        WHERE tenant_id IS NULL OR trim(tenant_id) = '';
    """)
    op.execute("""
        ALTER TABLE public.cases ALTER COLUMN tenant_id SET DEFAULT 'legacy-default';
    """)
    op.execute("""
        ALTER TABLE public.cases ALTER COLUMN tenant_id SET NOT NULL;
    """)

    # ── RLS (efficace pour rôles non superuser / non BYPASSRLS) ──
    op.execute("ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.cases FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS cases_tenant_isolation ON public.cases;")
    op.execute("""
        CREATE POLICY cases_tenant_isolation ON public.cases
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

    for table in ("supplier_scores", "pipeline_runs", "criteria"):
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
            CREATE POLICY {table}_tenant_isolation ON public.{table}
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


def downgrade() -> None:
    for table in ("criteria", "pipeline_runs", "supplier_scores"):
        op.execute(
            f"DROP POLICY IF EXISTS {table}_tenant_isolation ON public.{table};"
        )
        op.execute(
            f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY;"
        )
        op.execute(
            f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;"
        )

    op.execute("DROP POLICY IF EXISTS cases_tenant_isolation ON public.cases;")
    op.execute("ALTER TABLE public.cases NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.cases DISABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE public.cases DROP COLUMN IF EXISTS tenant_id;")
    op.execute("DROP TABLE IF EXISTS public.user_tenants;")
