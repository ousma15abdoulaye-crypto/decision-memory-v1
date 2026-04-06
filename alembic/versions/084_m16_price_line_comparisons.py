"""084 — M16 lignes de prix comparatifs (montants par bundle)

Revision ID: 084_m16_price_line_comparisons
Revises: 083_m16_deliberation_tables

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
"""

from __future__ import annotations

from alembic import op

revision = "084_m16_price_line_comparisons"
down_revision = "083_m16_deliberation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS price_line_comparisons (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            line_code       TEXT NOT NULL,
            label           TEXT,
            unit            TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (workspace_id, line_code)
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_plc_workspace ON price_line_comparisons(workspace_id)"
    )

    op.execute("ALTER TABLE price_line_comparisons ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS plc_tenant_isolation ON price_line_comparisons")
    op.execute("""
        CREATE POLICY plc_tenant_isolation ON price_line_comparisons
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS price_line_bundle_values (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            price_line_id       UUID NOT NULL REFERENCES price_line_comparisons(id) ON DELETE CASCADE,
            bundle_id           UUID NOT NULL REFERENCES supplier_bundles(id) ON DELETE CASCADE,
            workspace_id        UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id           UUID NOT NULL REFERENCES tenants(id),
            amount              NUMERIC(24,6),
            currency            TEXT NOT NULL DEFAULT 'XOF',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (price_line_id, bundle_id)
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_plbv_line ON price_line_bundle_values(price_line_id)"
    )

    op.execute("ALTER TABLE price_line_bundle_values ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS plbv_tenant_isolation ON price_line_bundle_values")
    op.execute("""
        CREATE POLICY plbv_tenant_isolation ON price_line_bundle_values
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS plbv_tenant_isolation ON price_line_bundle_values")
    op.execute("ALTER TABLE price_line_bundle_values DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS price_line_bundle_values CASCADE")

    op.execute("DROP POLICY IF EXISTS plc_tenant_isolation ON price_line_comparisons")
    op.execute("ALTER TABLE price_line_comparisons DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS price_line_comparisons CASCADE")
