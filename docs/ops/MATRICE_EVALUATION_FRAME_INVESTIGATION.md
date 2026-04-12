# Investigation — Matrice comparative (evaluation-frame) vs forme M14

**Date** : 2026-04-11  
**Symptôme** : en-têtes UUID, pondérations 0 %, cellules « — » partout dans la matrice V5.1.

## Preuves (sources de vérité)

| Source | Fait opposable |
|--------|----------------|
| `docs/ops/M16_SCHEMA_AUDIT.md` § « Forme de scores_matrix » | Niveau 1 = **bundle**, niveau 2 = **critère**. |
| `src/services/m14_bridge.py` (en-tête module) | `scores_matrix[bundle_id][criterion_key]` avec `criterion_key` = `dao_criteria.id`. |
| `frontend-v51/components/workspace/comparative-table.tsx` | Lecture `scores_matrix[supplierId][criterionId]` ; fournisseurs via `data.suppliers` sinon clés niveau 1. |
| `tests/cognitive/test_evaluation_frame.py` (avant correctif) | Test « legacy » à clés plates — **aucun** cas M14 imbriqué. |

## Chaîne de causalité (bug)

1. `GET /api/workspaces/{id}/evaluation-frame` appelait `extract_criteria_from_scores_matrix`, qui traitait les **clés de niveau 1** comme des critères.
2. Pour une matrice M14, le niveau 1 = **IDs bundle** → les « lignes critère » devenaient des UUID d’offres ; `critere_nom` / `ponderation` absents → **0 %** et libellés UUID.
3. La cellule `(colonne bundle S, ligne « critère » B)` faisait `scores_matrix[S][B]` avec `B` = UUID bundle alors que les clés internes sont des **IDs critère** → **`undefined`** → affichage **« — »**.
4. Le payload ne fournissait pas `suppliers` → le front retombait sur `0aa0b276…` tronqué.

## Correctifs chirurgicaux appliqués (code)

1. **`src/cognitive/evaluation_frame.py`**  
   - `scores_matrix_is_m14_bundle_nested()` : détection de la forme bundle → critère → cellule (`score` / `signal` / `confidence`).  
   - `extract_criteria_from_scores_matrix()` : en mode M14, **union des clés de niveau 2** ; sinon comportement legacy inchangé.

2. **`src/api/routers/workspaces.py`**  
   - `_enrich_frame_criteria_from_dao` : fusion `dao_criteria` (`critere_nom`, `ponderation`, `is_eliminatory`).  
   - `_frame_suppliers_for_workspace` : `supplier_bundles` → champ JSON **`suppliers`** pour le front.  
   - Réponse `evaluation-frame` : ajout de **`suppliers`**.

3. **`tests/cognitive/test_evaluation_frame.py`**  
   - Tests de non-régression M14 + détection de forme.

## Filtres UI (rappel)

Les cases « Éliminatoires », « Signal rouge », « Écart au max ligne » restent **100 % client** (`criterionPassesFilters` dans `comparative-table.tsx`) ; ils consomment la même `scores_matrix` et les métadonnées `is_eliminatory` des lignes critère (désormais alignées `dao_criteria` quand l’ID matche).

## Vérification manuelle suggérée

1. Workspace avec `evaluation_documents.scores_matrix` M14 + `dao_criteria` + `supplier_bundles`.  
2. `GET …/evaluation-frame` : `criteria[*].critere_nom` renseigné, `suppliers[*].name` lisible, scores visibles dans la grille.

## Sonde locale M14 vs M16 (SQL lecture seule)

Script : `scripts/probe_matrix_m14_m16.py` — charge `.env.local` / `.env`, utilise `DATABASE_URL`.

```bash
python scripts/probe_matrix_m14_m16.py --list 10
python scripts/probe_matrix_m14_m16.py <workspace_uuid>
```

Sortie JSON : forme détectée de `scores_matrix`, comptages bundles / `dao_criteria` / `criterion_assessments`, écarts de clés (si M14 imbriqué), échantillon lignes M16.
