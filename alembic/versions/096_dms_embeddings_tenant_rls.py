"""096 — tenant_id + RLS sur dms_embeddings (RAG corpus M12).

Révision unique : contrainte UNIQUE (tenant_id, source_table, source_pk, chunk_index),
backfill tenant par défaut (sci_mali / premier tenant), politique alignée 094.

Revision ID: 096_dms_embeddings_tenant_rls
Revises: 095_tenant_id_default_offers_extractions
"""

from __future__ import annotations

from alembic import op

revision = "096_dms_embeddings_tenant_rls"
down_revision = "095_tenant_id_default_offers_extractions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $body$
        DECLARE
            v_default uuid;
        BEGIN
            SELECT id INTO v_default FROM public.tenants WHERE code = 'sci_mali' LIMIT 1;
            IF v_default IS NULL THEN
                SELECT id INTO v_default FROM public.tenants ORDER BY code LIMIT 1;
            END IF;
            IF v_default IS NULL THEN
                RAISE EXCEPTION '096_dms_embeddings: aucune ligne dans public.tenants';
            END IF;

            ALTER TABLE public.dms_embeddings
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.dms_embeddings SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.dms_embeddings ALTER COLUMN tenant_id SET NOT NULL;

            ALTER TABLE public.dms_embeddings
                DROP CONSTRAINT IF EXISTS dms_embeddings_source_table_source_pk_chunk_index_key;

            -- Idempotent : évite DuplicateTable si upgrade rejoué (ex. workers pytest / DB partagée).
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                JOIN pg_namespace n ON t.relnamespace = n.oid
                WHERE n.nspname = 'public'
                  AND t.relname = 'dms_embeddings'
                  AND c.conname = 'dms_embeddings_tenant_source_chunk_uniq'
            ) THEN
                ALTER TABLE public.dms_embeddings
                    ADD CONSTRAINT dms_embeddings_tenant_source_chunk_uniq
                    UNIQUE (tenant_id, source_table, source_pk, chunk_index);
            END IF;

            ALTER TABLE public.dms_embeddings
                ALTER COLUMN tenant_id SET DEFAULT public.dms_default_tenant_id();
        END
        $body$;
    """)

    op.execute("ALTER TABLE public.dms_embeddings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.dms_embeddings FORCE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS dms_embeddings_tenant_uuid_isolation ON public.dms_embeddings;"
    )
    op.execute("""
        CREATE POLICY dms_embeddings_tenant_uuid_isolation ON public.dms_embeddings
        FOR ALL
        USING (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR tenant_id = current_setting('app.current_tenant', true)::uuid
        )
        WITH CHECK (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR tenant_id = current_setting('app.current_tenant', true)::uuid
        );
    """)


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS dms_embeddings_tenant_uuid_isolation ON public.dms_embeddings;"
    )
    op.execute("ALTER TABLE public.dms_embeddings NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.dms_embeddings DISABLE ROW LEVEL SECURITY;")

    op.execute("""
        ALTER TABLE public.dms_embeddings
            DROP CONSTRAINT IF EXISTS dms_embeddings_tenant_source_chunk_uniq;
    """)

    op.execute("""
        ALTER TABLE public.dms_embeddings
            ALTER COLUMN tenant_id DROP DEFAULT;
    """)
    op.execute("ALTER TABLE public.dms_embeddings DROP COLUMN IF EXISTS tenant_id;")

    op.execute("""
        ALTER TABLE public.dms_embeddings
            ADD CONSTRAINT dms_embeddings_source_table_source_pk_chunk_index_key
            UNIQUE (source_table, source_pk, chunk_index);
    """)
