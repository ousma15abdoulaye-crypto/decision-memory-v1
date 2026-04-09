# ADR — Deux points d’entrée FastAPI (`main.py` vs `src/api/main.py`)

**Statut** : accepté  
**Contexte** : DMS expose `uvicorn main:app` en production (Railway / `start.sh`). Un second module `src/api/main.py` existe pour le harness de tests et la politique de routers ADR-M5-PRE-001 §D1.3 (routers obligatoires vs optionnels).

## Décision

1. **Production** : toute route destinée aux utilisateurs / clients doit être **montée dans [`main.py`](../../main.py)** à la racine du dépôt.
2. **`src/api/main.py`** : sert de référence et de cible d’import pour une partie de la suite de tests ; **ne pas** y ajouter une surface API exclusive sans équivalent dans `main.py`, sauf décision CTO et documentation.
3. **Strangler** : convergence progressive vers une seule app ou maintien explicite des deux rôles (prod vs test harness) tant que l’ADR-M5-PRE-001 s’applique.

## Conséquences

- Les tests qui importent `src.api.main:app` ne garantissent pas à eux seuls la parité production ; voir [`tests/README.md`](../../tests/README.md) et le smoke [`tests/test_main_app_parity_smoke.py`](../../tests/test_main_app_parity_smoke.py) (criteria, M14, geo si présent, **préfixes W1/W3** `/api/workspaces` + `committee/seal` + `committee/pv` sur `main:app`).
- Toute nouvelle route **user-facing** doit être montée dans [`main.py`](../../main.py) **et** couverte ou justifiée dans le smoke / tests d’intégration — voir remédiation post-DD [`docs/ops/POST_DD_RISK_REMEDIATION_2026-04-06.md`](../ops/POST_DD_RISK_REMEDIATION_2026-04-06.md).
- La surface OpenAPI de **`main:app`** reste **plus large** que **`src.api.main:app`** (auth JSON, cases upload, scoring, vues, etc.) ; le harness est un **sous-ensemble** contrôlé, pas une copie byte-à-byte de la prod.

## Références

- [`src/api/app_factory.py`](../../src/api/app_factory.py) — `create_railway_app`, `create_modular_app`, hooks CTO, bundle V5.1
- [`main.py`](../../main.py) — `app = create_railway_app()` (production Railway)
- [`src/api/main.py`](../../src/api/main.py) — `app = create_modular_app()` (harness)
- [`docs/CONTRIBUTING.md`](../CONTRIBUTING.md) — section Applications FastAPI
- [`scripts/compare_fastapi_openapi_paths.py`](../../scripts/compare_fastapi_openapi_paths.py) — comparaison des chemins OpenAPI `main:app` vs `src.api.main:app` (avec `DATABASE_URL` ; préférer `TESTING=true` en local si génération OpenAPI échoue sur les décorateurs slowapi)

## Option A — deux factories (décision CTO, 2026-04)

**Rejet** d’un unique `create_app(deployment_mode=…)`. Deux constructeurs distincts partagent les mêmes **hooks** (noms figés) :

| Hook | Rôle |
|------|------|
| `_add_security_middleware(app, *, log_prefix=…)` | Alias stable vers `register_security_middleware_stack` (SecurityHeaders, Redis rate limit, TenantContext). |
| `_register_common_routers(app, *, entry=…)` | Pile de routeurs **avant** le bundle V5.1 : `entry="modular"` (harness) vs `entry="railway"` (production). Le paramètre `entry` évite un mode unique sur `create_app` tout en gardant un seul module source. |
| `_mount_v51_workspace_bundle(app)` | Bundle HTTP + WebSocket V5.1 ([`src/api/dms_v51_mount.py`](../../src/api/dms_v51_mount.py)). |

- **`create_railway_app()`** — utilisé par **`main.py`** : lifespan migrations / DB, `/health`, rate limit, pile production, V5.1, routers optionnels, `/static`.
- **`create_modular_app()`** — utilisé par **`src.api.main:app`** : CORS harness, mêmes hooks (sauf CORS), routers optionnels ADR-M5-PRE-001.

`register_security_middleware_stack` et `mount_v51_workspace_bundle` restent des **réexports** publics pour compatibilité ; les hooks `_…` sont la surface de convergence demandée par le mandat.
