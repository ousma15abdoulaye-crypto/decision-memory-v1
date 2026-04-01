# Pass 1A — Core Recognition Contract

**Version:** 1.0.0  
**Layers:** L1 (Framework) + L2 (Family) + L3 (Document Type)

## Input

| Field | Type | Source |
|-------|------|--------|
| normalized_text | str | Pass 0 output |
| document_id | str | Orchestrator |
| run_id | UUID | Orchestrator |
| quality_class | str | Pass 0.5 output ("good"/"degraded"/"poor"/"ocr_failed") |
| block_llm | bool | Pass 0.5 output |

## Output (output_data keys)

| Key | Type | Description |
|-----|------|-------------|
| m12_recognition | dict | Full ProcedureRecognition payload (serialized) |
| document_role | str | Legacy backward-compat: document kind value |
| taxonomy_core | str | Legacy backward-compat: document kind value |
| routing_confidence | float | Discretized to {0.6, 0.8, 1.0} |
| routing_source | str | Enum: "deterministic", "hybrid_deterministic_llm", "deterministic_blocked" |
| matched_rule | str | Rule ID that matched |
| deterministic | bool | True if deterministic path only; False when LLM overrides the result |
| routing_evidence | list[str] | Evidence list |
| routing_failure_reason | str or None | None unless unresolved |

## Quality Gate Integration

| quality_class | Behavior |
|---------------|----------|
| good | Full processing |
| degraded | Confidence ceiling 0.60, auto review_required |
| poor | If block_llm: unknown/not_assessable on everything |
| ocr_failed | Orchestrator routes to REVIEW_REQUIRED before 1A |
