# P2 — Livrable 7 : Couche sécurité

## 7.1 Authentification

| Sujet | Implémentation |
|-------|----------------|
| Flow | OAuth2 password — `POST /auth/token` ([`src/auth_router.py`](../../src/auth_router.py)) |
| Algorithme | **HS256** — [`src/couche_a/auth/jwt_handler.py`](../../src/couche_a/auth/jwt_handler.py) `ALGORITHM` |
| Access TTL | `JWT_ACCESS_TTL_MINUTES` (défaut **30** min) |
| Refresh TTL | `JWT_REFRESH_TTL_DAYS` (défaut **7** j) — utilisé si flux refresh implémenté dans le même module |
| Secret | `SECRET_KEY` ou `JWT_SECRET` — **obligatoire** pour émission |
| Stockage client | **NON TRANCHÉ** par le backend (comportement navigateur / app mobile) |
| Invalidation | Table `token_blacklist` — migration [`037_security_baseline.py`](../../alembic/versions/037_security_baseline.py) ; voir tests [`tests/auth/test_token_blacklist.py`](../../tests/auth/test_token_blacklist.py) |

---

## 7.2 Autorisation

| Sujet | Détail |
|-------|--------|
| RBAC SQL | `rbac_permissions`, `rbac_roles`, `rbac_role_permissions`, `user_tenant_roles` — [`075_rbac_permissions_roles.py`](../../alembic/versions/075_rbac_permissions_roles.py) |
| Workspace | `workspace_memberships` + permission `workspace.read` — [`workspace_access.py`](../../src/couche_a/auth/workspace_access.py) |
| Rôles JWT | `VALID_ROLES` dans `jwt_handler` : `admin`, `manager`, `buyer`, `viewer`, `auditor` |
| Rôles différents par workspace | **Partiel** : membership explicite par workspace ; sinon permission tenant-level |

**Middleware** : [`TenantContextMiddleware`](../../src/couche_a/auth/middleware.py) pose `tenant_id` pour RLS via claims **non vérifiés** — commentaire de sécurité : `is_admin` forcé False jusqu’à `get_current_user`.

---

## 7.3 Row-Level Security

- **Propagation `tenant_id`** : [`src/db/tenant_context.py`](../../src/db/tenant_context.py) + middleware.
- **Pool async / sync** : pools dédiés — [`src/db/pool.py`](../../src/db/pool.py), [`src/db/async_pool.py`](../../src/db/async_pool.py).
- **Tests isolation** : [`tests/integration/test_rls_dm_app_cross_tenant.py`](../../tests/integration/test_rls_dm_app_cross_tenant.py), `tests/db_integrity/test_workspace_rls.py`.

Politiques SQL : **par migration** (`051`–`055`, …) — pas recopiées ici.

---

## 7.4 Secrets / variables

Lister les noms depuis [`.env.example`](../../.env.example) si présent ; sinon documentation ops. **Ne jamais committer de valeurs.**

---

## 7.5 Audit

| Élément | Source |
|---------|--------|
| `audit_log` | [`038_audit_hash_chain.py`](../../alembic/versions/038_audit_hash_chain.py) |
| Événements workspace | `workspace_events` |
| Accès lecture | **NON TRANCHÉ** (rôle `auditor` + procédure org) |

---

## Limitations

- **INV-W07** : implémentation WS documentée comme diffusion `workspace_events` — écart possible vs projection stricte `dms_event_index` seul — voir [`GAP_MATRIX`](../../audits/GAP_MATRIX_V431_J1_J17_AND_INVARIANTS.md).
