"""079 - bundle confidence, supplier qualification, signal_relevance_log (BLOC5)

Revision ID: 079_bloc5_confidence_qualification_signal_log
Revises: 078_source_package_documents_bloc5
Create Date: 2026-04-05

INV-C05/C09 : system_confidence + HITL ; C2-V431 : qualification_status / is_retained.
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "079_bloc5_confidence_qualification_signal_log"
down_revision = "078_source_package_documents_bloc5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE supplier_bundles
        ADD COLUMN qualification_status TEXT NOT NULL DEFAULT 'pending'
            CHECK (qualification_status IN ('pending','qualified','disqualified'))
        """)
    op.execute("""
        ALTER TABLE supplier_bundles
        ADD COLUMN is_retained BOOLEAN NOT NULL DEFAULT FALSE
        """)

    op.execute("""
        ALTER TABLE bundle_documents
        ADD COLUMN system_confidence NUMERIC(4,3) NOT NULL DEFAULT 1.0
            CHECK (system_confidence >= 0 AND system_confidence <= 1)
        """)
    op.execute("""
        ALTER TABLE bundle_documents
        ADD COLUMN hitl_validated_at TIMESTAMPTZ
        """)
    op.execute("""
        ALTER TABLE bundle_documents
        ADD COLUMN hitl_validated_by INTEGER REFERENCES users(id)
        """)

    op.execute("""
        ALTER TABLE bundle_documents ADD CONSTRAINT bd_hitl_when_low_confidence CHECK (
            NOT (system_confidence < 0.5 AND hitl_validated_at IS NULL)
        )
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS signal_relevance_log (
            id              BIGSERIAL PRIMARY KEY,
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            workspace_id    UUID REFERENCES process_workspaces(id) ON DELETE SET NULL,
            signal_type     TEXT NOT NULL,
            relevance_score NUMERIC(6,5) NOT NULL,
            surfaced        BOOLEAN NOT NULL DEFAULT FALSE,
            payload         JSONB NOT NULL DEFAULT '{}',
            computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_srl_workspace ON signal_relevance_log(workspace_id)"
    )
    op.execute("ALTER TABLE signal_relevance_log ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS srl_tenant_isolation ON signal_relevance_log")
    op.execute("""
        CREATE POLICY srl_tenant_isolation ON signal_relevance_log
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS signal_relevance_log CASCADE")
    op.execute(
        "ALTER TABLE bundle_documents DROP CONSTRAINT IF EXISTS bd_hitl_when_low_confidence"
    )
    op.execute("ALTER TABLE bundle_documents DROP COLUMN IF EXISTS hitl_validated_by")
    op.execute("ALTER TABLE bundle_documents DROP COLUMN IF EXISTS hitl_validated_at")
    op.execute("ALTER TABLE bundle_documents DROP COLUMN IF EXISTS system_confidence")
    op.execute("ALTER TABLE supplier_bundles DROP COLUMN IF EXISTS is_retained")
    op.execute(
        "ALTER TABLE supplier_bundles DROP COLUMN IF EXISTS qualification_status"
    )
