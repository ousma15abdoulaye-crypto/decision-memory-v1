# Tableau comparatif production — LOT 4

**Date** : 2026-04-06

## Fonctions

- **`build_comparative_table_model(workspace_id)`** — projection DB **live** (`build_evaluation_projection`) — pour analyses hors export scellé.
- **`build_comparative_table_model_from_snapshot(snapshot)`** — **seule source** pour rendu XLSX après seal (pas de colonne gagnant, pas de classement global).

## XLSX

- Feuille **Comparatif** : fournisseur, critère, valeurs, scores, confiance ; pondéré export-only (commentaire cellule F1).
- Feuille **Traceability** : workspace, session, seal, versions schéma, `comparative_source`.

## Kill list

- Même sanitization que PV dans `scores_matrix` ; pas de `winner` / `rank` / etc. dans la matrice exposée.

## Tests

- `tests/services/test_comparative_table_model.py`.

## Preuve binaire XLSX

- Même contrainte que PV : export réel sur snapshot scellé en prod — **en attente** seal pilote.
