# Pass 1D — Process Linking Contract

**Version:** 1.0.0  
**Layer:** L7 (Process Linking)

## Input

| Field | Type | Source |
|-------|------|--------|
| normalized_text | str | Pass 0 output |
| document_id | str | Orchestrator |
| run_id | UUID | Orchestrator |
| pass_1a_output_data | dict | Pass 1A output_data |
| case_documents_1a | list[dict] or None | Other documents in the case (Pass 1A output_data each) |

## Output (output_data keys)

| Key | Type | Description |
|-----|------|-------------|
| m12_linking | dict | ProcessLinking payload |
| process_role | str | ProcessRole enum value |
| linked_parents_count | int | Number of parent links detected |
| suppliers_detected_count | int | Number of suppliers detected |

## Linking Levels (L7)

1. **EXACT_REFERENCE:** Identical procedure reference number. Confidence ~0.95.
2. **FUZZY_REFERENCE:** rapidfuzz ratio ≥ 0.85. Confidence ~0.85.
3. **SUBJECT_TEMPORAL:** Same project name or zone overlap. Confidence ~0.60-0.75.
4. **CONTEXTUAL:** Type pair implies relationship (e.g., offer → source_rules) but no reference match. Confidence ~0.40. Triggers Level 5 when LLM available.
5. **SEMANTIC_LLM:** LLM arbitration via `LLMArbitrator.semantic_link_documents`. Activated when a contextual pair is identified but fuzzy/reference matching is insufficient. Requires `MISTRAL_API_KEY` and `enabled=true` in `config/llm_arbitration.yaml`. Confidence capped at `thresholds.process_linking.max_llm_confidence` (default 0.80). Falls back to CONTEXTUAL (confidence 0.40) if LLM unavailable or confidence < 0.50.
6. **UNRESOLVED:** No linking criteria met at any level.

## Case-Level Operation

Pass 1D operates at case level. When `case_documents_1a` is provided, it links the source document to all other case documents. When absent, single-document mode with no links.
