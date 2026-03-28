# data/annotations

Sorties **M12** : format ground truth DMS (JSONL).

- Ne pas versionner de fichiers contenant des données procurement réelles sans validation sécurité / CTO.
- **Backups** : `scripts/m12_corpus_backup.ps1` → `data/annotations/backups/<horodatage>/` (gitignoré). Voir [`docs/m12/M12_PIPELINE_INDUSTRIAL.md`](../../docs/m12/M12_PIPELINE_INDUSTRIAL.md).
- **Vérité corpus (R2 exportée)** : `m12_corpus_authoritative.jsonl` — à générer explicitement via `scripts/export_r2_corpus_to_jsonl.py` (par exemple avec `-o data/annotations/m12_corpus_authoritative.jsonl`, ou en configurant `M12_R2_EXPORT_JSONL` si supporté).
- Export LS séparé (optionnel, comparaison / delta) : `m12_corpus_from_ls.jsonl` — ne remplace pas `m12_corpus_authoritative.jsonl`.
- Chaîne LS + delta R2 + consolidation : `scripts/run_m12_corpus_resync.ps1` (voir en-tête du script).
- Delta / fusion : [`docs/m12/M12_EXPORT.md`](../../docs/m12/M12_EXPORT.md).
- Split train/test : [`docs/m12/M12_AO_WORKFLOW.md`](../../docs/m12/M12_AO_WORKFLOW.md).
- Gabarit : [`M12_TRAIN_TEST_SPLIT.template.md`](M12_TRAIN_TEST_SPLIT.template.md).
- CI / golden schéma : [`fixtures/golden_dms_line.jsonl`](fixtures/golden_dms_line.jsonl) (`python scripts/validate_annotation.py …`).
