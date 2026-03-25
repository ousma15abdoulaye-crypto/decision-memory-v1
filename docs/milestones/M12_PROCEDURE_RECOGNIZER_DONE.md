# M12 — PROCEDURE RECOGNIZER (industrialisation pipeline)

**Statut** : livrables code présents — **tag Git** `v4.1.0-m12-done` à créer par AO après validation terrain.

## Livrables

| Élément | Emplacement |
| --- | --- |
| Pass 0 Ingestion | `src/annotation/passes/pass_0_ingestion.py` |
| Pass 0.5 Quality Gate | `src/annotation/passes/pass_0_5_quality_gate.py` |
| Pass 1 Router | `src/annotation/passes/pass_1_router.py` |
| Orchestrateur FSM | `src/annotation/orchestrator.py` |
| Feature flag | `ANNOTATION_USE_PASS_ORCHESTRATOR` (défaut `0`) — `src/annotation/orchestrator.py` |
| Dérive seuils | `scripts/derive_pass_0_5_thresholds.py` |
| Calibration P/R | `scripts/m12_calibrate_classifier_metrics.py` |
| Prérequis OCR / bridge | `docs/operations/M12_OCR_BRIDGE_PREREQ.md` |
| Tests | `tests/annotation/test_m12_passes.py` |

## Preuve (DoD)

- [x] Passes 0 / 0.5 / 1 + orchestrateur + tests CI sans appel API réel (REGLE-21).
- [ ] `N ≥ 50` documents terrain + table §3 `PASS_0_5_EMPIRICAL_THRESHOLDS.md` complétée par AO.
- [ ] Macro-F1 / précision-rappel classifieur `document_role` ≥ 0.70 sur corpus exporté (`m12_calibrate_classifier_metrics.py`).
- [ ] Tag `v4.1.0-m12-done` sur le commit validé.

## Export JSONL

`scripts/export_ls_to_dms_jsonl.py` — produit `m12-v2` sans `source_text` dans chaque ligne ; pour calibration, fusionner le texte tâche (LS) dans un champ `source_text` par ligne ou étendre le flux d’export sous mandat AO.
