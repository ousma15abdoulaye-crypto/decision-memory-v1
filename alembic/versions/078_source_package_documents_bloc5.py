"""078 - source_package_documents (BLOC5 SPEC V4.3.1 / O2)

Revision ID: 078_source_package_documents_bloc5
Revises: 077_fix_bridge_triggers_workspace_id
Create Date: 2026-04-05

Documents dossier source (DAO, RFQ, TDR, etc.) — INV-C02 : ne pas confondre avec bundle_documents.
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "078_source_package_documents_bloc5"
down_revision = "077_fix_bridge_triggers_workspace_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS source_package_documents (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id               UUID NOT NULL REFERENCES tenants(id),

            doc_type TEXT NOT NULL CHECK (doc_type IN (
                'dao','rfq','tdr','procurement_notice','market_notice',
                'instructions','clarification','amendment',
                'evaluation_grid','budget_reference','other'
            )),
            filename                TEXT NOT NULL,
            sha256                  TEXT NOT NULL,
            extraction_confidence   NUMERIC(4,3) NOT NULL
                CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
            structured_json         JSONB,

            uploaded_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            uploaded_by             INTEGER REFERENCES users(id),

            UNIQUE (workspace_id, sha256)
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_spd_workspace ON source_package_documents(workspace_id)"
    )
    op.execute("ALTER TABLE source_package_documents ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS spd_tenant_isolation ON source_package_documents")
    op.execute("""
        CREATE POLICY spd_tenant_isolation ON source_package_documents
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source_package_documents CASCADE")
