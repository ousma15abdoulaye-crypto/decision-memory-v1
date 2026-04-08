"""093 — Table assessment_history (Canon V5.1.0 §5.4, O6).

Revision ID: 093_v51_assessment_history
Revises: 092_workspace_access_model_v2

Journal des changements sur critères d'évaluation (flags, etc.).
Distinct de criterion_assessment_history (M16 append-only technique).

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "093_v51_assessment_history"
down_revision = "092_workspace_access_model_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS assessment_history (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            criterion_assessment_id UUID NOT NULL
                REFERENCES criterion_assessments(id) ON DELETE CASCADE,
            workspace_id            UUID NOT NULL
                REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id               UUID NOT NULL REFERENCES tenants(id),
            changed_by              INTEGER NOT NULL REFERENCES users(id),
            change_reason           TEXT NOT NULL,
            change_metadata         JSONB NOT NULL DEFAULT '{}',
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_assessment_history_workspace "
        "ON assessment_history(workspace_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_assessment_history_tenant "
        "ON assessment_history(tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_assessment_history_ca "
        "ON assessment_history(criterion_assessment_id)"
    )

    op.execute("ALTER TABLE assessment_history ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_history FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS assessment_history_tenant ON assessment_history")
    op.execute("""
        CREATE POLICY assessment_history_tenant ON assessment_history
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
                OR tenant_id = current_setting('app.current_tenant', true)::uuid
            )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS assessment_history_tenant ON assessment_history")
    op.execute("ALTER TABLE assessment_history DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS assessment_history CASCADE")
