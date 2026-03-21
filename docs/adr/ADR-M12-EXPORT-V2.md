# ADR — Export M12 v2 (Label Studio `extracted_json`)

## Statut

Accepté — 2026-03-21

## Contexte

Le XML commité [`services/annotation-backend/label_studio_config.xml`](../../services/annotation-backend/label_studio_config.xml) utilise `extracted_json` + méta (`routing_ok`, `financial_ok`, `annotation_status`), alors que l’ancien script d’export lisait `doc_type` / `ao_ref` / `zones` (projet LS différent).

## Décision

1. **Format `export_schema_version: m12-v2`** : chaque ligne JSONL contient `dms_annotation` (JSON validé `DMSAnnotation` v3.0.1d), `ls_meta`, `export_ok`, `export_errors`, `content_hash`, et champs de QA (`financial_warnings`, `evidence_violations` si applicable).
2. **Mode legacy** : `--legacy-mandat-fields` conserve l’export `m12-legacy` (ancien `ground_truth` doc_type / ao_ref).
3. **Contrôle `annotated_validated`** : par défaut, si le correcteur marque « validé » mais que le JSON est invalide, que la réconciliation financière échoue ou que les `evidence` ne sont pas retrouvables dans le texte tâche → `export_ok: false` (désactivable avec `--no-enforce-validated-qa`).
4. **`STRICT_PREDICT`** sur le backend ML : si `STRICT_PREDICT=1` (true/on), `/predict` ne renvoie pas de pré-annotation JSON lorsque la validation schéma, la QA financière ou la QA evidence échoue (résultat vide traçable avec `error_reason`).

## Conséquences

- Les consommateurs M12 doivent lire `dms_annotation` (ou migrer depuis legacy).
- CI exécute `scripts/validate_annotation.py` sur [`data/annotations/fixtures/golden_dms_line.jsonl`](../../data/annotations/fixtures/golden_dms_line.jsonl).
- UI Label Studio : attestations **evidence_attestation** / **no_invented_numbers** (voir `label_studio_config.xml`). Export optionnel `--require-ls-attestations` si le statut est `annotated_validated`.
- Code aval : [`src/annotation/m12_export_io.py`](../../src/annotation/m12_export_io.py) (`iter_ok_dms_annotations`, etc.).
- Ingestion : `data.structured_preview` dans les tâches bridge (pdfplumber, premières pages).
