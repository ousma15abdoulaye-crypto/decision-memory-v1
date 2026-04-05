# Diagnostic HTTP 500 — `POST /api/workspaces` et `GET /api/market/overview`

**Date** : 2026-04-05  
**Contexte** : smokes BLOC 3 sur `https://decision-memory-v1-production.up.railway.app` — auth OK, **500** sur création workspace et overview marché.  
**Logs Railway** : non consultables depuis l’agent (Dashboard humain). Diagnostic par **reproduction schéma DB réel** + **lecture code**.

---

## Synthèse des causes

| # | Endpoint | Cause identifiée | Type mandat |
|---|----------|------------------|---------------|
| 1 | `GET /api/market/overview` | La route sélectionnait des **colonnes inexistantes** sur `public.market_signals_v2` (`item_key`, `signal_type`, `unit_price`, `currency`, `market_zone`, `collected_at`). Le schéma réel (migration `043_market_signals_v11`) expose notamment `item_id`, `zone_id`, `price_avg`, `alert_level`, `created_at` / `updated_at`. PostgreSQL lève une erreur du type **`column ms.item_key does not exist`** → FastAPI **500**. | **CAUSE E** (vue/requête incompatible avec tables post-M9) |
| 2 | `POST /api/workspaces` | `user_tenants.tenant_id` est encore du **TEXT legacy** (`tenant-{user_id}`, cf. `051_cases_tenant_user_tenants_rls` + `create_user` dans [`auth_helpers.py`](src/api/auth_helpers.py)). `process_workspaces.tenant_id` est un **UUID** avec **FK vers `tenants(id)`** (migration `069`). La valeur `tenant-12` **n’est pas un UUID valide** pour la colonne → erreur SQL (**invalid input syntax for type uuid** ou FK) → **500**. | **CAUSE B** (décalage schéma TEXT legacy vs UUID V4.2.0), aligné REGLE-W01 après résolution |

---

## Preuves techniques (hors logs Railway)

### Schéma `market_signals_v2` (extrait)

Vérifié via `information_schema.columns` sur la base Railway (probe agent) : présence de `item_id`, `price_avg`, `alert_level`, `zone_id`, etc. — **pas** de `item_key` / `collected_at`.

### Cohérence `tenant_id`

- [`tenants`](alembic/versions/068_create_tenants.py) : ligne seed `code = 'sci_mali'` avec `id` UUID.
- [`user_tenants`](alembic/versions/051_cases_tenant_user_tenants_rls.py) : `tenant_id TEXT`.
- [`process_workspaces`](alembic/versions/069_process_workspaces_events_memberships.py) : `tenant_id UUID NOT NULL REFERENCES tenants(id)`.

---

## Correctifs appliqués (minimal, sans migration)

| Fichier | Modification |
|---------|--------------|
| [`src/api/routers/market.py`](src/api/routers/market.py) | Requête `market_overview` : jointure implicite supprimée ; `SELECT` aligné sur les colonnes réelles, avec alias de sortie (`item_id AS item_key`, etc.) pour garder une forme de réponse stable. |
| [`src/couche_a/auth/dependencies.py`](src/couche_a/auth/dependencies.py) | `_resolve_tenant_uuid_for_rls` : si `tenant_id` n’est pas un UUID, résolution vers `SELECT id FROM tenants WHERE code = 'sci_mali' LIMIT 1` avant `set_db_tenant_id` et injection dans `UserClaims`. |

**Non traité dans ce mandat** : autres routes du même router qui référencent encore `item_key` sur `market_signals_v2` (ex. `item_price_history`, `annotate`) — à traiter si des 500 y sont observés.

---

## Tableau livrable mandat

| Endpoint | Code HTTP (avant) | Cause identifiée | Fix appliqué |
|----------|-------------------|------------------|--------------|
| `POST /api/workspaces` | 500 | `tenant_id` legacy non-UUID vs colonne UUID + FK `tenants` | Résolution vers UUID `tenants` (`sci_mali`) dans `get_current_user` |
| `GET /api/market/overview` | 500 | Colonnes SQL inexistantes sur `market_signals_v2` | Requête alignée sur schéma 043 |

---

## Re-test (à faire après déploiement)

1. `POST /auth/register` (utilisateur smoke) puis `POST /auth/token` (form).
2. `POST /api/workspaces` avec corps JSON mandat BLOC 3 → attendu **201**.
3. `GET /api/market/overview` → attendu **200** (jeu vide acceptable).

Script : [`scripts/bloc3_smoke_railway.py`](scripts/bloc3_smoke_railway.py).

---

## Verdict

**500 attendus comme résolus côté code** — validation production **après déploiement** sur Railway.  
Formulation mandat : **« 500 RÉSOLUS → BLOC 3 = VERT → GO BLOC 4 »** sous réserve de smoke réel post-deploy ; sinon **escalade** si la trace runtime diffère.

**Pas d’escalade migration** : aucune migration corrective ajoutée ; pas de `STOP` Alembic.
