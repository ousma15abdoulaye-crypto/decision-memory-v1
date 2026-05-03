# M3C Gate B Execution Report

## 1. Contexte

Workspace GCF: `f1a6edfb-ac50-4301-a1a9-7a80053c632a`.

Fournisseurs runtime verifies:
- AZ bundle: `ed7dc0a5-3e1f-4d36-aa19-0e61bc0fca54`
- ATMOST bundle: `ed4884e6-23b0-44b8-81eb-caf83d57de0d`

Prerequis fermes avant M3C:
- M1 raw_text runtime termine pour AZ et ATMOST.
- M2 M12 classification document-level terminee.
- M3B Gate B role state merge et deployee sur worker HTTP + ARQ.

## 2. Runtime readiness

Runtime deploye:
- `dms-db-worker`: `f1b2c6298931b9615a0345b2b7970ccf493a58e9`
- `arq-worker`: `f1b2c6298931b9615a0345b2b7970ccf493a58e9`

Readiness checks:
- `GET /healthz = 200`
- `POST /arq/enqueue/bundle-gate-b-qualify` sans Bearer = `401`
- `POST /arq/enqueue/bundle-gate-b-qualify` payload invalide avec Bearer = `422`
- ARQ `WorkerSettings.functions` contient `qualify_supplier_bundle_gate_b_task`
- Migration `102_v11_bundle_gate_b_role` appliquee
- Colonnes presentes: `gate_b_role`, `gate_b_reason_codes`, `gate_b_evidence`, `gate_b_evaluated_at`, `gate_b_evaluated_by`

## 3. Resultat AZ

Job:
- `job_id = 485f49d16e1c4cc5ac86946abcfbd78e`
- `task_result = SUCCESS`
- `force = false`

Gate B:
- `gate_b_role = scorable`
- `gate_b_reason_codes = ["supplier_offer_with_present_raw_text"]`
- `gate_b_evidence` present
- `gate_b_evaluated_at = 2026-04-30T17:57:56.954032+00:00`
- `gate_b_evaluated_by = bundle_gate_b_service`

Completeness:
- `completeness_score = 0.33`
- `missing_documents = ["nif", "rccm"]`

Invariants non modifies:
- `raw_text_len = 68369`
- `raw_text_md5 = 658d41cefc0e1fcecfac9f365f1bc2a3`
- `m12_doc_kind = offer_combined`
- `m12_confidence = 0.8`
- `qualification_status = pending`
- `is_retained = false`

## 4. Resultat ATMOST

Job:
- `job_id = 1efa8e3e393d4d24b3f8b2e5d1b03aae`
- `task_result = SUCCESS`
- `force = false`

Gate B:
- `gate_b_role = scorable`
- `gate_b_reason_codes = ["supplier_offer_with_present_raw_text"]`
- `gate_b_evidence` present
- `gate_b_evaluated_at = 2026-04-30T18:02:47.056913+00:00`
- `gate_b_evaluated_by = bundle_gate_b_service`

Completeness:
- `completeness_score = 0.33`
- `missing_documents = ["nif", "rccm"]`

Invariants non modifies:
- `raw_text_len = 145390`
- `raw_text_md5 = d08b92ad41342241e8f5959f45a49740`
- `m12_doc_kind = offer_combined`
- `m12_confidence = 0.8`
- `qualification_status = pending`
- `is_retained = false`

## 5. Interdits respectes

- `scoring = NO`
- `matrix = NO`
- `force_true = NO`
- `direct_db_update = NO`
- `delete = NO`
- `full_pipeline = NO`
- `raw_text_update = NO`
- `m12_update = NO`
- `qualification_status_update = NO`
- `is_retained_update = NO`

## 6. Verdict

`M3C_STATUS = DONE`

`GATE_B_RUNTIME_VALIDATED = YES`

Gate B est validee runtime sur AZ et ATMOST: les deux bundles sont `scorable` comme offres presentes, avec pieces administratives manquantes tracees, sans mutation des couches aval.

`NEXT_ACTION = M4_EXTRACTION_EVALUATION_DIAG`
