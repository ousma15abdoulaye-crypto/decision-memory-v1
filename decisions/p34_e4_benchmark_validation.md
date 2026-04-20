# DMS — P3.4 E4 rapport : benchmark post-merge CASE-28b05d85

**Référence** : P3.4-E4-BENCHMARK-VALIDATION-POST-MERGE  
**Date** : À remplir après exécution  
**Branche** : `chore/p3-4-e4-benchmark-validation`  
**Commit base** : `7b1177c2` (main post-merge — ajuster si HEAD différent)  
**Contexte** : validation post-merge P3.4 ; exécution matérielle **Option B** (agent prépare, CTO principal exécute sur DB réelle).

---

## 1. Environnement d’exécution

- DB : (locale / hôte — **ne pas** coller `DATABASE_URL` en clair dans ce document)  
- Alembic head attendu : `101_p32_dao_criteria_scoring_schema` — **à confirmer** sur la DB utilisée (`alembic current`).  
- Workspace : CASE-28b05d85 — UUID `process_workspaces.id` : **À remplir**  
- Python : **À remplir**  
- Timestamp run : **À remplir**  
- Option d’exécution : **B** (script `scripts/e4_run_benchmark.py` exécuté par le CTO principal ; artefacts JSON sous `rapports/`, gitignorés).

---

## 2. Exécution pipeline V5

- Statut : SUCCÈS / ÉCHEC — **À remplir**  
- Timestamp début / fin : **À remplir**  
- `step_4_m14_eval_doc_id` (si M14 skip) : **À remplir**  
- Durée (`duration_seconds`) : **À remplir**

---

## 3. Volumes observés (dry-run ou introspection)

Relever depuis la sortie console du script (bloc `2_precheck_metrics`) ou depuis les métriques annexées :

- `bundle_documents` avec texte non vide  
- `dao_criteria`  
- `distinct_bundle_ids` (`bundle_documents`)  
- `evaluation_documents`  
- `criterion_assessments`  

**À remplir** — ne pas inventer de noms de tables hors schéma réel ; les comptes du script sont alignés sur le code pipeline V5.

---

## 4. Volumes produits (sortie matrice)

- `len(matrix_rows)` : **À remplir**  
- Distribution `RankStatus` : RANKED / EXCLUDED / PENDING / NOT_COMPARABLE / INCOMPLETE — **À remplir** (bloc `5_rank_distribution` du script).

---

## 5. Invariants V1–V6 sur sortie réelle

Synthèse depuis le bloc `6_invariants` du script (et compléments manuels si besoin) :

| Volet | Résultat | Détail |
|-------|----------|--------|
| V1 cohérence cohorte / compteurs | À remplir | |
| V2 modèles Pydantic (`MatrixRow` / `MatrixSummary`) | À remplir | |
| V3 idempotence (2 runs) | À remplir | |
| V4 explicabilité | À remplir | (inspection ciblée si requis) |
| V5 propagation flags | À remplir | |
| V6 summary | À remplir | |

---

## 6. Idempotence et tie-break

- Deux exécutions consécutives `run_pipeline_v5` : **À remplir** (empreinte stable sans `pipeline_run_id`).  
- Tie-break A2 : **À remplir** (vérifié / non applicable).

---

## 7. Artefacts locaux (gitignorés)

Chemins typiques générés par `scripts/e4_run_benchmark.py` :

- `rapports/p34_case_<slug>_matrix_rows.json`  
- `rapports/p34_case_<slug>_matrix_summary.json`  
- `rapports/p34_case_<slug>_run_meta.json`  

Tailles / nombre d’entrées : **À remplir**. Ne pas commiter ces fichiers.

---

## 8. Décision / suite

- Verdict E4 : **ACCEPTÉ / REFUSÉ / PARTIEL** — **À remplir**  
- Suites proposées (PR, tickets, gel) : **À remplir**
