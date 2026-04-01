"""056 — Crée la table evaluation_documents + RLS tenant_scoped.

Migration chirurgicale : aucune autogenerate.
DDL source : docs/freeze/DMS_V4.1.0_FREEZE.md (PARTIE IV — ÉVALUATION ACO)
Autorité   : Plan Directeur DMS V4.1 / DETTE-5 (docs/mandates/DETTE_M12.md)

Périmètre :
  - CREATE TABLE public.evaluation_documents (idempotent IF NOT EXISTS)
  - index unique (case_id, version) pour éviter les doublons de version
  - ENABLE ROW LEVEL SECURITY + policy tenant_scoped via cases.tenant_id

Types réels de la DB DMS (§4.3 règle universelle types) :
  cases.id          : TEXT  (pas UUID — migration 002 + règle §4.3)
  committees.committee_id : UUID
  users.id          : INTEGER (migration 042)

Revision ID: 056_evaluation_documents
Revises    : 055_extend_rls_documents_extraction_jobs
"""

from alembic import op

revision = "056_evaluation_documents"
down_revision = "055_extend_rls_documents_extraction_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Créer la table evaluation_documents ──────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.evaluation_documents (
          id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          case_id                 TEXT NOT NULL REFERENCES public.cases(id),
          committee_id            UUID NOT NULL REFERENCES public.committees(committee_id),
          version                 INTEGER NOT NULL DEFAULT 1,
          scores_matrix           JSONB NOT NULL DEFAULT '{}',
          justifications          JSONB NOT NULL DEFAULT '{}',
          qualification_threshold FLOAT,
          vendors_qualified       UUID[],
          vendors_eliminated      UUID[],
          pre_negotiation_scores  JSONB,
          status                  TEXT NOT NULL DEFAULT 'draft' CHECK (
            status IN ('draft','committee_review','sealed','exported')
          ),
          profile_applied         TEXT,
          aco_excel_path          TEXT,
          pv_word_path            TEXT,
          sealed_at               TIMESTAMPTZ,
          sealed_by               INTEGER REFERENCES public.users(id),
          seal_hash               TEXT,
          created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ── 2. Index unique (case_id, version) — évite les doublons de version ──
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uix_evaluation_documents_case_version
        ON public.evaluation_documents (case_id, version);
    """)

    # ── 3. RLS tenant_scoped via cases.tenant_id ────────────────────────────
    op.execute("ALTER TABLE public.evaluation_documents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.evaluation_documents FORCE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS evaluation_documents_tenant_isolation"
        " ON public.evaluation_documents;"
    )
    op.execute("""
        CREATE POLICY evaluation_documents_tenant_isolation
        ON public.evaluation_documents
        FOR ALL
        USING (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR EXISTS (
                SELECT 1 FROM public.cases c
                WHERE c.id = evaluation_documents.case_id
                  AND c.tenant_id = current_setting('app.tenant_id', true)
            )
        )
        WITH CHECK (
            COALESCE(current_setting('app.is_admin', true), '') = 'true'
            OR EXISTS (
                SELECT 1 FROM public.cases c
                WHERE c.id = evaluation_documents.case_id
                  AND c.tenant_id = current_setting('app.tenant_id', true)
            )
        );
    """)


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS evaluation_documents_tenant_isolation"
        " ON public.evaluation_documents;"
    )
    op.execute("ALTER TABLE public.evaluation_documents NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.evaluation_documents DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP INDEX IF EXISTS public.uix_evaluation_documents_case_version;")
    op.execute("DROP TABLE IF EXISTS public.evaluation_documents;")
