# M12 Benchmark — bootstrap_75

**Date**: 2026-03-30T19:37:56Z
**Corpus**: 75 annotations (export_ok=100%)

## Threshold Checks

| Check | Target | Actual | Pass |
|-------|--------|--------|------|
| document_kind_parent_accuracy_n5 | 0.80 | 0.8209 | PASS |
| evaluation_doc_non_offer_recall | 1.00 | 1.0000 | PASS |
| framework_detection_accuracy | 0.85 | 0.8649 | PASS |

## Global Metrics

- Accuracy (global): **0.7733**
- Accuracy (n>=5 types): **0.8209**
- Macro P/R/F1: 0.4050 / 0.3656 / 0.3813
- Types with n>=5: ['dao', 'offer_financial', 'offer_technical', 'supporting_doc']
- Types below n<5: ['contract', 'evaluation_doc', 'itt', 'offer_combined', 'po', 'rfq', 'tdr', 'unknown']

## Per-Class Metrics

| Type | P | R | F1 | Support |
|------|---|---|----|---------| 
| contract | 0.0000 | 0.0000 | 0.0000 | 0 |
| dao | 0.8571 | 1.0000 | 0.9231 | 12 |
| evaluation_doc | 0.3333 | 0.3333 | 0.3333 | 3 |
| itt | 0.0000 | 0.0000 | 0.0000 | 1 |
| offer_combined | 0.0000 | 0.0000 | 0.0000 | 1 |
| offer_financial | 0.9231 | 0.8000 | 0.8571 | 15 |
| offer_technical | 0.9286 | 0.8667 | 0.8966 | 15 |
| po | 0.0000 | 0.0000 | 0.0000 | 0 |
| rfq | 0.0000 | 0.0000 | 0.0000 | 0 |
| supporting_doc | 0.8182 | 0.7200 | 0.7660 | 25 |
| tdr | 1.0000 | 0.6667 | 0.8000 | 3 |
| unknown | 0.0000 | 0.0000 | 0.0000 | 0 |

## Confusion Matrix

Rows = ground truth, Cols = predicted

| |contract|dao|evaluation_doc|itt|offer_combined|offer_financial|offer_technical|po|rfq|supporting_doc|tdr|unknown|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| contract |0|0|0|0|0|0|0|0|0|0|0|0|
| dao |0|12|0|0|0|0|0|0|0|0|0|0|
| evaluation_doc |0|0|1|0|0|0|0|0|0|2|0|0|
| itt |0|1|0|0|0|0|0|0|0|0|0|0|
| offer_combined |0|0|0|0|0|0|0|0|1|0|0|0|
| offer_financial |0|0|0|0|1|12|1|0|0|1|0|0|
| offer_technical |0|0|0|0|0|1|13|0|0|1|0|0|
| po |0|0|0|0|0|0|0|0|0|0|0|0|
| rfq |0|0|0|0|0|0|0|0|0|0|0|0|
| supporting_doc |1|0|2|0|0|0|0|1|0|18|0|3|
| tdr |0|1|0|0|0|0|0|0|0|0|2|0|
| unknown |0|0|0|0|0|0|0|0|0|0|0|0|

## Fatal Check: evaluation_doc != offer_*

- Total evaluation_doc samples: 3
- Violations (classified as offer): 0
- Non-offer recall: 1.0000
- **PASS**

## Framework Detection

- Accuracy: 0.8649
- Total assessable: 74
- Distribution: {'sci': 52, 'mixed': 10, 'unknown': 10, 'world_bank': 2, 'bad': 1}