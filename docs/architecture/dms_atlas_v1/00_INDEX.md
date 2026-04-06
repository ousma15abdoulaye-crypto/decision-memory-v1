# DMS Architecture Atlas — Index (V1)

**Branche de travail** : `docs/dms-atlas-v1-2026-04`  
**Date de génération** : 2026-04-06  
**Mandat** : Production documentaire exhaustive (10 livrables), priorité P0→P3.

## Périmètre des fichiers livrés (liste fermée)

Tous les artefacts de ce mandat résident sous :

- [`docs/architecture/dms_atlas_v1/`](.)

Aucun autre répertoire n’a été modifié pour cette livraison.

## Annexes générées

| Fichier | Description |
|--------|-------------|
| [`ANNEX_A_openapi.json`](ANNEX_A_openapi.json) | Schéma OpenAPI 3.1 exporté depuis `main.app` (FastAPI). |
| [`ANNEX_B_traceability_inv.md`](ANNEX_B_traceability_inv.md) | Traçabilité INV → code (extrait du dépôt). |

## Livrables par priorité

| Priorité | ID | Document |
|----------|-----|----------|
| P0 | L2 | [`P0_L2_cognitive_engine.md`](P0_L2_cognitive_engine.md) |
| P0 | L3 | [`P0_L3_extraction_pipeline.md`](P0_L3_extraction_pipeline.md) |
| P0 | L4 | [`P0_L4_api_contract.md`](P0_L4_api_contract.md) |
| P1 | L5 | [`P1_L5_database.md`](P1_L5_database.md) |
| P1 | L1 | [`P1_L1_module_map.md`](P1_L1_module_map.md) |
| P2 | L6 | [`P2_L6_mql.md`](P2_L6_mql.md) |
| P2 | L7 | [`P2_L7_security.md`](P2_L7_security.md) |
| P3 | L8 | [`P3_L8_offline.md`](P3_L8_offline.md) |
| P3 | L9 | [`P3_L9_infra.md`](P3_L9_infra.md) |
| P3 | L10 | [`P3_L10_tests.md`](P3_L10_tests.md) |

## Glossaire rapide : E0–E6 vs statuts workspace

- **Source de vérité en base** : colonne `process_workspaces.status` (et données associées : packages source, bundles, scores). Il n’existe **pas** de colonne `cognitive_state` persistée comme autorité (projection — INV-C01, voir [`P0_L2_cognitive_engine.md`](P0_L2_cognitive_engine.md)).
- **E0–E6** : identifiants dérivés par `compute_cognitive_state()` dans [`src/cognitive/cognitive_state.py`](../../../src/cognitive/cognitive_state.py).
- **FSM annotation (M12)** : états distincts (`AnnotationPipelineState` dans [`src/annotation/orchestrator.py`](../../../src/annotation/orchestrator.py)) — ne pas confondre avec E0–E6.

## Clause de complétude (auto-évaluation)

- Toute couche est **documentée** ou marquée **NON IMPLÉMENTÉ / NON TRANCHÉ** avec pointeur code ou absence avérée.
- Endpoints : inventaire dans **ANNEX_A** + synthèse **L4**.
- Tables : inventaire **L5** ; DDL complet = **chaîne Alembic** (pas recopiée en entier dans ce dossier).
- Écarts canon : voir aussi [`docs/audits/GAP_MATRIX_V431_J1_J17_AND_INVARIANTS.md`](../../audits/GAP_MATRIX_V431_J1_J17_AND_INVARIANTS.md).

## Référence d’autorité (rappel)

Hiérarchie : `docs/freeze/DMS_V4.1.0_FREEZE.md`, `docs/freeze/CONTEXT_ANCHOR.md`, mandats CTO — voir [`CLAUDE.md`](../../../CLAUDE.md).
