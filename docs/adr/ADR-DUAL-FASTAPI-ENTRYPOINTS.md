# ADR — Deux points d’entrée FastAPI (`main.py` vs `src/api/main.py`)

**Statut** : accepté  
**Contexte** : DMS expose `uvicorn main:app` en production (Railway / `start.sh`). Un second module `src/api/main.py` existe pour le harness de tests et la politique de routers ADR-M5-PRE-001 §D1.3 (routers obligatoires vs optionnels).

## Décision

1. **Production** : toute route destinée aux utilisateurs / clients doit être **montée dans [`main.py`](../../main.py)** à la racine du dépôt.
2. **`src/api/main.py`** : sert de référence et de cible d’import pour une partie de la suite de tests ; **ne pas** y ajouter une surface API exclusive sans équivalent dans `main.py`, sauf décision CTO et documentation.
3. **Strangler** : convergence progressive vers une seule app ou maintien explicite des deux rôles (prod vs test harness) tant que l’ADR-M5-PRE-001 s’applique.

## Conséquences

- Les tests qui importent `src.api.main:app` ne garantissent pas à eux seuls la parité production ; voir [`tests/README.md`](../../tests/README.md) et le smoke [`tests/test_main_app_parity_smoke.py`](../../tests/test_main_app_parity_smoke.py).

## Références

- [`src/api/main.py`](../../src/api/main.py) — commentaire §D1.3
- [`docs/CONTRIBUTING.md`](../CONTRIBUTING.md) — section Applications FastAPI
