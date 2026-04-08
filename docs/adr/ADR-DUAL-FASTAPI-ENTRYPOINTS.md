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

## Références

- [`src/api/main.py`](../../src/api/main.py) — commentaire §D1.3
- [`docs/CONTRIBUTING.md`](../CONTRIBUTING.md) — section Applications FastAPI
- [`scripts/compare_fastapi_openapi_paths.py`](../../scripts/compare_fastapi_openapi_paths.py) — comparaison des chemins OpenAPI `main:app` vs `src.api.main:app` (avec `DATABASE_URL`)

## Convergence « factory unique » (option CTO)

Une fusion de `main.py` et `src/api/main.py` derrière un seul `create_app()` reste un chantier **large** (non requis pour la parité documentée ici). Tant qu’elle n’est pas mandatée, la preuve de prod repose sur le smoke OpenAPI + la checklist release.
