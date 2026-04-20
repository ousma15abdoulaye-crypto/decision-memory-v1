# DMS — P3.4 E4 rapport : benchmark post-merge CASE-28b05d85

**Référence** : P3.4-E4-BENCHMARK-VALIDATION-POST-MERGE  
**Mandat d’exécution** : `P3.4-E4-MANDAT-FINAL-BENCHMARK-EXECUTION`  
**Date d’exécution** : 2026-04-20 (session agent, poste Windows)  
**Branche** : `chore/p3-4-e4-benchmark-validation`  
**HEAD au moment du run** : `a78cda7f` (commit d’ajustement post-`be2b5f37`)  
**Option** : **B′** — agent borné (exécution locale, pas de push / pas de PR dans cette session)

---

## 1. Environnement d’exécution

- **DB** : PostgreSQL atteinte via `DATABASE_URL` chargé depuis `.env` puis `.env.local` (secret **non** reproduit ici). La base utilisée est l’**environnement d’exécution** du poste ; ce n’est **pas** posé comme vérité opposable Railway (triple vérité DMS — rappel mandat §2).
- **Alembic head (attendu dépôt)** : `101_p32_dao_criteria_scoring_schema` — non revérifié par `alembic current` dans cette session.
- **Workspace canonique** : `f1a6edfb-ac50-4301-a1a9-7a80053c632a` (`process_workspaces.id`).
- **`reference_code` humain** : `CASE-28b05d85` (distinct du `legacy_case_id` `28b05d85-62f1-4101-aaec-96bac40905cd`).
- **Python** : 3.11.9 (Windows).
- **Prérequis CLI** : `PYTHONPATH=src;.` requis pour `python scripts/e4_run_benchmark.py` (sinon `ModuleNotFoundError: src`).
- **Option d’exécution** : B′ — agent borné ; artefacts JSON prévus sous `rapports/` (gitignorés) — **non produits** (voir §2).

---

## 2. Exécution pipeline V5

- **Statut** : **ÉCHEC** avant projection matrice / sérialisation artefacts.
- **Commande** :  
  `PYTHONPATH=src;. python scripts/e4_run_benchmark.py --workspace-id f1a6edfb-ac50-4301-a1a9-7a80053c632a --runs 2`
- **Dry-run (Étape 3)** : **OK** (code sortie `0`) — métriques précheck affichées (voir §3).
- **Run complet (Étape 4)** : levée d’exception non gérée par le script E4 :
  - `src.services.pipeline_v5_service.PipelineError: pipeline_blocked:no_eligible_matrix_participants — All bundles failed Gate B or Gate C, no eligible supplier to score in this dossier`
- **Contexte observé dans les logs** : multiples `ConnectError` sur le **client d’extraction** (`src.couche_a.extraction.backend_client`) pour plusieurs `bundle_id` → offres sans extraction réussie → Gate B / cohorte vide côté scoring.
- **`run_pipeline_v5` a skip M14** : log `[PIPELINE-V5] skip M14 evaluate (document exists)` puis échec sur la phase suivante (participants matrice).
- **Durée** : non isolée proprement (script interrompu par traceback ; pas de `duration_seconds` capturé côté script).
- **Artefacts `rapports/p34_case_*.{json}`** : **absents** (dossier `rapports/` non créé — arrêt avant `serialize_artifacts`).

---

## 3. Volumes observés (dry-run)

Bloc `2_precheck_metrics` du dry-run (`--workspace-id` identique) :

| Métrique | Valeur |
|----------|--------|
| `bundle_documents` (texte non vide) | 6 |
| `dao_criteria` | 3 |
| `distinct_bundle_ids` (`bundle_documents`) | 8 |
| `evaluation_documents` | 18 |
| `criterion_assessments` | 6 |
| `tenant_code` | `sci_mali` |

**Lecture** : le workspace **n’est pas vide** sur l’axe données ; l’échec du run complet est **d’exécution / dépendances externes** (extraction), pas l’absence de critères DAO.

---

## 4. Volumes produits (sortie matrice)

- **`len(matrix_rows)`** : **non disponible** (pipeline n’a pas produit de matrice complète).
- **Distribution `RankStatus`** : **non disponible**.

---

## 5. Invariants V1–V6 sur sortie réelle

### Convention d’évaluation

| Code | Signification | Action attendue |
|------|---------------|-----------------|
| `ok: true` | invariant automatiquement vérifié et validé | aucune |
| `ok: false` | invariant automatiquement vérifié et violé | **STOP + remontée CTO Senior** |
| `ok: null` | invariant requiert inspection sémantique manuelle | inspection JSON artefacts, remplissage manuel du tableau |

### Tableau de synthèse V1–V6

| Volet | Automation | Résultat | Détail |
|-------|------------|----------|--------|
| V1 cohérence cohorte (compteurs) | automatisé | **N/A** | pas de `matrix_rows` / `matrix_summary` finalisés |
| V2 modèles Pydantic (`MatrixRow`, `MatrixSummary`) | automatisé | **N/A** | idem |
| V3 idempotence (2 runs, empreinte stable) | automatisé | **N/A** | second run non atteint (exception au run 1) |
| V4 explicabilité peuplée | **manuel** | **N/A** | pas d’artefact `matrix_rows.json` |
| V5 propagation flags métier | **manuel** | **N/A** | idem |
| V6 summary Pydantic | automatisé | **N/A** | idem |
| V6 summary distribution cohérente | **manuel** | **N/A** | idem |

**Anomalies d’environnement (hors liste A1–A6 métier)** : dépendance **service d’extraction** injoignable depuis ce poste (`ConnectError`), effet domino Gate B / absence de participants matrice — **à traiter hors mandat E4** (pas de correctif pipeline autorisé pendant E4).

---

## 6. Idempotence et tie-break

- **Deux exécutions consécutives `run_pipeline_v5`** : **non réalisées** (échec avant fin du premier run utile).
- **Tie-break A2** : **non applicable** (pas de rangs produits).

---

## 7. Artefacts locaux (gitignorés)

- **Chemins attendus** : `rapports/p34_case_<slug>_matrix_rows.json`, `_matrix_summary.json`, `_run_meta.json`
- **Statut** : **aucun fichier créé** (le script s’est arrêté sur exception avant écriture).
- **`git status`** : pas d’artefacts `rapports/` visibles comme suivis (dossier absent).

---

## 8. Décision / suite

- **Verdict E4** : **REFUSÉ** au sens « objectifs benchmark matrice non atteints sur cette exécution » — **cause** : **environnement** (backend d’extraction indisponible / réseau), **sans** constat de violation des invariants P3.4 sur sortie matrice (sortie absente).
- **Suite proposée** :
  1. Rejouer `python scripts/e4_run_benchmark.py --workspace-id f1a6edfb-ac50-4301-a1a9-7a80053c632a --runs 2` sur un poste où le **client d’extraction** est joignable, avec `PYTHONPATH=src;.` et mêmes secrets DB.
  2. **Dette doc / produit** : aligner `--workspace-reference` sur `reference_code` (schéma 069) — aujourd’hui le script résout la référence texte via **`legacy_case_id`** seulement (`WHERE legacy_case_id = :ref`), ce qui **ne** couvre **pas** `CASE-28b05d85` posé comme `reference_code`. **Aucune** colonne `reference` fantôme n’est utilisée. Exécution mandatée avec **`--workspace-id`** pour lever l’ambiguïté.
  3. Ouvrir post-merge l’issue **tech-debt** « helper DB cross-platform » (mandat CTO — hors périmètre E4).
- **PR / push** : **non effectués** dans cette session (conformément mandat §9 différé jusqu’à revue CTO Senior du présent rapport).

---

## Annexe — Vérifications postérieures au run (mandat §4 Étape 7)

- **`python -m pytest tests/unit/ -q`** : **`456 passed`** (2026-04-20, même session).
- **Test d’intégration E4** : non relancé avec `P34_E4_WORKSPACE_ID` après échec pipeline (résultat attendu : échec identique tant que l’extraction est KO).
