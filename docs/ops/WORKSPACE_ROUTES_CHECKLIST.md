# Checklist Routes Workspace — Résolution P0-OPS-01

**Référence** : Plan V4.2.0 Phase 0 — P0-OPS-01  
**Date** : 2026-04-04  
**Statut** : ACTIF — appliquer à chaque PR ajoutant une route workspace

---

## Contexte (ADR-DUAL-FASTAPI-ENTRYPOINTS)

Deux applications FastAPI coexistent :
- `main.py` (racine) — **production Railway** (`uvicorn main:app`)
- `src/api/main.py` — harness de test et import de routers

**Règle** : toute route destinée aux utilisateurs doit être dans `main.py`.
Les nouvelles routes workspace V4.2.0 suivent cette règle sans exception.

---

## Checklist avant merge de toute PR routes V4.2.0

### Routes W1 (Process Workspaces)
- [ ] `src/api/routers/workspaces.py` créé
- [ ] Importé dans `main.py` : `from src.api.routers.workspaces import router as workspaces_router`
- [ ] Monté dans `main.py` : `app.include_router(workspaces_router)`
- [ ] Test smoke vérifiant `/workspaces` accessible depuis `main:app`

### Routes W2 (Market Intelligence)
- [ ] `src/api/routers/market.py` créé
- [ ] Importé et monté dans `main.py`
- [ ] Test smoke `/market/overview` sans workspace_id → données retournées

### Routes W3 (Committee Sessions)
- [ ] `src/api/routers/committee_sessions.py` créé
- [ ] Importé et monté dans `main.py`
- [ ] Test smoke `/workspaces/{id}/committee` avec JWT valide

### WebSocket
- [ ] `src/api/ws/workspace_events.py` créé
- [ ] Monté dans `main.py` : `app.add_websocket_route("/ws/workspace/{workspace_id}/events", ...)`
- [ ] Test WebSocket connexion + reception premier event

---

## Procédure de vérification parité main.py / src/api/main.py

```powershell
# Vérifier que toutes les routes workspace sont dans main.py
Select-String -Path "main.py" -Pattern "workspaces_router|market_router|committee_router"

# Vérifier smoke test de parité
pytest tests/test_main_app_parity_smoke.py -v
```

---

## Inventaire routes V4.2.0 attendues dans main.py

| Route | Module | Priorité | Phase |
|---|---|---|---|
| GET /workspaces | `src/api/routers/workspaces.py` | Haute | Phase 5 |
| POST /workspaces | `src/api/routers/workspaces.py` | Haute | Phase 5 |
| GET /workspaces/{id} | `src/api/routers/workspaces.py` | Haute | Phase 5 |
| GET /workspaces/{id}/bundles | `src/api/routers/workspaces.py` | Haute | Phase 5 |
| GET /workspaces/{id}/evaluation | `src/api/routers/workspaces.py` | Haute | Phase 5 |
| POST /workspaces/{id}/upload-zip | `src/api/routers/workspaces.py` | Haute | Phase 5 |
| GET /market/overview | `src/api/routers/market.py` | Haute | Phase 5 |
| GET /market/items/{item_key}/history | `src/api/routers/market.py` | Moyenne | Phase 5 |
| GET /market/vendors/{vendor_id}/signals | `src/api/routers/market.py` | Moyenne | Phase 5 |
| GET /market/watchlist | `src/api/routers/market.py` | Moyenne | Phase 5 |
| POST /market/watchlist | `src/api/routers/market.py` | Moyenne | Phase 5 |
| PATCH /market/items/{item_key}/annotate | `src/api/routers/market.py` | Basse | Phase 5 |
| GET /workspaces/{id}/committee | `src/api/routers/committee_sessions.py` | Haute | Phase 5 |
| POST /workspaces/{id}/committee/open-session | `src/api/routers/committee_sessions.py` | Haute | Phase 5 |
| POST /workspaces/{id}/committee/add-member | `src/api/routers/committee_sessions.py` | Haute | Phase 5 |
| POST /workspaces/{id}/committee/add-comment | `src/api/routers/committee_sessions.py` | Haute | Phase 5 |
| POST /workspaces/{id}/committee/challenge-score | `src/api/routers/committee_sessions.py` | Haute | Phase 5 |
| POST /workspaces/{id}/committee/seal | `src/api/routers/committee_sessions.py` | Haute | Phase 5 |
| WS /ws/workspace/{id}/events | `src/api/ws/workspace_events.py` | Haute | Phase 5 |

---

*Résout P0-OPS-01 — Plan V4.2.0 Phase 0*
