"""069 - Process workspaces, events, memberships (V4.2.0)

Revision ID: 069_process_workspaces_events_memberships
Revises: 068_create_tenants
Create Date: 2026-04-04

Cree les 3 tables fondamentales du paradigme workspace-first :
  - process_workspaces : entite racine (remplace cases)
  - workspace_events   : journal append-only (INV-W03, INV-W05)
  - workspace_memberships : composition CRUD (INV-W03)

Note decision users.id :
  users.id est INTEGER (migration 004 reelle).
  Les colonnes created_by et user_id referencent INTEGER users(id).
  La migration vers UUID est planifiee post-pilote (V4.2.1_PATCH).

Reference : docs/freeze/DMS_V4.2.0_SCHEMA.sql lignes 35-174
REGLE-12 : op.execute() uniquement.
INV-W04 : sealed irreversible via trigger fn_workspace_sealed_final.
INV-W03 : workspace_events append-only via fn_reject_mutation.
INV-W05 : colonnes NOT NULL sur workspace_events.
REGLE-W01 : RLS via app.tenant_id et app.is_admin.
"""

from __future__ import annotations

from alembic import op

revision = "069_process_workspaces_events_memberships"
down_revision = "068_create_tenants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE process_workspaces (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            created_by      INTEGER NOT NULL REFERENCES users(id),

            reference_code  TEXT NOT NULL,
            title           TEXT NOT NULL,
            process_type    TEXT NOT NULL CHECK (process_type IN (
                'devis_unique','devis_simple','devis_formel',
                'appel_offres_ouvert','rfp_consultance','contrat_direct'
            )),

            estimated_value      NUMERIC(15,2),
            currency             TEXT NOT NULL DEFAULT 'XOF',
            humanitarian_context TEXT NOT NULL DEFAULT 'none' CHECK (
                humanitarian_context IN ('none','cat1','cat2','cat3','cat4')
            ),
            min_offers_required  INTEGER NOT NULL DEFAULT 1,
            response_period_days INTEGER,
            sealed_bids_required BOOLEAN NOT NULL DEFAULT FALSE,
            committee_required   BOOLEAN NOT NULL DEFAULT FALSE,
            zone_id              VARCHAR(50) REFERENCES geo_master(id),
            category_id          TEXT REFERENCES procurement_categories(id),
            submission_deadline  TIMESTAMPTZ,
            profile_applied      TEXT,

            status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                'draft','assembling','assembled','in_analysis',
                'analysis_complete','in_deliberation',
                'sealed','closed','cancelled'
            )),

            procurement_file JSONB NOT NULL DEFAULT '{
                "pr": "absent", "rfq": "absent",
                "sealed_bids_opened": false, "offers_received": 0,
                "aco": "absent", "vcrn_all_verified": false,
                "contract": "absent", "po": "absent", "grn": "absent"
            }',

            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            assembled_at            TIMESTAMPTZ,
            analysis_started_at     TIMESTAMPTZ,
            deliberation_started_at TIMESTAMPTZ,
            sealed_at               TIMESTAMPTZ,
            closed_at               TIMESTAMPTZ,

            legacy_case_id TEXT,

            UNIQUE (tenant_id, reference_code)
        )
        """)

    op.execute("""
        ALTER TABLE process_workspaces ENABLE ROW LEVEL SECURITY
        """)

    op.execute("""
        CREATE POLICY pw_tenant_isolation ON process_workspaces
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute(
        "CREATE INDEX idx_pw_tenant_status ON process_workspaces(tenant_id, status)"
    )
    op.execute("CREATE INDEX idx_pw_zone ON process_workspaces(zone_id)")
    op.execute("CREATE INDEX idx_pw_created ON process_workspaces(created_at DESC)")

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_workspace_sealed_final()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status = 'sealed' AND NEW.status NOT IN ('sealed','closed') THEN
                RAISE EXCEPTION
                    'Workspace % est scelle. Seule transition : sealed -> closed.',
                    OLD.id;
            END IF;
            IF OLD.status = 'closed' THEN
                RAISE EXCEPTION
                    'Workspace % est cloture. Aucune transition.',
                    OLD.id;
            END IF;
            RETURN NEW;
        END;
        $$
        """)

    op.execute("""
        CREATE TRIGGER trg_workspace_sealed_final
            BEFORE UPDATE ON process_workspaces
            FOR EACH ROW EXECUTE FUNCTION fn_workspace_sealed_final()
        """)

    op.execute("""
        CREATE TABLE workspace_events (
            id             BIGSERIAL PRIMARY KEY,
            workspace_id   UUID NOT NULL REFERENCES process_workspaces(id),
            tenant_id      UUID NOT NULL REFERENCES tenants(id),
            event_type     TEXT NOT NULL,
            actor_id       INTEGER NOT NULL REFERENCES users(id),
            actor_type     TEXT NOT NULL CHECK (actor_type IN ('user','service','agent')),
            payload        JSONB NOT NULL DEFAULT '{}',
            schema_version INTEGER NOT NULL DEFAULT 1,
            emitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute("""
        CREATE TRIGGER trg_workspace_events_append_only
            BEFORE DELETE OR UPDATE ON workspace_events
            FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation()
        """)

    op.execute("""
        ALTER TABLE workspace_events ENABLE ROW LEVEL SECURITY
        """)

    op.execute("""
        CREATE POLICY we_tenant_isolation ON workspace_events
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute(
        "CREATE INDEX idx_we_workspace_time ON workspace_events(workspace_id, emitted_at)"
    )
    op.execute(
        "CREATE INDEX idx_we_tenant_type ON workspace_events(tenant_id, event_type)"
    )
    op.execute("CREATE INDEX idx_we_emitted ON workspace_events(emitted_at DESC)")

    op.execute("""
        CREATE TABLE workspace_memberships (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL REFERENCES process_workspaces(id),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),
            user_id      INTEGER NOT NULL REFERENCES users(id),
            role         TEXT NOT NULL,
            granted_by   INTEGER NOT NULL REFERENCES users(id),
            granted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at   TIMESTAMPTZ,
            UNIQUE(workspace_id, user_id, role)
        )
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace_memberships CASCADE")
    op.execute("DROP TABLE IF EXISTS workspace_events CASCADE")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_workspace_sealed_final ON process_workspaces"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_workspace_sealed_final()")
    op.execute("DROP TABLE IF EXISTS process_workspaces CASCADE")
