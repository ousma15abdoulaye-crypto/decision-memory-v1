# Checklist release — parité `main:app` (Railway)

**Référence** : [ADR-DUAL-FASTAPI-ENTRYPOINTS](../adr/ADR-DUAL-FASTAPI-ENTRYPOINTS.md), P0-OPS-01 ([DMS_TECHNICAL_DEBT_P0_P3.md](../audit/DMS_TECHNICAL_DEBT_P0_P3.md)).

**Entrée prod** : `uvicorn main:app` ([`start.sh`](../../start.sh)). Toute route user-facing doit être montée dans [`main.py`](../../main.py).

---

## Avant tag / déploiement production

1. `pytest tests/test_main_app_parity_smoke.py -v` — échec = route critique absente de l’OpenAPI `main:app`.
2. Si la PR ajoute une route HTTP : vérifier présence dans `main.py` (pas seulement `src/api/main.py`).
3. `pytest tests/couche_a/test_endpoints.py -v` si dashboard touché (INV-F06 smoke).

---

## Matrice route critique → montage → preuve test

| Préfixe / route | Module router | Monté dans `main.py` | Preuve (test / doc) |
|-----------------|---------------|----------------------|---------------------|
| `/api/criteria` | `src/couche_a/criteria/router.py` | Oui | `test_main_app_parity_smoke` (criteria) |
| `/api/m14` | `src/api/routes/evaluation.py` | Oui (optionnel si import OK) | `test_main_app_parity_smoke` |
| `/api/workspaces` | `src/api/routers/workspaces.py` | Oui | `test_main_app_parity_smoke` |
| `committee/seal`, `committee/pv` | W3 + BLOC7 | Oui | `test_main_app_parity_smoke` |
| `/geo/*` | `src/geo/router.py` | Si paquet présent | `test_main_app_parity_smoke` (conditionnel) |
| `/api/dashboard` | `src/api/routers/dashboard.py` | Oui | `test_main_app_parity_smoke` (V5.1) |
| `POST /api/agent/prompt` | `src/api/routers/agent.py` | Oui | `test_main_app_parity_smoke` (V5.1) |
| `POST .../comments` (W1 O8) | `src/api/routers/workspaces.py` (ou sous-module) | Oui | `test_main_app_parity_smoke` + tests intégration dédiés |

**Note** : une partie de la suite importe `src.api.main:app` ([`tests/README.md`](../../tests/README.md)) — cela **ne** remplace **pas** la preuve ci-dessus pour Railway.

---

## Analyse de dérive `main` vs `src.api.main` (optionnel)

Avec `DATABASE_URL` :

```bash
python scripts/compare_fastapi_openapi_paths.py
```

## Après déploiement (smoke manuel optionnel)

- `GET /health` (ou équivalent health router).
- `GET /openapi.json` depuis l’URL prod : présence des chemins de la matrice.
- JWT valide : `GET /api/dashboard` (200 attendu pour utilisateur tenanté).
