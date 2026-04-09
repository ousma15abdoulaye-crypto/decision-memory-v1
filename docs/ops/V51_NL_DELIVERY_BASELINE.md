# Baseline livraison V5.1 — NL-01 à NL-10

Trace ops pour la **phase 0** du plan de livraison V5.1 (merge socle + déploiement + smoke).

## Dépendances backend (relevé plan)

| NL | Ancien blocage supposé | Réalité |
|----|------------------------|---------|
| NL-02 | Exposer WebSocket | Déjà monté : `/ws/workspace/{id}/events` + alias, JWT `?token=` ([`src/api/ws/workspace_events.py`](../../src/api/ws/workspace_events.py)). |
| NL-03 | Backend O10 | `GET /api/workspaces/{id}/committee/pv?format=json|pdf|xlsx` ([`src/api/routers/documents.py`](../../src/api/routers/documents.py)). |
| NL-07 | — | Aucun endpoint « page PDF / split view » ; mandat dédié : [`MANDAT_NL07_PDF_PAGE_ENDPOINT.md`](./MANDAT_NL07_PDF_PAGE_ENDPOINT.md). |

## Checklist baseline (AO / release)

- [ ] PRs backend V5.1 + frontend socle mergés selon processus équipe (pas de travail direct sur `main` sans validation).
- [ ] Déploiement Railway (ou cible) : `mount_v51_workspace_http_and_ws` actif ([`main.py`](../../main.py)).
- [ ] Smoke automatisé : `tests/test_main_app_parity_smoke.py` (OpenAPI W1/W3 + parité `src.api.main`).
- [ ] Smoke manuel ou E2E : dashboard, workspace, matrice, commentaire, agent SSE ; optionnel handshake WS + export PV sur session scellée de test.
- [ ] E2E : `npm run test:e2e` dans `frontend-v51` — **vert en CI** (workflow `dms_invariants_v51.yml`, job `frontend_v51_e2e`) ou local après `npx playwright install` ; échec TLS possible sur poste d’entreprise → voir [`docs/ops/DEV_SETUP.md`](./DEV_SETUP.md).
- [ ] WeasyPrint : vérifier deps système sur l’image Railway si export PDF utilisé en prod.

## Enregistrement des runs

| Date | Environnement | Commit / tag | Résultat smoke | Agent |
|------|---------------|--------------|----------------|-------|
| *(à remplir)* | | | | |

## Suite

Sprints NL : voir plan Cursor « Livraison V5.1 NL frontend » — implémentation dans `frontend-v51/` (matrice, exports UI, WS client, virtualisation, shadcn, thème).
