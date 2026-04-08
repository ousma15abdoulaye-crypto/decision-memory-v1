"""088 — V5.1 assessment_comments : commentaires/flags comité délibération

Revision ID: 088_v51_assessment_comments
Revises: 087_v51_mql_query_log

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
Canon V5.1.0 INV-S04 : content et is_flag immutables (trigger DB).
users.id = INTEGER (migration 004).
"""

from __future__ import annotations

from alembic import op

revision = "088_v51_assessment_comments"
down_revision = "087_v51_mql_query_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS assessment_comments (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id               UUID NOT NULL REFERENCES tenants(id),
            criterion_assessment_id UUID REFERENCES criterion_assessments(id) ON DELETE CASCADE,
            author_user_id          INTEGER NOT NULL REFERENCES users(id),
            content                 TEXT NOT NULL,
            comment_type            TEXT NOT NULL DEFAULT 'comment'
                                    CHECK (comment_type IN ('comment', 'flag', 'question')),
            is_flag                 BOOLEAN NOT NULL DEFAULT FALSE,
            resolved                BOOLEAN NOT NULL DEFAULT FALSE,
            resolved_by             INTEGER REFERENCES users(id),
            resolved_at             TIMESTAMPTZ,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ac_workspace "
        "ON assessment_comments(workspace_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ac_criterion "
        "ON assessment_comments(criterion_assessment_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ac_flag "
        "ON assessment_comments(workspace_id, is_flag, resolved) "
        "WHERE is_flag = TRUE"
    )

    op.execute("ALTER TABLE assessment_comments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_comments FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS ac_tenant_isolation ON assessment_comments")
    op.execute("""
        CREATE POLICY ac_tenant_isolation ON assessment_comments
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_ac_content_immutable()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF NEW.content IS DISTINCT FROM OLD.content
                   OR NEW.is_flag IS DISTINCT FROM OLD.is_flag THEN
                    RAISE EXCEPTION
                        'assessment_comments: content et is_flag sont immutables (INV-S04).';
                END IF;
            END IF;
            RETURN NEW;
        END $$
    """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_ac_content_immutable ON assessment_comments"
    )
    op.execute("""
        CREATE TRIGGER trg_ac_content_immutable
            BEFORE UPDATE ON assessment_comments
            FOR EACH ROW EXECUTE FUNCTION fn_ac_content_immutable()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_ac_content_immutable ON assessment_comments"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_ac_content_immutable()")
    op.execute("DROP POLICY IF EXISTS ac_tenant_isolation ON assessment_comments")
    op.execute("ALTER TABLE assessment_comments DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS assessment_comments CASCADE")
