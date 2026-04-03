# Golden Dataset — DMS Agent Evaluation

## Purpose

This directory contains golden (ground-truth) test cases for evaluating the
DMS regulatory compliance tools and agent pipeline. Each case represents a
real or synthetic procurement scenario with known expected outputs.

## Structure

```
data/golden/
├── README.md           # This file
├── cases/              # Individual case JSON files
│   ├── case_001.json
│   ├── case_002.json
│   └── ...
└── expected/           # Expected outputs per case
    ├── case_001_expected.json
    └── ...
```

## Case Format

Each `case_NNN.json` contains:

```json
{
  "case_id": "GOLDEN-001",
  "description": "SCI goods procurement, RFQ tier, Mali",
  "framework": "sci",
  "procurement_family": "goods",
  "estimated_value": 15000,
  "currency": "USD",
  "zone": "Bamako",
  "humanitarian_context": false,
  "m12_gates": [...],
  "tags": ["sci", "goods", "rfq", "non-humanitarian"]
}
```

## Expected Output Format

Each `case_NNN_expected.json` contains:

```json
{
  "case_id": "GOLDEN-001",
  "expected_regime": {
    "framework": "sci",
    "procedure_type": "request_for_quotation",
    "threshold_tier_name": "rfq"
  },
  "expected_principles_count": 9,
  "expected_sustainability_present": true,
  "expected_derogations": [],
  "expected_gate_categories": ["administrative", "eligibility"],
  "notes": "Standard SCI goods below ITB threshold"
}
```

## Evaluation

Run `scripts/eval_against_golden.py` to score the tool outputs against expected.

## Minimum Requirement (H1 Gate)

≥ 10 cases annotated before H1 gate closure.

## Contributing

1. Add a new `case_NNN.json` + `case_NNN_expected.json`
2. Run `scripts/eval_against_golden.py` to verify
3. Include in PR
