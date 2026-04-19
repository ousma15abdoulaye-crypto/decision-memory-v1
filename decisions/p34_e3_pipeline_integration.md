# P3.4 E3 — Rapport d’intégration pipeline V5 (opposable)

**Référence** : `P3.4-E3-PIPELINE-ORCHESTRATION`  
**Date** : 2026-04-19  
**Branche cible** : `feat/p3-4-matrixrow-builder-summary`

---

## 1. Point d’insertion exact (fichier:ligne, fenêtre L1453–L1471)

**OUI**

Après le bloc `try` / `populate_assessments_from_m14(...)` (succès bridge) et **avant** `out.completed = True`, le service appelle la projection matrice (`build_matrix_projection_for_pipeline`) puis assigne `out.matrix_rows` et `out.matrix_summary`. La fenêtre correspond au mandat (post-M14 persisté + bridge, pré-complétion).

---

## 2. Extension `PipelineV5Result` additive conforme

**OUI**

Champs ajoutés uniquement, sans retrait ni renommage des champs existants :

- `matrix_rows: list[MatrixRow] = Field(default_factory=list)`
- `matrix_summary: MatrixSummary | None = None`

`extra="forbid"` conservé sur le modèle.

---

## 3. Tiebreak E2→E3 intégré (CTO A2)

**OUI**

Dans `matrix_builder_service.py`, le tri des rangs comparables utilise une clé déterministe `(-total_score_system, str(bundle_id))` (chemins principal et sous-cohorte partial sustainability), garantissant le même ordre de rangs pour des scores identiques.

---

## 4. Gestion fallbacks (vide, gate absent, `pipeline_run_id`, seuil technique)

**OUI**

- `offer_evaluations` vide → `matrix_rows == []`, résumé avec `total_bundles == 0`, `cohort_comparability_status == NOT_COMPARABLE` (logique cohorte du builder).
- `gate_output is None` dans `build_matrix_projection_for_pipeline` → `ValueError` explicite (pas de fallback silencieux).
- **`pipeline_run_id` (E0.6)** : `run_pipeline_v5` passe `pipeline_run_id=None` au helper ; `build_matrix_projection_for_pipeline` applique `uuid4()` lorsque aucun id n’est fourni (aucun id pipeline stable exposé en amont dans cette fonction aujourd’hui).
- Seuil technique : lecture optionnelle `technical_threshold_mode` sur `process_workspaces` ; colonne absente / erreur SQL → `None` → builder applique `MANDATORY` + flag `TECHNICAL_THRESHOLD_MODE_DEFAULT_APPLIED`.
- Rapport M14 absent au point de projection (invariant violé) → `PipelineError` explicite avant projection.

---

## 5. Tests d’intégration unit

**PASSED (8)**

Fichier : `tests/unit/services/test_pipeline_v5_matrix_integration.py`  
Scénarios : nominal 3 fournisseurs, évaluations vides, `gate_output` absent, sérialisation JSON `PipelineV5Result`, flag seuil par défaut, idempotence (même `pipeline_run_id`), ex-aequo par `bundle_id`, préservation des champs pré-matrice sur le résultat pipeline.

---

## 6. Non-régression pipeline pré-existant

**OUI**

`pytest tests/unit/ -q` : **456 passed** (448 + 8), **6 warnings** inchangés en nature (dépréciations / SWIG existantes).

---

## 7. Verdict

**READY FOR E4**

E3 respecte le périmètre : câblage minimal dans `pipeline_v5_service.py`, tests unit ciblés, tiebreak A2 dans le même lot fonctionnel que le mandat, sans migration, sans toucher aux modèles E1 gelés ni moteurs M14 / bridge / `eligibility_models`.
