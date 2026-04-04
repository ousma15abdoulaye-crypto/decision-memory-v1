"""072 - Vendor market signals and watchlist (V4.2.0)

Revision ID: 072_vendor_market_signals_watchlist
Revises: 071_committee_sessions_deliberation
Create Date: 2026-04-04

Cree les tables du module W2 Market Intelligence (hors processus) :
  - vendor_market_signals  : signaux fournisseurs append-only (INV-W03)
  - market_watchlist_items : liste de surveillance CRUD

Ces tables sont accessibles SANS workspace_id — zone W2 independante.
INV-R6 adapte : seul ARQ projector ecrit dans ces tables apres scellement.

users.id = INTEGER (migration 004).

Reference : docs/freeze/DMS_V4.2.0_SCHEMA.sql lignes 432-463
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "072_vendor_market_signals_watchlist"
down_revision = "071_committee_sessions_deliberation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS vendor_market_signals (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL REFERENCES tenants(id),
            vendor_id           UUID NOT NULL REFERENCES vendors(id),
            signal_type TEXT NOT NULL CHECK (signal_type IN (
                'reliability_update','price_anchor_update',
                'compliance_flag','blacklist_alert',
                'watchlist_trigger','performance_note'
            )),
            payload             JSONB NOT NULL,
            source_workspace_id UUID REFERENCES process_workspaces(id),
            generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

    op.execute("DROP TRIGGER IF EXISTS trg_vms_append_only ON vendor_market_signals")
    op.execute("""
        CREATE TRIGGER trg_vms_append_only
            BEFORE DELETE OR UPDATE ON vendor_market_signals
            FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation()
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS market_watchlist_items (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL REFERENCES tenants(id),
            created_by          INTEGER NOT NULL REFERENCES users(id),
            item_type TEXT NOT NULL CHECK (item_type IN ('item_key','vendor')),
            item_ref            TEXT NOT NULL,
            alert_threshold_pct NUMERIC(5,2),
            is_active           BOOLEAN NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS market_watchlist_items CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_vms_append_only ON vendor_market_signals")
    op.execute("DROP TABLE IF EXISTS vendor_market_signals CASCADE")
