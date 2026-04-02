# ADR-M14-001 — Evaluation Engine (M14)

**Statut :** Accepté (implémentation)  
**Date :** 2026-04-02  
**Référence spec :** DMS V4.1.0 — Phase 5, Milestone M14  
**Prérequis :** M12 DONE (PR #274), M13 DONE (PR #292 + PR #293 hardening)

## Contexte

M14 reçoit les handoffs structurés de M12 (H2 `AtomicCapabilitySkeleton`, H3 `MarketContextSignal`) et de M13 (RH1 `ComplianceChecklist`, RH2 `EvaluationBlueprint`) pour produire une **évaluation comparative des offres** par dossier (case).

M14 **évalue** ; il ne **décide** pas. Tout résultat est soumis au comité humain.

## Décisions

### 1. Architecture — Moteur d'évaluation déterministe

- **`src/procurement/m14_engine.py`** — `EvaluationEngine` : orchestrateur principal.
  - Consomme les 4 handoffs (H2, H3, RH1, RH2) + `ProcessLinking` (Pass 1D).
  - Produit un `EvaluationReport` par dossier (case).
  - Aucun LLM dans M14 V1 — déterministe pur.

### 2. Modèles Pydantic — `extra="forbid"` partout (E-49)

- **`src/procurement/m14_evaluation_models.py`** — modèles typés.
- `M14Confidence = Literal[0.6, 0.8, 1.0]` — réutilise la même grille DMS.
- Champs interdits (RÈGLE-09 Kill List) : `winner`, `rank`, `recommendation`, `offre_retenue`.
- Chaque offre reçoit un `OfferEvaluation` avec :
  - `eligibility_result` : résultat checklist éliminatoire (pass/fail/indeterminate).
  - `technical_score` : score technique pondéré si `scoring_structure` disponible.
  - `price_analysis` : analyse prix avec référence mercuriale si `MarketContextSignal` non-None.
  - `compliance_results` : résultats des checks RH1 par offre.
  - `flags` : alertes (pondération incohérente, devise différente, etc.).

### 3. Persistance — table `evaluation_documents` (migration 056)

- **`src/procurement/m14_evaluation_repository.py`** — CRUD sur `evaluation_documents`.
- Utilise `get_connection()` (contexte tenant RLS).
- Versionnement par `(case_id, version)` — unique index existant.
- `scores_matrix` JSONB : `EvaluationReport.model_dump(mode="json")`.
- Statut initial = `"draft"`.
- Aucun `committee_id` requis à la création (M14 prépare, le comité scelle).

### 4. API — routes `/api/m14/`

- **`src/api/routes/evaluation.py`** — routeur FastAPI.
- `POST /api/m14/evaluate` : lance l'évaluation d'un case.
- `GET /api/m14/evaluations/{case_id}` : lit le dernier résultat.
- Auth `Depends(get_current_user)` sur toutes les routes.

### 5. Interdictions (STOP signals)

- **RÈGLE-09** : `winner`, `rank`, `recommendation`, `offre_retenue` = INTERDITS dans tout payload M14.
- M14 ne produit pas de verdict d'attribution — uniquement des scores et analyses.
- M14 ne modifie pas les données M12/M13 (append-only).
- Le statut `"sealed"` dans `evaluation_documents` ne peut être posé que par le comité humain.

### 6. Wiring Pass 2A → M14

- `run_passes_0_to_1` transmet `case_id` à `run_passes_1a_to_1d` pour que Pass 2A produise RH1/RH2.
- Le backend `/predict` résout `case_id` depuis `task.data.case_id`.
- M14 peut fonctionner en mode offline (fixtures/mocks) si Pass 2A n'est pas encore actif en prod.

## Conséquences

- Nouvelle migration **non requise** : table `evaluation_documents` existe (056).
- Mise à jour CI : `VALID_ALEMBIC_HEADS` inchangé (pas de nouvelle migration).
- Aucun nouveau contrat documentaire créé par cette ADR (contrat éventuel en phase ultérieure).
- Mise à jour `CONTEXT_ANCHOR` et `MRD_CURRENT_STATE` après merge.
