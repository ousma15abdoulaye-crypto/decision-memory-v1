# Rapport pilote — BLOC 6 (SCI Mali bout-en-bout)

**Mandat** : `DMS-BLOC6-PILOTE-SCI-MALI-001`  
**Date du constat** : 2026-04-06  
**Environnement API** : `https://decision-memory-v1-production.up.railway.app`  
**Baseline dépôt (lecture MRD / ANCHOR)** : commit `19d8578d3cb41fb977f57114cfe3b8df7ee62634`  
**Qualification du jeu de données** : **simulé réaliste** — titre et référence pilote (`DAO-2026-MOPTI-017-*`) ; document source = fichier texte minimal uploadé via `POST …/source-package` ; **écarts API** : transitions `analysis_complete` / `in_deliberation` et `committee_required` appliquées par **SQL** (même famille que `scripts/bloc4_committee_mandate_run.py`), pas par enchaînement complet `PATCH /status` + cadre d’évaluation réel — **déclaré explicitement** (pas de présentation comme parcours métier entièrement « natif »).

**IDs pilote (run 2026-04-06)** :

| Champ | Valeur |
|--------|--------|
| `reference_code` | `DAO-2026-MOPTI-017-94454af1bc` |
| `workspace_id` | `3a1ebd0e-dc79-4b40-bc94-dcae1de6d33f` |
| `session_id` (comité) | `890d1984-b1b1-46c6-961e-b6e24225e13e` |

---

## Tableau obligatoire (mandat §9)

| Étape | Statut | Détails |
|-------|--------|---------|
| Préconditions validées | OK | Alembic prod = head `079_bloc5_confidence_qualification_signal_log` ; `with_railway_env` + `diagnose_railway_migrations.py` : sync OK ; ETL vendors `--dry-run` OK (103 lignes) ; smokes `bloc3_smoke_railway.py` : register, token, `POST /api/workspaces`, `GET /api/market/overview` OK ; comité smoke 403 sans rôle = attendu RBAC. |
| Workspace créé | OK | `workspace_id` ci-dessus ; `POST /api/workspaces` → **201** |
| Corpus ingéré | OK | `POST …/source-package` → **200** ; `sha256` documenté dans sortie JSON script ; `doc_type=dao` |
| Bundles produits | Partiel | `GET …/bundles` → **200** ; **0** lignes `supplier_bundles` — pas de Pass assembleur / ZIP sur ce pilote ; diagnostic cohérent « vide » |
| Qualification exploitable | Partiel | État cognitif atteint **E5** (délibération) via chemins documentés ; pas de bundles réels |
| Évaluation sans verdict | OK | `GET …/evaluation-frame` → **200** ; scan kill list sur JSON sérialisé : **aucune** occurrence de `winner`, `rank`, `recommendation`, `best_offer`, `selected_vendor` |
| Comité créé/activé | OK | `POST …/committee/open-session` → **201** ; `session_id` ci-dessus |
| Actes append-only prouvés | OK | SQL lecture : `committee_deliberation_events` — `session_activated` ×1, `member_added` ×5 pour ce `workspace_id` |
| Seal effectué | **KO** | `POST …/committee/seal` → **500** « Internal Server Error » ; pas de persistance `seal_hash` / `pv_snapshot` (voir §Scellement) |
| Irréversibilité prouvée | **KO** | Non testable tant que le scellement ne réussit pas (pas d’état `sealed` en base) |
| Projection post-seal | **KO** | Pas de seal → pas de preuve runtime `project_sealed_workspace` / `vendor_market_signals` pour ce workspace ; gap ARQ/Redis possible côté infra (hors constat principal) |
| Verdict final | **ROUGE** | Scellement **non** obtenu en production au moment du constat (STOP 6 — pas de `seal_hash` ni snapshot persistés) ; kill list OK sur la vue évaluation |

---

## Les 7 tests de vérité (mandat §7)

| # | Question | Réponse | Preuve courte |
|---|----------|---------|----------------|
| 1 | Workspace réellement créé ? | **Oui** | HTTP **201** ; `workspace_id` UUID retourné |
| 2 | Documents réellement ingérés ? | **Oui** | **200** sur `source-package` ; `sha256` dans corps de réponse |
| 3 | Bundles ou diagnostic crédible ? | **Partiel** | **0** bundle ; liste vide explicite — pas de contournement SQL sur `supplier_bundles` |
| 4 | Lecture comparative sans verdict interdit ? | **Oui** | `evaluation-frame` ; chaînes kill list absentes du JSON texte |
| 5 | Comité réellement dans DMS ? | **Oui** | Session créée ; 5 membres ajoutés (**200**) ; événements CDE en base |
| 6 | Seal avec hash + snapshot ? | **Non** | **500** sur seal ; requête SQL : `session_status=active`, `seal_hash` et `pv_snapshot` **NULL** |
| 7 | Projection / trace post-seal ? | **Non** | Prérequis seal non rempli |

---

## Scellement — analyse (sans faux vert)

**Symptôme** : réponse **500** sur `POST /api/workspaces/{id}/committee/seal` alors que le workspace est en `in_deliberation` (positionnement SQL) et la session comité active.

**Cause probable (dépôt)** : construction de `pv_snapshot` avec `session_id` issu du driver PostgreSQL comme **UUID Python** ; `json.dumps` sans adaptateur ⇒ **TypeError** ⇒ 500.  

**Correctif minimal enregistré dans le dépôt** : `src/api/routers/committee_sessions.py` — `session_id` forcé en **`str(session["id"])`** dans le dictionnaire snapshot avant `json.dumps`.

**Conséquence pour le pilote** : le runtime **Railway au moment du run** n’inclut pas encore ce correctif tant qu’un **déploiement** n’a pas été effectué — le constat **ROUGE** reste opposable pour l’**épreuve terrain** telle qu’exécutée.

---

## Scripts et preuves auxiliaires

- Orchestration pilote : `scripts/bloc6_pilot_sci_mali_run.py` (API + `run_pg_sql` pour états BLOC4-style).
- Smokes / préconditions : `scripts/bloc3_smoke_railway.py`, `scripts/with_railway_env.py`, `scripts/diagnose_railway_migrations.py`, `scripts/etl_vendors_m4.py --dry-run`.

---

## Verdict final (mandat §10)

**ROUGE**

**Justification courte** : le processus bout-en-bout **s’arrête au scellement** sur l’API de production observée : **pas** de `seal_hash`, **pas** de `pv_snapshot` en base (STOP 6). Les étapes amont (workspace, source package, comité, kill list sur `evaluation-frame`) sont **réellement** passées par l’API ; le correctif UUID→str est **nommé** et **minimal** pour lever la cause probable du 500 après déploiement — **sans** transformer ce rapport en vert narratif sur l’état prod au moment du run.

---

## BLOC 6 BIS — Fix seal UUID + preuve prod (mandat correctif)

**Branche dépôt** : `feat/bloc6-bis-seal-uuid-fix` (PR vers `main` — pas de push direct `main` : gouvernance DMS).

### Scan handler `POST …/committee/seal` (UUID / JSON)

Commande équivalente (sortie attendue : aucune ligne problématique sur le snapshot PV) : recherche des usages de `json.dumps` sur le snapshot scellement ; le snapshot utilise désormais **`safe_json_dumps`** (`src/utils/json_utils.py`) avec clés normalisées en `str()` pour `workspace_id`, `session_id`, `sealed_by`, `tenant_id`. Les autres `json.dumps` du fichier (charges CDE `member_added`, `session_sealed`, `WORKSPACE_STATUS_CHANGED`) ne contiennent que des types JSON natifs (entiers, chaînes, statuts) — pas d’objet `uuid.UUID` brut.

### Implémentation dépôt

| Élément | Détail |
|--------|--------|
| `pv_snapshot` | Champs explicites : `workspace_id`, `session_id`, `sealed_by`, `sealed_at`, `seal_comment`, `tenant_id`, `events_count` (compte SQL synchrone `committee_deliberation_events` pour la session). |
| Sérialisation | `pv_json = safe_json_dumps(pv_snapshot, sort_keys=True)` — `uuid.UUID` et `datetime` gérés par défaut si besoin. |
| Tests | `tests/test_json_utils_safe_dumps.py` — couverture UUID + datetime + rejet d’un `default=` externe. |

### Tableau mandat — statut au **2026-04-06** (séparation code vs prod)

| Étape | Statut avant fix (BLOC 6) | Statut après fix (BLOC 6 BIS) |
|-------|---------------------------|-------------------------------|
| Cause 500 identifiée | `uuid.UUID` non sérialisable dans `json.dumps` | Confirmée ; mitigation **dépôt** : `str()` + `safe_json_dumps` |
| Fix dans le dépôt | Partiel (`str(session["id"])` seul) | **OK** — snapshot complet + helper + `events_count` |
| Fix déployé Railway | Non — API prod inchangée au run initial | **EN ATTENTE** — déployer **après** merge PR (build CI/Railway vert) |
| `POST /committee/seal` | **500** | **Non re-testé HTTP** sur prod tant que le déploiement n’inclut pas le commit ; ne pas déclarer 200/201 sans preuve |
| `seal_hash` 64 caractères | ABSENT (NULL) | En prod **toujours NULL** tant que seal non rejoué (SQL ci-dessous) |
| `pv_snapshot` | ABSENT (NULL) | Idem |
| `sealed_at` | ABSENT | Idem |
| Irréversibilité (`fn_workspace_sealed_final`) | Non testée | **EN ATTENTE** — même condition que seal réussi |

**Preuve SQL prod (Railway, lecture seule, 2026-04-06)** — workspace pilote `3a1ebd0e-dc79-4b40-bc94-dcae1de6d33f` :

- `session_status` = `active`, `process_workspaces.status` = `in_deliberation`, `reference_code` = `DAO-2026-MOPTI-017-94454af1bc` → **CAS A** du mandat (seal possible **après** déploiement du fix).
- `seal_hash` / `pv_snapshot` / `sealed_at` : **toujours NULL** — cohérent avec l’échec seal initial et l’absence de nouveau seal post-fix côté prod.

### Verdict BLOC 6 BIS (règle mandat)

| Domaine | Verdict |
|---------|---------|
| **Code / tests / scan handler** | **VERT** — correctif structuré, pas de raccourci « str() partiel seul » sans filet `safe_json_dumps`. |
| **Production (HTTP 200 + hash + snapshot + irréversibilité)** | **EN ATTENTE DÉPLOIEMENT** — ne pas passer à BLOC 7 tant que `POST …/committee/seal` n’a pas été **re-joué** sur l’API déployée avec ce commit. Si **500** persiste après déploiement : capturer **le corps de réponse complet** (`r.text`) + logs Railway, **STOP**, escalade CTO. |

### Suite opératoire (post-merge)

1. Merger la PR, attendre build Railway vert.
2. Obtenir un JWT avec `committee.manage` sur le workspace pilote (ou script `bloc6_pilot_sci_mali_run` / client API habituel).
3. `POST /api/workspaces/3a1ebd0e-dc79-4b40-bc94-dcae1de6d33f/committee/seal` avec `{"seal_comment": "Seal pilote BLOC 6 BIS après fix UUID"}` (le corps **ne contient pas** `sealed_by` — l’API utilise l’utilisateur JWT).
4. Rejouer les vérifications SQL mandat (longueur hash 64, `pv_snapshot` non NULL, test `UPDATE process_workspaces` bloqué).
