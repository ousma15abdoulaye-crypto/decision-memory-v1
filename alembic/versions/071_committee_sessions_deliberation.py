"""071 - Committee sessions, members, deliberation events (V4.2.0)

Revision ID: 071_committee_sessions_deliberation
Revises: 070_supplier_bundles_documents
Create Date: 2026-04-04

Remplace les tables committee/committee_members/submission_registries du canon V4.1.0
par des entites workspace-first :
  - committee_sessions         : session de deliberation (FSM sealed irreversible)
  - committee_session_members  : composition CRUD (INV-W03)
  - committee_deliberation_events : journal append-only (INV-W01, INV-W03)

INV-R1 adapte : UNIQUE(workspace_id) sur committee_sessions
                = 1 workspace = 1 session comite.
INV-W01 : immuabilite actes — trigger fn_committee_session_sealed_final
           + trigger fn_reject_mutation sur deliberation_events.
INV-W04 : sealed et closed = irreversibles.

users.id = INTEGER (migration 004).

Reference : docs/freeze/DMS_V4.2.0_SCHEMA.sql lignes 291-422
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "071_committee_sessions_deliberation"
down_revision = "070_supplier_bundles_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS committee_sessions (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL REFERENCES process_workspaces(id),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),

            committee_type TEXT NOT NULL DEFAULT 'standard' CHECK (
                committee_type IN ('standard','humanitarian','simplified')
            ),
            min_members INTEGER NOT NULL DEFAULT 3,

            session_status TEXT NOT NULL DEFAULT 'draft' CHECK (
                session_status IN (
                    'draft','active','in_deliberation','sealed','closed'
                )
            ),

            activated_at           TIMESTAMPTZ,
            deliberation_opened_at TIMESTAMPTZ,
            sealed_at              TIMESTAMPTZ,
            closed_at              TIMESTAMPTZ,

            sealed_by    INTEGER REFERENCES users(id),
            seal_hash    TEXT,
            pv_snapshot  JSONB,

            UNIQUE(workspace_id),
            CONSTRAINT sealed_requires_timestamp CHECK (
                NOT (
                    session_status IN ('draft','active')
                    AND sealed_at IS NOT NULL
                )
            )
        )
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_committee_session_sealed_final()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.session_status = 'sealed'
               AND NEW.session_status NOT IN ('sealed','closed') THEN
                RAISE EXCEPTION
                    'Session % est scellee. Seule transition : sealed -> closed.',
                    OLD.id;
            END IF;
            IF OLD.session_status = 'closed' THEN
                RAISE EXCEPTION
                    'Session % est cloturee. Aucune transition.',
                    OLD.id;
            END IF;
            RETURN NEW;
        END;
        $$
        """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_committee_session_sealed ON committee_sessions"
    )
    op.execute("""
        CREATE TRIGGER trg_committee_session_sealed
            BEFORE UPDATE ON committee_sessions
            FOR EACH ROW EXECUTE FUNCTION fn_committee_session_sealed_final()
        """)

    op.execute("ALTER TABLE committee_sessions ENABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS cs_tenant_isolation ON committee_sessions")
    op.execute("""
        CREATE POLICY cs_tenant_isolation ON committee_sessions
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS committee_session_members (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id           UUID NOT NULL REFERENCES committee_sessions(id),
            workspace_id         UUID NOT NULL REFERENCES process_workspaces(id),
            tenant_id            UUID NOT NULL REFERENCES tenants(id),
            user_id              INTEGER NOT NULL REFERENCES users(id),

            role_in_committee TEXT NOT NULL CHECK (role_in_committee IN (
                'supply_chain','finance','budget_holder',
                'technical','security','pharma','observer','secretary'
            )),
            is_voting BOOLEAN NOT NULL DEFAULT TRUE,

            conflict_declared    BOOLEAN NOT NULL DEFAULT FALSE,
            conflict_detail      TEXT,
            conflict_declared_at TIMESTAMPTZ,

            delegate_name      TEXT,
            delegate_function  TEXT,
            delegation_reason  TEXT,

            joined_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            removed_at TIMESTAMPTZ,

            UNIQUE(session_id, user_id)
        )
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS committee_deliberation_events (
            id           BIGSERIAL PRIMARY KEY,
            session_id   UUID NOT NULL REFERENCES committee_sessions(id),
            workspace_id UUID NOT NULL REFERENCES process_workspaces(id),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),
            actor_id     INTEGER NOT NULL REFERENCES users(id),

            event_type TEXT NOT NULL CHECK (event_type IN (
                'session_activated',
                'deliberation_opened',
                'comment_added',
                'score_challenged',
                'clarification_requested',
                'conflict_declared',
                'member_added',
                'member_removed',
                'deliberation_closed',
                'session_sealed',
                'pv_generated',
                'session_closed'
            )),

            payload    JSONB NOT NULL DEFAULT '{}',
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_cde_append_only ON committee_deliberation_events"
    )
    op.execute("""
        CREATE TRIGGER trg_cde_append_only
            BEFORE DELETE OR UPDATE ON committee_deliberation_events
            FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation()
        """)

    op.execute("ALTER TABLE committee_deliberation_events ENABLE ROW LEVEL SECURITY")

    op.execute(
        "DROP POLICY IF EXISTS cde_tenant_isolation ON committee_deliberation_events"
    )
    op.execute("""
        CREATE POLICY cde_tenant_isolation ON committee_deliberation_events
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cde_session ON committee_deliberation_events(session_id, occurred_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS committee_deliberation_events CASCADE")
    op.execute("DROP TABLE IF EXISTS committee_session_members CASCADE")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_committee_session_sealed ON committee_sessions"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_committee_session_sealed_final()")
    op.execute("DROP TABLE IF EXISTS committee_sessions CASCADE")
