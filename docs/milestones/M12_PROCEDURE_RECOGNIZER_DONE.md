# M12 — PROCEDURE RECOGNIZER (industrialisation pipeline)

**Statut** : **DONE** (2026-03-26) — aligné `docs/freeze/MRD_CURRENT_STATE.md` (`last_completed` M12, `last_tag` `v4.1.0-m12-done`, commit `bde8378`).

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

## Preuve (DoD) — clôture M12 / MRD

Ces critères correspondent au registre MRD (`JALONS`, `last_tag`, `last_merge_commit`).

- [x] Passes 0 / 0.5 / 1 + orchestrateur + tests CI sans appel API réel (REGLE-21).
- [x] Corpus terrain **N ≥ 50** exploitable pour calibration (export JSONL dédié M12 ; voir `data/annotations/` et scripts ci-dessus).
- [x] Tag jalonnement **`v4.1.0-m12-done`** associé au commit de clôture (`bde8378` dans le MRD ; création / push Git selon pratique équipe — merge PR `main` = **agent**, `CLAUDE.md`).

## Suivi qualité (non bloquant pour l’enregistrement M12 dans le MRD)

À poursuivre ou confirmer selon besoin produit / terrain :

- [ ] Table §3 `docs/contracts/annotation/PASS_0_5_EMPIRICAL_THRESHOLDS.md` : ligne terrain complète (percentiles dérivés sur le corpus exporté).
- [ ] Macro-F1 / précision-rappel classifieur `document_role` ≥ 0.70 sur corpus exporté (`m12_calibrate_classifier_metrics.py`).

## Transition M13 — prérequis (hors `blocked_on` MRD)

Le MRD porte `blocked_on : (vide)` pour M13 ; les points suivants sont des **prérequis d’exécution** listés sous `m13_prerequisites` dans `MRD_CURRENT_STATE.md` :

- ADR LLM (RÈGLE-11).
- Wiring `backend.py` / gel backend si GO CTO.
- Sync Railway si GO CTO (cf. état Alembic dans le MRD).

## Export JSONL

`scripts/export_ls_to_dms_jsonl.py` — flux `m12-v2` ; pour dérivation seuils / calibration, s’assurer que le texte source exploitable est présent par ligne (merge depuis LS si besoin, selon mandat AO).
