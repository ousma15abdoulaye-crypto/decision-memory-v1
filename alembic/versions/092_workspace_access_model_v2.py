"""092 — Accès workspace V2 : user_tenants, user_tenant_roles, workspace_memberships.

Revision ID: 092_workspace_access_model_v2
Revises: 091_fix_user_tenant_provisioning

Aligné sur le schéma réel DMS :
  - ``process_workspaces`` (pas ``workspaces``)
  - ``users.id`` INTEGER (pas UUID)
  - ``workspace_memberships.role`` TEXT, UNIQUE (workspace_id, user_id, role)
  - ``user_tenant_roles`` : ``granted_at`` (pas ``created_at``)
  - RLS existant : ``app.tenant_id`` (cf. migration 089)

Downgrade : no-op (données + colonnes optionnelles).

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "092_workspace_access_model_v2"
down_revision = "091_fix_user_tenant_provisioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── STEP 1 — Placeholders user_tenants → UUID réel (idempotent) ─────────
    op.execute("""
        UPDATE public.user_tenants ut
        SET tenant_id = t.id::text
        FROM public.tenants t
        WHERE t.code = 'sci_mali'
          AND t.is_active = TRUE
          AND ut.tenant_id ~ '^tenant-[0-9]+$'
        """)

    op.execute("""
        UPDATE public.user_tenants ut
        SET tenant_id = sub.id_txt
        FROM (
            SELECT id::text AS id_txt
            FROM public.tenants
            WHERE is_active = TRUE
            ORDER BY created_at ASC
            LIMIT 1
        ) sub
        WHERE ut.tenant_id ~ '^tenant-[0-9]+$'
        """)

    # ── STEP 2 — user_tenant_roles manquants (granted_at = défaut DB) ───────
    op.execute("""
        INSERT INTO public.user_tenant_roles (user_id, tenant_id, role_id)
        SELECT u.id, t.id, r.id
        FROM public.users u
        JOIN public.user_tenants ut ON ut.user_id = u.id
        JOIN public.tenants t ON (t.id::text = ut.tenant_id OR t.code = ut.tenant_id)
        JOIN public.roles old_r ON old_r.id = u.role_id
        JOIN public.rbac_roles r ON r.code = CASE
            WHEN u.is_superuser = TRUE THEN 'supply_chain_admin'
            WHEN old_r.name = 'admin' THEN 'supply_chain_admin'
            WHEN old_r.name = 'procurement_officer' THEN 'procurement_officer'
            WHEN old_r.name = 'viewer' THEN 'market_analyst'
            ELSE 'market_analyst'
        END
        WHERE NOT EXISTS (
            SELECT 1 FROM public.user_tenant_roles utr
            WHERE utr.user_id = u.id
              AND utr.tenant_id = t.id
              AND utr.role_id = r.id
        )
        """)

    # ── STEP 3 — Colonnes COI (table 069 déjà créée ; pas de recréation) ───
    op.execute("""
        ALTER TABLE public.workspace_memberships
        ADD COLUMN IF NOT EXISTS coi_declared BOOLEAN NOT NULL DEFAULT FALSE
        """)
    op.execute("""
        ALTER TABLE public.workspace_memberships
        ADD COLUMN IF NOT EXISTS coi_declared_at TIMESTAMPTZ
        """)
    op.execute("""
        ALTER TABLE public.workspace_memberships
        ADD COLUMN IF NOT EXISTS coi_note TEXT
        """)

    # ── STEP 4 — Backfill memberships (un rôle par user/workspace) ───────
    op.execute("""
        INSERT INTO public.workspace_memberships (
            workspace_id, tenant_id, user_id, role, granted_by
        )
        SELECT
            w.id,
            w.tenant_id,
            u.id,
            CASE
                WHEN u.is_superuser = TRUE OR r.name = 'admin'
                    THEN 'procurement_lead'
                WHEN r.name = 'procurement_officer'
                    THEN 'committee_member'
                ELSE 'observer'
            END,
            u.id
        FROM public.process_workspaces w
        JOIN public.tenants tw ON tw.id = w.tenant_id
        JOIN public.user_tenants ut
            ON (ut.tenant_id = tw.id::text OR ut.tenant_id = tw.code)
        JOIN public.users u ON u.id = ut.user_id
        LEFT JOIN public.roles r ON r.id = u.role_id
        WHERE w.status IS DISTINCT FROM 'sealed'
          AND NOT EXISTS (
              SELECT 1 FROM public.workspace_memberships wm
              WHERE wm.workspace_id = w.id
                AND wm.user_id = u.id
                AND wm.revoked_at IS NULL
          )
        ON CONFLICT (workspace_id, user_id, role) DO NOTHING
        """)


def downgrade() -> None:
    pass
