# DMS — Cartographie totale M0→M15

**Référence mandat :** DMS-MAP-M0-M15-001  
**Date :** 2026-04-04  
**Exécutant :** Agent Cursor (mandat CTO)  
**Niveau :** vérité système > narration — preuves citées  

**Documents normatifs lus (extraits + structure) :**  
- `docs/freeze/DMS_V4.1.0_FREEZE.md` (jalons M0/M3/M9/M11/M15/M21, stack)  
- `docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md` (hiérarchie, INV, PostgreSQL Railway = vérité données)  
- `docs/freeze/MRD_CURRENT_STATE.md` (état déclaré — **sections contradictoires détectées**, voir §11)  
- **`DMS-PLAN-FINAL-2026-04-02` : ABSENT du dépôt** (recherche globale — 0 fichier). Le mandat y fait référence ; le réel = **non versionné ici**.  

**Code & outils :** `main.py`, `src/api/main.py`, `alembic/versions/`, `src/workers/`, `pytest --collect-only`, git log.

---

## 1. Executive summary (brutal)

- **Le dépôt `main` est un système large et réel** : FastAPI, migrations jusqu’à **067**, moteurs M12/M13/M14, Couche B marché, stack VIVANT V2 (`src/memory`), workers ARQ, **1737 tests** collectés. Ce n’est pas un prototype vide.
- **La documentation d’état (MRD) contient des contradictions internes** : une section « probe 2026-04-03 » parle encore de head **058** et tables absentes, tandis qu’une autre section affirme **067** appliqué et migrations pending **AUCUNE**. **Une seule peut être vraie par instant T** — c’est une dette **P0 gouvernance** (voir `DMS_TECHNICAL_DEBT_P0_P3.md`).
- **Deux applications FastAPI** (`main.py` et `src/api/main.py`) : décision historique pour CI / dual-mount M14 (PR #297). Risque opérationnel si une release ne valide qu’un seul point d’entrée.
- **M14 n’est pas un « closage bout-en-bout du workspace »** : le moteur d’évaluation consomme **`inp.offers`** — liste d’offres déjà structurées. L’assemblage **document brut → offres[] consolidées par process** n’est **pas** implémenté comme composant unique dans `m14_engine.py` ; il est **amont** (orchestration, intégration, future couche workspace). C’est le **trou structurel** le plus honnête à assumer pour passer *procedure-first*.
- **Couche B** (signaux, surveys, dict) est **réellement peuplée et calculable** côté code (`signal_engine`, tables `market_signals_v2`, etc.) ; **l’exploitabilité « hors processus »** pour un opérateur métier dépend surtout des **routes exposées**, de l’**auth**, et des **produits UI** — pas seulement du SQL.
- **Workers async** : ARQ définit **3** fonctions (`index_event`, `detect_patterns`, `generate_candidate_rules`). Pas de worker d’**extraction document** en queue — l’extraction est **API synchrone/asynchrone** selon SLA.

---

## 2. Carte système globale

```
                    ┌─────────────────────────────────────────┐
                    │  Clients : UI, Label Studio, scripts ops │
                    └───────────────┬─────────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────────┐
                    │  FastAPI main.py (canon Railway)         │
                    │  auth · cases · documents · analysis     │
                    │  extractions · regulatory (M13) · scoring  │
                    │  committee · criteria · M14 eval · views   │
                    └───────┬───────────────────────┬───────────┘
                            │                       │
              ┌─────────────▼────────────┐   ┌──────▼──────────────┐
              │  annotation-backend    │   │  PostgreSQL Railway  │
              │  (Mistral /predict)      │   │  + RLS + triggers    │
              └─────────────┬────────────┘   └──────┬──────────────┘
                            │                       │
              ┌─────────────▼────────────┐   ┌──────▼──────────────┐
              │  Orchestrateur M12      │   │  Couche B : dict,   │
              │  passes + FSM           │   │  mercurials, signals │
              └────────────────────────┘   └─────────────────────┘
              ┌────────────────────────────────────────────────────┐
              │  Redis : rate limit + ARQ (si REDIS_URL)            │
              │  Workers : index_event, detect_patterns, …         │
              └────────────────────────────────────────────────────┘
```

**Preuve point d’entrée :** `Procfile` → `bash start.sh` ; `main.py` monte les routeurs listés (lecture fichier).

---

## 3. État milestone par milestone

Légende complétude : **REAL_DONE** | **SUBSTANTIAL_BUT_OPEN** | **PARTIAL** | **DOC_ONLY** | **CONTRADICTORY**

| Jalons | Objectif canon (V4.1 / MRD) | Implémentation réelle | Complétude |
|--------|----------------------------|------------------------|------------|
| **M0** | Dette visible | `docs/`, `TECHNICAL_DEBT`, audits | SUBSTANTIAL_BUT_OPEN |
| **MRD-1..6** | Dict / taxonomie / identité | Migrations `m7_*`, `m6_*` | REAL_DONE (code) |
| **M8–M10** | Pipeline, infra | migrations `032+`, docker PR #276 | SUBSTANTIAL_BUT_OPEN |
| **M9** | Signaux Couche B | `signal_engine`, `market_signals_v2` | REAL_DONE (moteur) |
| **M10–M11** | Extraction + corpus | `extraction`, annotation, tests | SUBSTANTIAL_BUT_OPEN |
| **M12** | Recognizer 10 couches | `src/procurement/*`, `annotation/orchestrator` | REAL_DONE (code) — flag / déploiement = OPEN |
| **M13** | Réglementaire Pass 2A | YAML + `regulatory_profile` + migration 057 | SUBSTANTIAL_BUT_OPEN |
| **M14** | Evaluation sans « winner » | `m14_engine` + API + 059 audit | SUBSTANTIAL_BUT_OPEN — entrée `offers[]` |
| **DMS VIVANT V2** | Memory / RAG / events | `src/memory`, migrations 060–067 | PARTIAL (code riche, usage prod à mesurer) |
| **M15** | 100 dossiers + métriques | Scripts ops PR #304, gates partiels | SUBSTANTIAL_BUT_OPEN — MRD **contradictoire** sur probes |

---

## 4. État local ↔ Railway

Voir livrable dédié : **`docs/audit/DMS_LOCAL_VS_RAILWAY_TRUTH.md`**.

Synthèse : **head fichier = 067** ; **`alembic current` local a échoué** (auth DB) — vérité révision locale **non prouvée** par CLI sur ce poste.

---

## 5. Cartographie DB / migrations / RLS / triggers

- **Migrations** : 89 fichiers listés sous `alembic/versions/` ; head unique **067** (preuve CLI `alembic heads`).
- **M14** : `056_evaluation_documents`, `059` score_history/elimination_log.
- **M13** : `057`, `058` index.
- **VIVANT** : `060`–`067` (event index, embeddings, llm_traces, bridge triggers, fix matview).
- **RLS** : migrations 051–053, extensions 055, M13/M14 — détail dans DDL (non re-dump ici faute de connexion live sur mandat).

---

## 6. Cartographie API / workers / routes réelles

**Montées dans `main.py` (obligatoires + optionnelles si import OK) :**  
auth, upload, health, cases, documents, analysis, **extractions**, **regulatory_profile**, committee, scoring, criteria, + optionnels geo, vendors, mercuriale, price_check, pipeline, analysis_summary, **M14 evaluation**, **case_timeline**, **market_memory_card**, **learning_console**.

**Workers ARQ** (`arq_config.py`) : `index_event`, `detect_patterns`, `generate_candidate_rules` — **pas** d’équivalent « extract_document_job ».

---

## 7. Couche A — état réel

- **Cases / uploads / documents** : routes présentes ; extraction **sous auth** et contraintes case.
- **Pipeline annotation** : orchestrateur + passes M12 ; M13 Pass 2A branché via flags et routes.
- **M14** : routes `/api/m14/*` (préfixe selon `evaluation.py`) — **exposées sur `main.py`** si import réussi.
- **Score history / elimination** : tables **059** — écriture via `save_m14_audit` (réf. MRD PR #297).

---

## 8. Couche B — état réel

- **Mercuriales, surveys, signals** : tables et code `signal_engine` — **REAL** (subject to data coverage).
- **Dictionary** : `couche_b.procurement_dict_items` — volumétrie et validation dans probes MRD (draft vs validated — **OPEN**).
- **Memory tables VIVANT** : DDL en 061–065 ; **writes** via services + triggers bridge — **PARTIAL** sans métriques prod dans ce mandat.

---

## 9. Dette technique totale priorisée

Voir **`docs/audit/DMS_TECHNICAL_DEBT_P0_P3.md`**.

---

## 10. Gaps majeurs / failles systémiques

1. **Doc MRD incohérente** (probe 03/04 vs 067) — risque décisionnel.
2. **Double `main:app`** — risque de déploiement partiel.
3. **M14 / offres** : pas de composant canon unique « workspace bundle » — **dispersé** (API attend JSON structuré).
4. **Redis / ARQ** : optionnel — projections **vivantes** si worker + charge.

---

## 11. Écarts doc ↔ code ↔ runtime

| Sujet | Doc | Réel |
|-------|-----|------|
| Head Railway | MRD probe 058 vs section 067 | **Contradiction interne MRD** |
| Tables VIVANT | Probe « absentes » | Code + migrations 061+ **existants** |
| Extraction queue | Narration « ARQ extract » | **API seulement** (post PR #304) |

---

## 12. Ce qui est solide

- Chaîne **Alembic** unifiée sur **067** (fichier).
- **Test suite** massive (**1737** tests).
- **Moteurs** M12/M13/M14 **existants** dans `src/procurement` et `annotation`.
- **Couche B** : signal et données structurées **non fictives** dans le schéma.

---

## 13. Ce qui ment / surestime / reste semi-fictif

- **« M15 DONE »** au sens **100 dossiers terrain + métriques opposables** : **non prouvé** par ce mandat (jalon produit V4.1).
- **« Probe Railway »** figé au **03/04** alors que **067** est mergé : **fiction partielle** dans MRD si non mis à jour.
- **Workspace-first** : **non** — le produit exposé reste **très pipeline/API/document**.

---

## 14. Ce qui manque pour un vrai workspace DMS

- **Objet workspace** (agrégat dossier + offres + liens process) **premier citoyen** en API et en DB.
- **Assembleur** document(s) → `offers[]` **validé contractuellement** (aujourd’hui consommateur M14, pas producteur unique).
- **UI / permissions** opérateur sur la même surface que l’agent.

---

## 15. Recommandations NOW / NEXT / LATER

- **NOW** : Réconcilier **MRD** (une vérité par date) ; valider **Redis** + **JWT** runbooks ops.
- **NEXT** : ADR **workspace bundle** + orchestration **offers** ; métriques M15 sur **100 dossiers**.
- **LATER** : Remplacer dual-app par **une** façade si possible sans régression CI.

---

## 16. Annexe — preuves / commandes

```text
git branch --show-current
git log --oneline -n 5
alembic heads
pytest tests/ --collect-only -q
```

**Fichiers cités :** `main.py`, `src/api/main.py`, `src/workers/arq_config.py`, `src/procurement/m14_engine.py`, `docs/freeze/MRD_CURRENT_STATE.md`, `docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md`, `docs/freeze/DMS_V4.1.0_FREEZE.md`.

---

## Réponses obligatoires (focus § mandat)

1. **M12** : **Recognizer réel** dans le code (`src/procurement`, passes) + orchestrateur — **pas** « doctrine seule » ; calibration **sous conditions** (corpus, flags).
2. **M13** : **Partiellement projeté** — YAML + API + DB ; charge terrain réelle sur **passes** et données.
3. **M14** : **Pas fermé workspace-complet** — moteur **fermé** sur le **périmètre** « liste d’offres + handoffs » ; **assemblage amont** = OPEN.
4. **Routes M14** : **Oui sur `main.py`** si import OK (preuve include_router).
5. **Assemblage offres** : **Amont M14** — consommation `inp.offers` dans `m14_engine.py` ; construction = **intégration / orchestration / futur workspace**.
6. **Couche B hors processus** : **Données OK** ; **surface produit** limitée par API/UI et auth.
7. **Workers async** : **3 tâches ARQ** ; **pas** extraction ; **projections** dépendent **Redis + exécution worker**.
8. **Compat workspace-first** : **Partielle** — events, memory, vues API = briques ; **manque** objet workspace souverain.
9. **Plus grand mensonge implicite** : **« tout est branché en prod comme en doc »** — **non** (MRD contradictoire, flags, Redis).
10. **Plus grand actif réel** : **Code + schéma + tests** — socle **non trivial** et **auditable**.
