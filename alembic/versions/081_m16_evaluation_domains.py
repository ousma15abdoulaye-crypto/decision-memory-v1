"""081 — M16 domaines d'évaluation + extension dao_criteria

Revision ID: 081_m16_evaluation_domains
Revises: 080_market_signals_v2_zone_id_index

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
"""

from __future__ import annotations

from alembic import op

revision = "081_m16_evaluation_domains"
down_revision = "080_market_signals_v2_zone_id_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_domains (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            code            TEXT NOT NULL,
            label           TEXT NOT NULL,
            display_order   INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (workspace_id, code)
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_eval_domains_ws "
        "ON evaluation_domains(workspace_id)"
    )

    op.execute("ALTER TABLE evaluation_domains ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS edom_tenant_isolation ON evaluation_domains")
    op.execute("""
        CREATE POLICY edom_tenant_isolation ON evaluation_domains
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS evaluation_domain_id UUID
            REFERENCES evaluation_domains(id) ON DELETE SET NULL
        """)
    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS m16_criterion_code TEXT
        """)
    op.execute("""
        ALTER TABLE dao_criteria
        ADD COLUMN IF NOT EXISTS m16_scoring_mode TEXT CHECK (
            m16_scoring_mode IS NULL OR m16_scoring_mode IN (
                'numeric','qualitative','binary','not_applicable'
            )
        )
        """)


def downgrade() -> None:
    op.execute("ALTER TABLE dao_criteria DROP COLUMN IF EXISTS m16_scoring_mode")
    op.execute("ALTER TABLE dao_criteria DROP COLUMN IF EXISTS m16_criterion_code")
    op.execute("ALTER TABLE dao_criteria DROP COLUMN IF EXISTS evaluation_domain_id")

    op.execute("DROP POLICY IF EXISTS edom_tenant_isolation ON evaluation_domains")
    op.execute("ALTER TABLE evaluation_domains DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS evaluation_domains CASCADE")
