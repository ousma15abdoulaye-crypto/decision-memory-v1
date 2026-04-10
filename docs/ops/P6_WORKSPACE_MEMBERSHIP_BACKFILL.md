# P6.0 — Backfill workspace_memberships (one-shot)

Objectif : corriger tous les workspaces sans membership en prod, sans migration Alembic.

## Prerequis
- Railway CLI configuree et connectee.
- Acces lecture/execute sur la base prod.
- Executer en fenetre controlee (ops).

## Verification avant
```sql
SELECT pw.id, pw.reference_code, pw.status, pw.created_at,
       pw.created_by, pw.tenant_id,
       u.email AS creator_email
FROM process_workspaces pw
LEFT JOIN users u ON u.id = pw.created_by
WHERE pw.id NOT IN (
  SELECT DISTINCT workspace_id FROM workspace_memberships
)
ORDER BY pw.created_at;
```

## Backfill (Option A — created_by present)
```sql
INSERT INTO workspace_memberships (
  id,
  workspace_id,
  tenant_id,
  user_id,
  role,
  granted_by,
  granted_at
)
SELECT
  gen_random_uuid(),
  pw.id,
  pw.tenant_id,
  pw.created_by,
  'supply_chain',
  pw.created_by,
  NOW()
FROM process_workspaces pw
WHERE pw.id NOT IN (
  SELECT DISTINCT workspace_id FROM workspace_memberships
)
AND pw.created_by IS NOT NULL
ON CONFLICT (workspace_id, user_id, role) DO NOTHING;
```

## Verification apres
```sql
SELECT COUNT(1) AS remaining_orphans
FROM process_workspaces pw
WHERE pw.id NOT IN (
  SELECT DISTINCT workspace_id FROM workspace_memberships
);
```

Attendu : `remaining_orphans = 0`.

