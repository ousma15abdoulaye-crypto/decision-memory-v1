# M4C Bundle Offer Extraction Execution Report

## 1. Contexte

Workspace GCF: `f1a6edfb-ac50-4301-a1a9-7a80053c632a`.

Fournisseurs runtime verifies:
- AZ bundle: `ed7dc0a5-3e1f-4d36-aa19-0e61bc0fca54`
- ATMOST bundle: `ed4884e6-23b0-44b8-81eb-caf83d57de0d`

Prerequis fermes avant M4C:
- M1 raw_text runtime termine pour AZ et ATMOST.
- M2 M12 classification document-level terminee.
- M3 Gate B runtime valide sur AZ et ATMOST.
- M4B bundle-level offer extraction task mergee et deployee.
- M4C-0B read-only snapshot endpoint merge et deployee.

## 2. Runtime readiness

Runtime deploye:
- `dms-db-worker`: `f8d48f90669109f24613d36999122d5b4d899619`
- `arq-worker`: `f8d48f90669109f24613d36999122d5b4d899619`

Readiness checks:
- `GET /diagnostics/v1/workspaces/{workspace_id}/bundles/{bundle_id}/m4c-pre-snapshot = 200`
- Snapshot endpoint authentifie: sans Bearer = `401`
- ARQ `WorkerSettings.functions` contient `extract_supplier_bundle_offer_task`
- `POST /arq/enqueue/bundle-offer-extract = 202` sur payload valide
- Backend annotation `/health = 200` depuis `arq-worker`
- Backend annotation `/ = 200` depuis `arq-worker`
- Backend annotation `/healthz = 404` accepte: le service expose `/health`

## 3. Correction runtime M4D

Premier essai AZ:
- `job_id = 4d0da7ed93094a979588a21d8f7eca66`
- `task_result = EXTRACTION_FAILED`
- Cause: `ANNOTATION_BACKEND_URL` absent sur `arq-worker`
- Fallback code: `http://localhost:8001`
- Effet DB: aucune ligne `offer_extractions` creee

Correction appliquee:
- `ANNOTATION_BACKEND_URL` configure sur `arq-worker`
- URL cible: service `dms-annotation-backend`
- Schema `https://` present
- Suffixe `/predict` absent
- Aucun patch code

## 4. Resultat AZ

Job:
- `job_id = e9a831ce7be44f8ebb07b0d23bb68fe2`
- `task_result = SUCCESS`
- `force = false`
- `duration = 75.78s`

Extraction:
- `offer_extractions_count_before = 0`
- `offer_extractions_count_after = 1`
- `extraction_id = ee89b512-0d47-40cb-a8b4-c487d555589c`
- `supplier_name = A - Z SARL`
- `extraction_ok = true`
- `review_required = false`
- `error_reason = null`
- `family_main = services`
- `family_sub = consultancy`
- `taxonomy_core = offer_technical`
- `fields_count = 15`
- `line_items_count = 0`
- `missing_fields = []`

Invariants non modifies:
- `raw_text_len = 68369`
- `raw_text_md5 = 658d41cefc0e1fcecfac9f365f1bc2a3`
- `m12_doc_kind = offer_combined`
- `m12_confidence = 0.8`
- `gate_b_role = scorable`

## 5. Resultat ATMOST

Job:
- `job_id = b4f5f8f82e5c4f749b1cd1a949f5fa8d`
- `task_result = SUCCESS`
- `force = false`
- `duration = 104.58s`

Extraction:
- `offer_extractions_count_before = 0`
- `offer_extractions_count_after = 1`
- `extraction_id = 5c25ea55-c37d-4062-ac2d-86080c0d505b`
- `supplier_name = ATMOST`
- `extraction_ok = true`
- `review_required = false`
- `error_reason = null`
- `family_main = services`
- `family_sub = consultancy`
- `taxonomy_core = dao`
- `fields_count = 15`
- `line_items_count = 0`
- `missing_fields = []`

Invariants non modifies:
- `raw_text_len = 145390`
- `raw_text_md5 = d08b92ad41342241e8f5959f45a49740`
- `m12_doc_kind = offer_combined`
- `m12_confidence = 0.8`
- `gate_b_role = scorable`

## 6. Interdits respectes

- `az_reenqueue_after_success = NO`
- `atmost_before_az_success = NO`
- `run_pipeline_v5 = NO`
- `m14 = NO`
- `bridge = NO`
- `matrix = NO`
- `scoring = NO`
- `force_true = NO`
- `direct_db_update = NO`
- `delete = NO`
- `code_change = NO`
- `commit = NO`

## 7. Verdict

`M4C_STATUS = DONE`

`BUNDLE_OFFER_EXTRACTION_RUNTIME_VALIDATED = YES`

M4C valide le passage controle `raw_text -> M12 -> Gate B -> offer_extractions` sur AZ et ATMOST. Les deux extractions ont ete produites bundle par bundle, sans pipeline large et sans mutation des invariants amont.

`NEXT_ACTION_PROPOSED = M5_DIAG_EVALUATION_INPUTS_OR_M14_READINESS`

`STATUS = WAITING_CTO_GO`
