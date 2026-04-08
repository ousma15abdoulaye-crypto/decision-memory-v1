"""091 — Corrige user_tenants (placeholders) et provisionne user_tenant_roles manquants.

Revision ID: 091_fix_user_tenant_provisioning
Revises: 090_v51_extraction_jobs_langfuse_trace

Données : remplace ``tenant-<id>`` par l'UUID du tenant par défaut (code sci_mali ou
premier tenant actif). Insère les lignes ``user_tenant_roles`` alignées sur la logique
de la migration 075 (rbac_roles).

Downgrade : no-op (correction de données).

REGLE-12 : op.execute() uniquement.

Audit lecture seule recommandé avant ``alembic upgrade head``::

    SELECT COUNT(*) FROM user_tenants
    WHERE tenant_id ~ '^tenant-[0-9]+$';

    SELECT ut.user_id, ut.tenant_id,
           ut.tenant_id ~ '^tenant-[0-9]+$' AS is_legacy_placeholder,
           EXISTS (
               SELECT 1 FROM user_tenant_roles utr
               WHERE utr.user_id = ut.user_id
           ) AS has_rbac_row
    FROM user_tenants ut
    LIMIT 50;

    SELECT code FROM rbac_roles ORDER BY code;
"""

from __future__ import annotations

from alembic import op

revision = "091_fix_user_tenant_provisioning"
down_revision = "090_v51_extraction_jobs_langfuse_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        WITH def_tenant AS (
            SELECT id FROM public.tenants
            WHERE code = 'sci_mali' AND is_active = TRUE
            LIMIT 1
        ),
        fallback AS (
            SELECT id FROM public.tenants
            WHERE is_active = TRUE
            ORDER BY created_at
            LIMIT 1
        ),
        pick AS (
            SELECT COALESCE((SELECT id FROM def_tenant), (SELECT id FROM fallback)) AS id
        )
        UPDATE public.user_tenants ut
        SET tenant_id = (SELECT id::text FROM pick)
        WHERE ut.tenant_id ~ '^tenant-[0-9]+$'
          AND EXISTS (SELECT 1 FROM pick WHERE id IS NOT NULL)
        """)

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


def downgrade() -> None:
    pass
