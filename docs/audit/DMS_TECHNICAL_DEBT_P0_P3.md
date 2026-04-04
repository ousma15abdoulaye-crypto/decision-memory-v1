# DMS — Dette technique priorisée (P0–P3)

**Référence :** DMS-MAP-M0-M15-001 — Livrable 3  
**Date :** 2026-04-04  
**Méthode :** preuves repo + contradictions doc + probes où exécutées

---

## P0 — Peut casser ou invalider le système

| ID | Description | Preuve | Impact | Risque | Action recommandée |
|----|-------------|--------|--------|--------|-------------------|
| P0-DOC-01 | **MRD `PROBE RAILWAY 2026-04-03` contradictoire** avec « ÉTAT ALEMBIC 067 » (même fichier) | `docs/freeze/MRD_CURRENT_STATE.md` : L87–101 vs L68–73 | Décisions CTO sur « migrations pending » ou tables absentes **fausses** | Go/no-go erroné | Réécrire section probe avec date unique post-067 ou archiver probe historique |
| P0-OPS-01 | **Double source de vérité app** : `main.py` vs `src/api/main.py` | Deux `FastAPI` ; CI teste les deux (PR #297 M14) | Régression si un seul point d’entrée mis à jour | Route M14 absente sur un déploiement | Checklist release : inclure tests `main:app` **et** `src.api.main:app` |
| P0-SEC-01 | **JWT obligatoire** pour extraction et la plupart des routes métier ; scripts ops sans JWT = échec silencieux avant fix Copilot | `trigger_extraction_queue.py` post-#304 | Blocage pipeline V6 | Perte de temps opérateur | Runbook : `DMS_JWT` + `--api-url` |

---

## P1 — Ralentit fortement ou ment sur l’état

| ID | Description | Preuve | Impact | Risque | Action |
|----|-------------|--------|--------|--------|--------|
| P1-DATA-01 | **Couverture mercuriale→dict** < seuil 70 % (doc) | MRD / anchor : ~67,38 % | Signal engine partiel | Gate M15 orange | Mapping manuel top items (`unmapped_items.csv`) |
| P1-ANN-01 | **Orchestrateur M12 Ph.3** derrière flag `ANNOTATION_USE_PASS_ORCHESTRATOR` (défaut 0) | `CONTEXT_ANCHOR`, `services/annotation-backend` | Prod peut tourner **sans** passes 0→1 complètes | Écart training vs runtime | Bascule CTO + fenêtre hors annotation |
| P1-INFRA-01 | **REDIS_URL** optionnel ; ARQ / rate limit dégradés si absent | `arq_config.py`, `ratelimit` | Workers inactifs ; limite dégradée | Charge DB / UX | Service Redis Railway + env |
| P1-M14-01 | **Assemblage `offers[]`** pour M14 : le moteur **consomme** une liste d’offres en entrée ; **ne construit pas** le bundle process depuis les seuls documents | `src/procurement/m14_engine.py` (`for offer in inp.offers`) | « Trou structurel » document → offres unifiées **si** l’appelant ne fournit pas les dicts | Évaluation incomplète en prod | Contrat API + orchestration amont (case workspace) explicite |

---

## P2 — Important mais non bloquant court terme

| ID | Description | Preuve | Action |
|----|-------------|--------|--------|
| P2-DOC-02 | **MRD `next_status`** (REGLE-23 KO 0/50) peut diverger de **CONTEXT** (75 validés) | MRD L38–39 vs anchor L127–128 | Aligner MRD sur probe post-PR#304 |
| P2-TEST-01 | **1737 tests collectés** — couverture inégale sur chemins Railway réels | `pytest --collect-only` | Auditer couverture par module critique (`pyproject` threshold) |
| P2-VIVANT-01 | **Modules `src/memory/*`** volumineux — utilisation réelle proportionnelle au trafic API `/api/views/*` et workers | Arborescence `src/memory` | Observabilité : métriques par route |

---

## P3 — À surveiller

| ID | Description | Preuve |
|----|-------------|--------|
| P3-LEG-01 | Migrations préfixes `m7_*` vs numériques `0xx` — historique branchement (merge) | `alembic/versions/` liste |
| P3-DOC-03 | Fichier mandat **`DMS-PLAN-FINAL-2026-04-02`** introuvable dans le dépôt | `Glob **/*PLAN*2026*` → 0 fichiers | Ajouter ou archiver référence externe |
| P3-LS-01 | Label Studio Railway — problèmes `POSTGRE_PORT` documentés dans anchor (historique) | `CONTEXT_ANCHOR` section LS | Runbook infra LS |

---

## Note sur « dette doctrinale »

- **V4.1.0 FREEZE** impose jalons M9/M11/M15 avec **métriques opposables** — l’existence du code **ne suffit pas** à clore M15 (100 dossiers terrain) : **SUBSTANTIAL_BUT_OPEN** jusqu’à preuve.
- **Orchestration Framework** : divergence PostgreSQL Railway / git / alembic = **STOP** — ici divergence **au sein du MRD** = dette **gouvernance documentaire** (P0-DOC-01).
