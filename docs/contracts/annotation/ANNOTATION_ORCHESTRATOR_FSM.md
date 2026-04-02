# ANNOTATION_ORCHESTRATOR_FSM — Machine à états (pipeline annotation)

**Version** : `1.1.0`  
**Date** : 2026-04-02  
**Subordonné** : [PASS_OUTPUT_STANDARD.md](./PASS_OUTPUT_STANDARD.md), contrats Pass 0 / 0.5 / 1

---

## 1. États (`AnnotationPipelineState`)

| État | Description |
| --- | --- |
| `ingested` | Document connu ; texte brut ou URI stockage disponible |
| `pass_0_done` | Pass 0 (ingestion) a produit `AnnotationPassOutput` `success` ou `degraded` avec `normalized_text` non vide |
| `quality_assessed` | Pass 0.5 a produit une `quality_class` |
| `routed` | Pass 1 a produit `document_role` / `taxonomy_core` |
| `llm_preannotation_pending` | En attente d’appel LLM (si non bloqué) |
| `llm_preannotation_done` | JSON brut LLM disponible |
| `validated` | Validation déterministe (Pydantic / règles locales) OK |
| `review_required` | Sortie LS / humain requis |
| `annotated_validated` | Ground truth humain scellé (RÈGLE-25) |
| `rejected` | Document exclu du corpus |
| `dead_letter` | Échec non récupérable après retries |

### 1.1 Sous-passes M12 et Pass 2A (impl. `src/annotation/orchestrator.py`)

Lorsque `ANNOTATION_USE_M12_SUBPASSES=1`, la chaîne **1A → 1B → 1C → 1D** remplace le routage Pass 1 monolithique. Les états persistés incluent :

| État | Description |
| --- | --- |
| `pass_1a_done` | Pass 1A (reconnaissance cœur) terminé avec succès |
| `pass_1b_done` | Pass 1B (validité documentaire) terminé |
| `pass_1c_done` | Pass 1C (conformité + handoffs M12) terminé |
| `pass_1d_done` | Pass 1D (lien processus) terminé |

**Pass 2A (M13 — profil réglementaire)** : si `ANNOTATION_USE_PASS_2A=1`, après `pass_1d_done` l’orchestrateur enchaîne Pass 2A puis positionne l’état à `pass_2a_done`. Si le flag est à **0**, `pass_1d_done` est **terminal** pour la séquence M12 (aucun 2A). Contrat : [PASS_2A_REGULATORY_PROFILE_CONTRACT.md](./PASS_2A_REGULATORY_PROFILE_CONTRACT.md).

---

## 2. Transitions principales

```mermaid
stateDiagram-v2
  direction LR
  ingested --> pass_0_done: Pass0 success_or_degraded
  pass_0_done --> quality_assessed: Pass0_5 success
  quality_assessed --> routed: Pass1 success_and_not_block_llm
  quality_assessed --> review_required: quality_class ocr_failed_or_poor_mandate
  routed --> llm_preannotation_pending: policy_allows_llm
  llm_preannotation_pending --> llm_preannotation_done: LLM_OK
  llm_preannotation_done --> validated: schema_OK
  validated --> review_required: spot_check_or_rules
  review_required --> annotated_validated: human_seal
  pass_0_done --> dead_letter: Pass0 failed_after_retry
  quality_assessed --> dead_letter: Pass0_5 failed_after_retry
  routed --> dead_letter: Pass1 failed_after_retry
```

*(Diagramme indicatif — l’implémentation peut regrouper `llm_*` dans l’adapter LS.)*

---

## 3. Garde-fous

| Garde | Action |
| --- | --- |
| Pass 0.5 `block_llm = true` | Interdire transition vers `llm_preannotation_pending` |
| `quality_class = ocr_failed` | Forcer `review_required` ou `rejected` selon mandat |
| Timeout passe | Retry `N` fois (défaut **2**) puis `dead_letter` ou `review_required` |

---

## 4. Timeouts recommandés (ms) — à ajuster par mandat

| Passe | Timeout ms | Notes |
| --- | ---: | --- |
| Pass 0 | 60_000 | I/O + normalisation |
| Pass 0.5 | 5_000 | CPU seul |
| Pass 1 (déterministe) | 5_000 | Regex |
| Pass 1 (LLM) | 120_000 | Aligné `ANNOTATION_TIMEOUT` backend |

---

## 5. Persistance

- **Minimal** : `run_id` + état courant + derniers `AnnotationPassOutput` sérialisés (JSON) par document.
- **Enterprise** : table `annotation_pipeline_runs` (mandat Alembic séparé).

---

## 6. Observabilité obligatoire par transition

Journaliser : `run_id`, `document_id`, `from_state`, `to_state`, `pass_name`, `duration_ms`, `status`, `error_codes`.
