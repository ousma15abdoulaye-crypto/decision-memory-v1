# Pass 1B — Document Validity Contract

**Version:** 1.0.0  
**Layers:** L4 (Mandatory Parts) + L5 (Validity Judgment)

## Input

| Field | Type | Source |
|-------|------|--------|
| normalized_text | str | Pass 0 output |
| document_id | str | Orchestrator |
| run_id | UUID | Orchestrator |
| document_kind | str | Pass 1A output (m12_recognition.document_kind.value) |
| quality_class | str | Pass 0.5 output |

## Output (output_data keys)

| Key | Type | Description |
|-----|------|-------------|
| m12_validity | dict | Full DocumentValidity payload (serialized) |
| document_kind | str | Echo of input kind |
| validity_status | str | "valid"/"invalid"/"partial"/"not_assessable" |
| mandatory_coverage | float | 0.0 to 1.0 |
| mandatory_parts_present | list[str] | Names of detected parts |
| mandatory_parts_missing | list[str] | Names of missing parts |

## Detection Levels

1. **Level 1 — Heading Match:** Regex against section headings. Confidence ~0.90.
2. **Level 2 — Keyword Density:** Keyword count in sliding window. Confidence ~0.75.
3. **Level 3 — LLM Fallback:** Implemented via `llm_arbitrator`. Decision threshold comes from each rule's `rule.threshold` + `max_llm_confidence` cap (defined in `config/mandatory_parts/*.yaml`), **not** from `thresholds.mandatory_parts_l3` in `llm_arbitration.yaml`. Confidence ≤ `max_llm_confidence` (typically 0.70). Pass 1B does **not** emit a `requires_human_review` field nor force `review_required` status automatically; that decision is made downstream by the validator based on confidence and coverage thresholds.
