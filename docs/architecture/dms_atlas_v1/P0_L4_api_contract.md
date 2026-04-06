# P0 — Livrable 4 : Contrat API exhaustif

## 1. Source de vérité machine-readable

- **OpenAPI 3.1** exporté : [`ANNEX_A_openapi.json`](ANNEX_A_openapi.json) (généré depuis `main:app`).
- **Mesure** (2026-04-06) : **95** chemins, **103** opérations HTTP distinctes.

Tout schéma Pydantic complet par endpoint est **dans** ce JSON (`components.schemas`). Ce document ajoute la **couche sémantique** (permissions, rate limit, notes) non toujours présente dans les descriptions OpenAPI.

## 2. Regroupement par domaine (inventaire fonctionnel)

Les routeurs sont montés dans [`main.py`](../../main.py). Liste des familles :

| Domaine | Module / préfixe typique |
|---------|---------------------------|
| AUTH | [`src/auth_router.py`](../../src/auth_router.py) `/auth` |
| Health | [`src/api/health.py`](../../src/api/health.py) `/api/health` |
| Cases | [`src/api/cases.py`](../../src/api/cases.py) |
| Documents | [`src/api/documents.py`](../../src/api/documents.py) |
| Analysis | [`src/api/analysis.py`](../../src/api/analysis.py) |
| Extractions | [`src/api/routes/extractions.py`](../../src/api/routes/extractions.py) |
| Upload Couche A | [`src/couche_a/routers.py`](../../src/couche_a/routers.py) `/api/cases` |
| Regulatory profile | [`src/api/routes/regulatory_profile.py`](../../src/api/routes/regulatory_profile.py) |
| Committee | [`src/couche_a/committee/router.py`](../../src/couche_a/committee/router.py) |
| Scoring | [`src/couche_a/scoring/api.py`](../../src/couche_a/scoring/api.py) |
| Criteria | [`src/couche_a/criteria/router.py`](../../src/couche_a/criteria/router.py) |
| Pipeline A | [`src/couche_a/pipeline/router.py`](../../src/couche_a/pipeline/router.py) (optionnel) |
| Analysis summary | [`src/couche_a/analysis_summary/router.py`](../../src/couche_a/analysis_summary/router.py) (optionnel) |
| Evaluation M14 | [`src/api/routes/evaluation.py`](../../src/api/routes/evaluation.py) (optionnel) |
| Geo / Vendors / Mercuriale / Price check | Routers optionnels sous `src/geo`, `src/vendors`, `src/api/routers/*` |
| **Workspaces W1** | [`src/api/routers/workspaces.py`](../../src/api/routers/workspaces.py) `/api/workspaces` |
| **Market W2** | [`src/api/routers/market.py`](../../src/api/routers/market.py) |
| **Committee sessions W3** | [`src/api/routers/committee_sessions.py`](../../src/api/routers/committee_sessions.py) |
| Documents BLOC7 | [`src/api/routers/documents.py`](../../src/api/routers/documents.py) (préfixe committee PV) |
| M16 comparative | [`src/api/routers/m16_comparative.py`](../../src/api/routers/m16_comparative.py) |
| WebSocket | `/ws/workspace/{workspace_id}/events` — [`src/api/ws/workspace_events.py`](../../src/api/ws/workspace_events.py) |

### Routes canon mentionnées dans le mandat — statut

| Route mandat | Statut dans ce dépôt |
|--------------|----------------------|
| `GET .../cognitive-state` dédié | **Absent** — état cognitif inclus dans `GET /api/workspaces/{id}` |
| `POST .../hitl` | **Absent** sous ce chemin |
| `POST /agent/prompt` | **Absent** (cf. GAP_MATRIX J13) |
| `GET .../audit-replay` | **Absent** (J15) |

---

## 3. Authentification et permissions

- **JWT** : dépendance `get_current_user` — [`src/couche_a/auth/dependencies.py`](../../src/couche_a/auth/dependencies.py).
- **Workspace** : `require_workspace_access`, `require_workspace_permission` — [`src/couche_a/auth/workspace_access.py`](../../src/couche_a/auth/workspace_access.py).
- **Permissions nommées** (exemples utilisés) : `workspace.create`, `workspace.read`, `bundle.upload`, `committee.manage` — voir usages dans `workspaces` et migrations RBAC `075`.

---

## 4. Rate limiting

| Mécanisme | Détail |
|-----------|--------|
| **slowapi** (`src/ratelimit.py`) | Limiter Redis ou `memory://` ; défaut **`100/minute`** par IP si non `TESTING` |
| **Routes auth** | Décorateurs `@limiter.limit` sur `/auth/token` (5/min), `/auth/register` (3/h), `/auth/me` (60/min) — [`src/auth_router.py`](../../src/auth_router.py) |
| **Middleware Redis** | IP **100/min**, user **200/min** — [`src/couche_a/auth/middleware.py`](../../src/couche_a/auth/middleware.py) `RedisRateLimitMiddleware` |

---

## 5. État cognitif requis par endpoint

**NON IMPLÉMENTÉ** comme garde globale : aucun middleware ne bloque une route HTTP en fonction de E0–E6. Seules les **transitions de statut** appliquent `validate_transition`. Pour une matrice endpoint×E, considérer **« pas de restriction automatique »** sauf logique interne de la route (ex. scellement comité).

---

## 6. HTTP 501 documentés

[`main.py`](../../main.py) `OPENAPI_DESCRIPTION` mentionne des **501** volontaires (ex. `/api/scoring/calculate`, `/api/analyze` selon étape non livrée). Vérifier les `responses` par route dans **ANNEX_A**.

---

## 7. Exemples requête/réponse

Utiliser **ANNEX_A** (`paths.*.requestBody`, `paths.*.responses`) — génération garantit cohérence avec les modèles FastAPI actuels.

---

## 8. Limitations

- OpenAPI ne liste pas toujours les **permissions RBAC** par route : complément manuel futur ou enrichissement des `Depends` avec métadonnées.
- **Double application** : `main.py` racine peut coexister avec `src/api/main.py` dans certains déploiements — la vérité pour ce dépôt est **`main.py`** à la racine (point d’entrée Docker / uvicorn).
