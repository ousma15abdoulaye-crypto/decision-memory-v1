# Inventaire des gardes — surface V5.1 + workspace

**Objectif** : liste opposable des mécanismes d’authz sur les routes montées par le bundle workspace / V5.1 et les routers W1/W3 voisins, pour éviter les oublis au montage (`main:app` vs harness).

## Primitives

| Primitive | Fichier | Usage typique |
|-----------|---------|----------------|
| `get_current_user` | `src/couche_a/auth/dependencies.py` | JWT obligatoire (sauf routes publiques). |
| `require_workspace_access` | `src/couche_a/auth/workspace_access.py` | Tenant + accès au workspace (lecture / membership). |
| `require_workspace_permission` | idem | Permission métier (`matrix.read`, `member.invite`, …). |
| `guard` (async) | `src/auth/guard.py` | Membership + permission + **blocage écriture si workspace scellé/clos** (asyncpg + RLS). **M-CTO-V53-C** : `WORKSPACE_ACCESS_JWT_FALLBACK` n’autorise **pas** les permissions d’écriture (`WRITE_PERMISSIONS` dans `guard.py`) sans membership DB. |
| `require_case_access_dep` | `src/couche_a/auth/case_access.py` | Routes case-scoped (`/api/cases/...`). |
| RBAC JWT `ROLE_PERMISSIONS` | `src/auth/permissions.py` | Ex. `mql.internal` sur `POST /api/mql/stream`. |

## Bundle V5.1 (`mount_v51_workspace_http_and_ws`)

| Route (préfixe) | Garde principale | Remarque |
|------------------|------------------|----------|
| `GET /api/dashboard` | `get_current_user` + filtre `tenant_id` | Pas de `workspace_id` ; liste tous les workspaces du tenant. |
| `POST /api/agent/prompt` | `get_current_user` ; si `workspace_id` → `guard(..., "agent.query")` | Stream SSE. |
| `POST /api/mql/stream` | `get_current_user` + rôle `mql.internal` ou `system.admin` | N’utilise pas `execute_mql_query` mocké dans les tests d’intégration réels. |
| `POST /api/m12/corrections` | `get_current_user` + `audit.read` / `mql.internal` / `system.admin` | Append ``m12_correction_log`` (M-CTO-V53-G). |
| `GET /api/m12/corrections/recent` | idem | Lecture audit. |
| `GET /api/workspaces/{id}/event-timeline` | `require_workspace_access` | Journal ``workspace_events`` (M-CTO-V53-F). |
| `GET /api/workspaces/{id}/members` | `require_workspace_permission(..., "matrix.read")` | |
| `POST /api/workspaces/{id}/members` | `require_workspace_permission(..., "member.invite")` | 409 si membership actif. |
| `DELETE /api/workspaces/{id}/members/{user_id}` | `require_workspace_permission(..., "member.revoke")` | Interdit auto-révocation. |
| WebSocket `/ws/workspace/{id}/events` | Auth + `require_workspace_access` (voir `src/api/ws/workspace_events.py`) | Non listé dans OpenAPI. |

## Routers workspace W1 / W3 (hors bundle mais même préfixe `/api/workspaces`)

Référence : [`src/api/routers/workspaces.py`](../../src/api/routers/workspaces.py), [`src/api/routers/workspaces_comments.py`](../../src/api/routers/workspaces_comments.py), [`src/api/routers/committee_sessions.py`](../../src/api/routers/committee_sessions.py).

Patterns récurrents :

- `require_workspace_access` pour lecture / actions générales sur un `workspace_id`.
- `require_workspace_permission(..., "bundle.upload")` pour uploads liés au bundle.
- `require_workspace_permission(..., "committee.manage")` pour scellage / session comité.
- `require_workspace_comment_permission` pour commentaires (CDE).

## Mise à jour

Toute nouvelle route sous `/api/workspaces`, `/api/dashboard`, `/api/agent`, `/api/mql` doit être répertoriée ici et dans le smoke [`tests/test_main_app_parity_smoke.py`](../../tests/test_main_app_parity_smoke.py) si elle est user-facing en production.
