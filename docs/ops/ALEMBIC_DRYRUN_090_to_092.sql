-- =============================================================================
-- DRY-RUN ALEMBIC (offline --sql) — delta EXACT prod → dépôt
--
-- PROD (constat AO / mandat V51-001, aligné 2026-04-09) :
--   alembic_version.version_num = 090_v51_extraction_jobs_langfuse_trace
--
-- Ce fichier = SQL émis pour enchaîner 090 → 091 → 092 (sans l’exécuter ici).
-- Après apply réel : head attendu = 092_workspace_access_model_v2
--
-- Regénérer (depuis la racine du repo) :
--   set DATABASE_URL=postgresql+psycopg://USER:PASS@HOST:PORT/DB
--   python -m alembic upgrade 090_v51_extraction_jobs_langfuse_trace:092_workspace_access_model_v2 --sql
--
-- Ne pas exécuter sur prod sans GO CTO + pre-check `alembic current` = 090_…
-- =============================================================================

BEGIN;

-- Running upgrade 090_v51_extraction_jobs_langfuse_trace -> 091_fix_user_tenant_provisioning

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
          AND EXISTS (SELECT 1 FROM pick WHERE id IS NOT NULL);

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
        );

UPDATE alembic_version SET version_num='091_fix_user_tenant_provisioning' WHERE alembic_version.version_num = '090_v51_extraction_jobs_langfuse_trace';

-- Running upgrade 091_fix_user_tenant_provisioning -> 092_workspace_access_model_v2

UPDATE public.user_tenants ut
        SET tenant_id = t.id::text
        FROM public.tenants t
        WHERE t.code = 'sci_mali'
          AND t.is_active = TRUE
          AND ut.tenant_id ~ '^tenant-[0-9]+$';

UPDATE public.user_tenants ut
        SET tenant_id = sub.id_txt
        FROM (
            SELECT id::text AS id_txt
            FROM public.tenants
            WHERE is_active = TRUE
            ORDER BY created_at ASC
            LIMIT 1
        ) sub
        WHERE ut.tenant_id ~ '^tenant-[0-9]+$';

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
        );

ALTER TABLE public.workspace_memberships
        ADD COLUMN IF NOT EXISTS coi_declared BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.workspace_memberships
        ADD COLUMN IF NOT EXISTS coi_declared_at TIMESTAMPTZ;

ALTER TABLE public.workspace_memberships
        ADD COLUMN IF NOT EXISTS coi_note TEXT;

DO $wm_backfill$
        DECLARE
            rec RECORD;
        BEGIN
            FOR rec IN
                SELECT w.id AS wid, w.tenant_id AS tid
                FROM public.process_workspaces w
                WHERE w.status IS DISTINCT FROM 'sealed'
                ORDER BY w.tenant_id, w.id
            LOOP
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
                WHERE w.id = rec.wid
                  AND w.tenant_id = rec.tid
                  AND NOT EXISTS (
                      SELECT 1 FROM public.workspace_memberships wm
                      WHERE wm.workspace_id = w.id
                        AND wm.user_id = u.id
                        AND wm.revoked_at IS NULL
                  )
                ON CONFLICT (workspace_id, user_id, role) DO NOTHING;
            END LOOP;
        END
        $wm_backfill$;

UPDATE alembic_version SET version_num='092_workspace_access_model_v2' WHERE alembic_version.version_num = '091_fix_user_tenant_provisioning';

COMMIT;

