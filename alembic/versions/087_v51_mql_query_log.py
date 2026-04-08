"""087 — V5.1 mql_query_log : journal requêtes agent MQL

Revision ID: 087_v51_mql_query_log
Revises: 086_m16_force_row_level_security

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
Canon V5.1.0 Section 8.7.
Adaptation codebase : user_id INTEGER (migration 004) — Canon mentionne UUID
                      par cohérence avec users.id = INTEGER.
"""

from __future__ import annotations

from alembic import op

revision = "087_v51_mql_query_log"
down_revision = "086_m16_force_row_level_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS mql_query_log (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL REFERENCES tenants(id),
            workspace_id        UUID REFERENCES process_workspaces(id) ON DELETE SET NULL,
            user_id             INTEGER NOT NULL REFERENCES users(id),
            query_text          TEXT NOT NULL,
            intent_classified   VARCHAR(50) NOT NULL,
            intent_confidence   NUMERIC(4, 3) NOT NULL,
            template_used       VARCHAR(50),
            sources_count       INTEGER NOT NULL DEFAULT 0,
            latency_ms          INTEGER NOT NULL,
            model_used          VARCHAR(100) NOT NULL,
            langfuse_trace_id   VARCHAR(100),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mql_log_tenant "
        "ON mql_query_log(tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mql_log_workspace "
        "ON mql_query_log(workspace_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mql_log_created "
        "ON mql_query_log(created_at)"
    )

    op.execute("ALTER TABLE mql_query_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE mql_query_log FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS mql_log_tenant_isolation ON mql_query_log")
    op.execute("""
        CREATE POLICY mql_log_tenant_isolation ON mql_query_log
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS mql_log_tenant_isolation ON mql_query_log")
    op.execute("ALTER TABLE mql_query_log DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS mql_query_log CASCADE")
