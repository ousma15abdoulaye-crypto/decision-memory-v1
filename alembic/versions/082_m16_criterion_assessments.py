"""082 — M16 criterion_assessments (pont relationnel depuis scores_matrix)

Revision ID: 082_m16_criterion_assessments
Revises: 081_m16_evaluation_domains

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
"""

from __future__ import annotations

from alembic import op

revision = "082_m16_criterion_assessments"
down_revision = "081_m16_evaluation_domains"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS criterion_assessments (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id               UUID NOT NULL REFERENCES tenants(id),
            bundle_id               UUID NOT NULL REFERENCES supplier_bundles(id) ON DELETE CASCADE,
            criterion_key           TEXT NOT NULL,
            dao_criterion_id        TEXT REFERENCES dao_criteria(id) ON DELETE SET NULL,
            evaluation_document_id  UUID REFERENCES evaluation_documents(id) ON DELETE SET NULL,
            cell_json               JSONB NOT NULL DEFAULT '{}'::jsonb,
            assessment_status       TEXT NOT NULL DEFAULT 'draft' CHECK (
                assessment_status IN (
                    'draft','under_review','validated','contested','not_applicable'
                )
            ),
            confidence              NUMERIC(3,2) CHECK (
                confidence IS NULL OR confidence IN (0.6, 0.8, 1.0)
            ),
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (workspace_id, bundle_id, criterion_key)
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ca_workspace ON criterion_assessments(workspace_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ca_bundle ON criterion_assessments(bundle_id)"
    )

    op.execute("ALTER TABLE criterion_assessments ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS ca_tenant_isolation ON criterion_assessments")
    op.execute("""
        CREATE POLICY ca_tenant_isolation ON criterion_assessments
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS ca_tenant_isolation ON criterion_assessments")
    op.execute("ALTER TABLE criterion_assessments DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS criterion_assessments CASCADE")
