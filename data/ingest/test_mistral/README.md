# Corpus PDF — entrée `ingest_to_annotation_bridge`

Placez ici les PDFs à traiter (y compris le lot scanné). Les fichiers `*.pdf` sont **ignorés par Git** (données locales / lourdes).

**Sortie du bridge** (JSON, manifests) : répertoire voisin [`../test_mistral_output/`](../test_mistral_output/).

Exemple :

```powershell
python scripts/ingest_to_annotation_bridge.py `
  --source-root "data/ingest/test_mistral" `
  --output-root "data/ingest/test_mistral_output" `
  --run-id test-mistral-run
```

Référence : [`docs/milestones/HANDOVER_M_INGEST_ANNOTATION_BRIDGE_00.md`](../../../docs/milestones/HANDOVER_M_INGEST_ANNOTATION_BRIDGE_00.md).
