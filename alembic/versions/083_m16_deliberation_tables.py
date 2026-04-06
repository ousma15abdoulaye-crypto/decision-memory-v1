"""083 — M16 délibération (threads, messages append-only, notes, historique)

Revision ID: 083_m16_deliberation_tables
Revises: 082_m16_criterion_assessments

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
"""

from __future__ import annotations

from alembic import op

revision = "083_m16_deliberation_tables"
down_revision = "082_m16_criterion_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS deliberation_threads (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id           UUID NOT NULL REFERENCES tenants(id),
            committee_session_id UUID REFERENCES committee_sessions(id) ON DELETE SET NULL,
            title               TEXT NOT NULL DEFAULT '',
            thread_status       TEXT NOT NULL DEFAULT 'open' CHECK (
                thread_status IN ('open','archived')
            ),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dt_workspace ON deliberation_threads(workspace_id)"
    )

    op.execute("ALTER TABLE deliberation_threads ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS dt_tenant_isolation ON deliberation_threads")
    op.execute("""
        CREATE POLICY dt_tenant_isolation ON deliberation_threads
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS deliberation_messages (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            thread_id       UUID NOT NULL REFERENCES deliberation_threads(id) ON DELETE CASCADE,
            workspace_id    UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            author_user_id  INTEGER NOT NULL REFERENCES users(id),
            body            TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dm_thread ON deliberation_messages(thread_id, created_at)"
    )

    op.execute("ALTER TABLE deliberation_messages ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS dm_tenant_isolation ON deliberation_messages")
    op.execute("""
        CREATE POLICY dm_tenant_isolation ON deliberation_messages
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_dm_append_only ON deliberation_messages"
    )
    op.execute("""
        CREATE TRIGGER trg_dm_append_only
            BEFORE DELETE OR UPDATE ON deliberation_messages
            FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation()
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS clarification_requests (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id               UUID NOT NULL REFERENCES tenants(id),
            criterion_assessment_id UUID NOT NULL REFERENCES criterion_assessments(id) ON DELETE CASCADE,
            status                  TEXT NOT NULL DEFAULT 'open' CHECK (
                status IN ('open','answered','withdrawn')
            ),
            requested_by            INTEGER REFERENCES users(id),
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at             TIMESTAMPTZ
        )
        """)

    op.execute("ALTER TABLE clarification_requests ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS clr_tenant_isolation ON clarification_requests")
    op.execute("""
        CREATE POLICY clr_tenant_isolation ON clarification_requests
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS criterion_assessment_history (
            id                      BIGSERIAL PRIMARY KEY,
            criterion_assessment_id UUID NOT NULL REFERENCES criterion_assessments(id) ON DELETE CASCADE,
            workspace_id            UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id               UUID NOT NULL REFERENCES tenants(id),
            changed_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actor_id                INTEGER REFERENCES users(id),
            old_status              TEXT,
            new_status              TEXT,
            payload                 JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cah_ca ON criterion_assessment_history(criterion_assessment_id)"
    )

    op.execute("ALTER TABLE criterion_assessment_history ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS cah_tenant_isolation ON criterion_assessment_history")
    op.execute("""
        CREATE POLICY cah_tenant_isolation ON criterion_assessment_history
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_cah_append_only ON criterion_assessment_history"
    )
    op.execute("""
        CREATE TRIGGER trg_cah_append_only
            BEFORE DELETE OR UPDATE ON criterion_assessment_history
            FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation()
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS validated_analytical_notes (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            UUID NOT NULL REFERENCES process_workspaces(id) ON DELETE CASCADE,
            tenant_id               UUID NOT NULL REFERENCES tenants(id),
            criterion_assessment_id UUID NOT NULL REFERENCES criterion_assessments(id) ON DELETE CASCADE,
            source_message_id       UUID NOT NULL REFERENCES deliberation_messages(id),
            note_body               TEXT NOT NULL,
            validated_by            INTEGER REFERENCES users(id),
            validated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute("ALTER TABLE validated_analytical_notes ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS van_tenant_isolation ON validated_analytical_notes")
    op.execute("""
        CREATE POLICY van_tenant_isolation ON validated_analytical_notes
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS van_tenant_isolation ON validated_analytical_notes")
    op.execute("ALTER TABLE validated_analytical_notes DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS validated_analytical_notes CASCADE")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_cah_append_only ON criterion_assessment_history"
    )
    op.execute("DROP POLICY IF EXISTS cah_tenant_isolation ON criterion_assessment_history")
    op.execute("ALTER TABLE criterion_assessment_history DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS criterion_assessment_history CASCADE")

    op.execute("DROP POLICY IF EXISTS clr_tenant_isolation ON clarification_requests")
    op.execute("ALTER TABLE clarification_requests DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS clarification_requests CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_dm_append_only ON deliberation_messages")
    op.execute("DROP POLICY IF EXISTS dm_tenant_isolation ON deliberation_messages")
    op.execute("ALTER TABLE deliberation_messages DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS deliberation_messages CASCADE")

    op.execute("DROP POLICY IF EXISTS dt_tenant_isolation ON deliberation_threads")
    op.execute("ALTER TABLE deliberation_threads DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS deliberation_threads CASCADE")
