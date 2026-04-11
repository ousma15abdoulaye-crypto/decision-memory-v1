# Runbook — validation synthétique R1 / R3 (M-V52-A)

## Contexte

Les ruptures **R1** (bridge M14 → `criterion_assessments`) et **R3** (persistance `market_delta_pct`) sont codées ; ce runbook décrit comment les **prouver** sans dépendre d’un dump production.

## Prérequis

- `DATABASE_URL` (psycopg) vers une base **Alembic head**.
- Extensions PostgreSQL : `pg_trgm` (déjà requise pour le lookup marché).

## R1 — Bridge M14 → M16

1. Créer un tenant, un `process_workspaces`, un `committees` + `cases` si nécessaire pour la FK `evaluation_documents.committee_id`.
2. Insérer `supplier_bundles` (`bundle_index` unique par workspace) et `dao_criteria` avec `id` = clé utilisée dans la matrice.
3. Insérer `evaluation_documents` avec `scores_matrix` de la forme  
   `{ "<bundle_uuid>": { "<criterion_id>": { "score": 0.8, "confidence": 0.8 } } }`.
4. Appeler `populate_assessments_from_m14(workspace_id)` (ou `_run_bridge` dans un test avec connexion partagée).
5. Vérifier SQL :  
   `SELECT cell_json->>'source' FROM criterion_assessments WHERE workspace_id = …` → `m14`.

**Automatisation :** `pytest tests/integration/test_v52_r1_r3_synthetic.py::TestV52R1BridgeSynthetic -m db`

## R3 — Delta marché

1. Renseigner `process_workspaces.zone_id` avec un `geo_master.id` existant.
2. Insérer (ou réutiliser) une ligne `couche_b.procurement_dict_items` et une ligne `market_signals_v2` avec le même `item_id` (slug attendu après normalisation du libellé prix) et `price_seasonal_adj` > 0, `signal_quality` ∈ {strong, moderate, propagated}.
3. Créer `price_line_comparisons` + `price_line_bundle_values` avec un `label` qui normalise vers ce `item_id`.
4. Appeler `persist_market_deltas_for_workspace(conn, workspace_id)`.
5. Vérifier `price_line_bundle_values.market_delta_pct` non NULL et cohérent avec  
   `(amount - price_seasonal_adj) / price_seasonal_adj`.

**Automatisation :** `pytest tests/integration/test_v52_r1_r3_synthetic.py::TestV52R3MarketDeltaSynthetic -m db`

## Après succès CI local

Mettre à jour la légende **RUPTURES_V52** : R1 / R3 — implémentation validée par tests synthétiques (en complément des données réelles Railway).
