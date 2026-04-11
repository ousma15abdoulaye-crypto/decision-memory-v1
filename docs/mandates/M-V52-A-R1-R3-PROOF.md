# Mandat CTO — M-V52-A — Preuves synthétiques R1 / R3

**Statut :** Émis pour exécution (plan correction enterprise-grade)  
**Date :** 2026-04-11  
**Référence :** `docs/audit/RUPTURES_V52.md` (R1 bridge M14→M16, R3 `market_delta_pct`)

## Objectif mesurable

1. **R1** : Sur une base de test avec `evaluation_documents.scores_matrix`, `supplier_bundles`, `dao_criteria` cohérents, un appel au bridge produit au moins une ligne `criterion_assessments` avec `cell_json->>'source' = 'm14'`.
2. **R3** : Sur une base avec `process_workspaces.zone_id`, `price_line_bundle_values`, `market_signals_v2` (item×zone) et `pg_trgm`, `persist_market_deltas_for_workspace` met à jour `market_delta_pct` avec une valeur numérique attendue.

## Périmètre fichiers (liste close)

| Action | Chemins |
|--------|---------|
| Autorisé | `tests/integration/test_v52_r1_r3_synthetic.py` |
| Autorisé | `docs/mandates/M-V52-A-R1-R3-PROOF.md` |
| Autorisé | `docs/ops/RUNBOOK_V52_R1_R3_SYNTHETIC_VALIDATION.md` |
| Autorisé | `docs/audit/RUPTURES_V52.md` (statuts / légende) |
| Autorisé | `docs/freeze/CONTEXT_ANCHOR.md`, `docs/freeze/MRD_CURRENT_STATE.md` (lignes trace mandat) |
| Autorisé | `tests/services/test_pv_builder.py` (extension stubs `score_history` / `m13` si nécessaire) |
| Autorisé | `src/services/market_signal_lookup.py` — cast **REAL** pour `set_limit` / `similarity` (compatibilité `pg_trgm`) |

**Interdit sans autre mandat :** `alembic/versions/`, `services/annotation-backend/`, `schema_validator.py`, `DMS_V4.1.0_FREEZE.md`.

## Definition of Done

- `ruff check` / `black --check` sur les fichiers Python touchés.
- `pytest tests/integration/test_v52_r1_r3_synthetic.py -m db` passe lorsque `DATABASE_URL` pointe vers une DB migrée à `head` et contient au minimum une ligne `geo_master`, `couche_b.procurement_dict_items` (sinon tests R3 skippés avec raison explicite).
- Runbook ops reproduit la logique métier en langage humain.

## Non-objectifs (mandats suivants)

- Apply prod Railway 093→095 (mandat B).
- PV complet R4/R6 au-delà des tests unitaires existants sur `pv_builder`.
- Unification RBAC (mandat H).
