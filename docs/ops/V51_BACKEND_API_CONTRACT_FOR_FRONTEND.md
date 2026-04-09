# Contrat API backend V5.1 — référence frontend

**Statut** : opérationnel (baseline mandat fermeture V5.1)  
**Public** : équipe frontend `frontend-v51` + intégrateurs API.

## Authentification

- JWT Bearer (claims `tenant_id`, `user_id`, `role`) sur les routes protégées.
- Login JSON : `POST /api/auth/login` (corps JSON — voir OpenAPI `main:app`).

## Workspace — cadre d’évaluation (BLOC5 / Sprint 2)

**Contrat cible (NL-10 / Sprint 2)** — à aligner sur l’implémentation lorsque les query params seront branchés côté handler :

| Élément | Valeur |
|--------|--------|
| Méthode + chemin | `GET /api/workspaces/{workspace_id}/evaluation-frame` |
| Query optionnelle `domain` | Code domaine métier (`?domain={code}`) pour filtrer / surcharger la projection du cadre. |
| Query optionnelle `mode` | `mode=financial` pour la vue financière du cadre (projection dédiée). |
| Garde | `Depends(get_current_user)` + `require_workspace_access(workspace_id, user)` (au minimum lecture workspace tenant + membership). |

**État actuel dépôt** : la route expose le cadre assemblé sans `domain` / `mode` dans la signature FastAPI ; le contrat ci-dessus fige l’**intention produit** pour éviter la dérive entre équipes.

## Bundle V5.1 monté via factory

Toujours présent sur `main:app` et `src.api.main:app` (via [`src/api/dms_v51_mount.py`](../../src/api/dms_v51_mount.py)) :

- `GET /api/dashboard` — pilotage multi-workspace (tenant JWT).
- `POST /api/agent/prompt` — agent SSE ; si `workspace_id` est fourni, garde async `guard(..., "agent.query")`.
- `POST /api/mql/stream` — usage interne ; JWT + permission `mql.internal` ou `system.admin`.
- `GET|POST|DELETE …/api/workspaces/{id}/members` — permissions `matrix.read`, `member.invite`, `member.revoke`.
- WebSocket : `/ws/workspace/{workspace_id}/events` et alias `/ws/workspace/{workspace_id}`.

## Références code

- [`src/api/app_factory.py`](../../src/api/app_factory.py) — `create_railway_app` / `create_modular_app`
- [`src/api/routers/workspaces.py`](../../src/api/routers/workspaces.py) — `evaluation-frame`
- [`docs/ops/V51_ROUTE_GUARD_INVENTORY.md`](V51_ROUTE_GUARD_INVENTORY.md) — détail des gardes
- [`docs/adr/ADR-V51-WORKSPACE-ROLE-PERMISSION-MAP.md`](../adr/ADR-V51-WORKSPACE-ROLE-PERMISSION-MAP.md) — matrice rôles × permissions
