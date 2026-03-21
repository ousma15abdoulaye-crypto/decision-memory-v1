# data/annotations

Sorties **M12** : exports JSONL Label Studio → format ground truth DMS.

- Ne pas versionner de fichiers contenant des données procurement réelles sans validation sécurité / CTO.
- Nommage suggéré : `m12_batch_<id>.jsonl`.
- Split train/test : voir [`docs/m12/M12_AO_WORKFLOW.md`](../../docs/m12/M12_AO_WORKFLOW.md).
- Gabarit versionné : [`M12_TRAIN_TEST_SPLIT.template.md`](M12_TRAIN_TEST_SPLIT.template.md) → copier en `M12_TRAIN_TEST_SPLIT.md` pour le travail AO (voir workflow).
- CI / golden schéma : [`fixtures/golden_dms_line.jsonl`](fixtures/golden_dms_line.jsonl) (`python scripts/validate_annotation.py …`).
