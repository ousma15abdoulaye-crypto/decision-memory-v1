# OCR bridge — artefacts d’ingestion

Les **PDFs sources** se placent dans le dossier voisin [`../test_mistral/`](../test_mistral/) (voir son README).

- **`skipped.json`** — manifeste des PDFs classés `no_text_all_extractors` (chemins placeholder si issu du freeze MD ; à remplacer par un run réel du bridge).
- **`ocr_texts/`** — déposer ici les fichiers `.txt` (ou `.ocr.txt`) produits par un OCR entreprise pour alimenter `scripts/merge_external_ocr_to_ls_tasks.py`.

Voir `docs/ops/OCR_BRIDGE_VALIDATION.md`.
