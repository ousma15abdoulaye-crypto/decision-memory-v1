# Pass 1C — Conformity & Handoffs Contract

**Version:** 1.0.0  
**Layers:** L6 (Conformity Signal) + H1/H2/H3 (Handoffs)

## Input

| Field | Type | Source |
|-------|------|--------|
| normalized_text | str | Pass 0 output |
| document_id | str | Orchestrator |
| run_id | UUID | Orchestrator |
| document_kind_str | str | Pass 1A |
| is_composite | str | Pass 1A (m12_recognition.is_composite.value) |
| validity_dict | dict | Pass 1B (m12_validity serialized) |
| framework_str | str | Pass 1A |
| framework_confidence | float | Pass 1A |
| family_str | str | Pass 1A |
| family_sub_str | str | Pass 1A |

## Output (output_data keys)

| Key | Type | Description |
|-----|------|-------------|
| m12_conformity | dict | DocumentConformitySignal payload |
| m12_handoffs | dict | M12Handoffs payload (H1 + H2 + H3) |
| conformity_status | str | "conforme"/"non_conforme"/"partiellement_conforme"/"non_statuable" |

## Handoffs

- **H1 (regulatory_profile_skeleton):** Only for source_rules documents. Prepared for M13.
- **H2 (atomic_capability_skeleton):** Only for source_rules documents. Prepared for M14.
- **H3 (market_context_signal):** For any document with price/market signals. Prepared for M14.

Handoffs PREPARE data — they never APPLY rules (M12 V6 S18).
