# M12 — Export JSONL ground truth (Phase C)

Scripts :

- Export : [`scripts/export_ls_to_dms_jsonl.py`](../../scripts/export_ls_to_dms_jsonl.py)
- Validation : [`scripts/validate_annotation.py`](../../scripts/validate_annotation.py)

Réf. : [ADR-M12-EXPORT-V2](../adr/ADR-M12-EXPORT-V2.md)

## Prérequis (export API)

- `LABEL_STUDIO_URL` — URL publique (ex. `https://label-studio-dms.up.railway.app`)
- `LABEL_STUDIO_API_KEY` — token API LS
- Projet aligné sur [`services/annotation-backend/label_studio_config.xml`](../../services/annotation-backend/label_studio_config.xml) (`extracted_json`, `document_text`)

## Commande type (format m12-v2, défaut)

```powershell
$env:LABEL_STUDIO_URL="https://<votre-instance>.up.railway.app"
$env:LABEL_STUDIO_API_KEY="<token>"
python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output data/annotations/m12_batch_001.jsonl
```

## Export hors API (fichier JSON Label Studio)

```powershell
python scripts/export_ls_to_dms_jsonl.py --from-export-json export_ls.json --output out.jsonl
```

## Ancien format (doc_type / ao_ref)

Si le projet LS utilise encore les champs mandat historiques :

```powershell
python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output legacy.jsonl --legacy-mandat-fields
```

## Validation JSONL

Schéma seul (ligne = JSON DMS complet) :

```powershell
python scripts/validate_annotation.py data/annotations/m12_batch_001.jsonl
```

Lignes « wrapped » (clé `dms_annotation`, ex. copie d’export m12-v2) :

```powershell
python scripts/validate_annotation.py export.jsonl --wrapped --strict-financial
```

## Après export

1. Vérifier `export_ok` et `export_errors` sur chaque ligne (m12-v2).
2. SHA256 du fichier pour traçabilité :

   ```powershell
   Get-FileHash data/annotations/m12_batch_001.jsonl -Algorithm SHA256
   ```

3. Ne **pas** committer de données sensibles : voir [`data/annotations/README.md`](../../data/annotations/README.md).

## Backend ML — `STRICT_PREDICT`

Si `STRICT_PREDICT=1`, le service [`services/annotation-backend/backend.py`](../../services/annotation-backend/backend.py) refuse d’envoyer un JSON de pré-annotation lorsque schéma / finances / evidence échouent. Santé : `GET /health` expose `strict_predict`. Détail : [`services/annotation-backend/ENVIRONMENT.md`](../../services/annotation-backend/ENVIRONMENT.md).

## Attestations Label Studio (export)

Le XML inclut deux choix obligatoires (**evidence_attestation**, **no_invented_numbers**) avant correction du JSON. Pour exiger ces champs lorsque le statut est « VALIDÉ » :

```powershell
python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output out.jsonl --require-ls-attestations
```

## Adoption downstream (Python)

Lire uniquement les lignes **m12-v2** validées :

```python
from pathlib import Path
from src.annotation.m12_export_io import iter_ok_dms_annotations

for dms in iter_ok_dms_annotations(Path("data/annotations/batch.jsonl")):
    taxonomy = dms["couche_1_routing"]["taxonomy_core"]
    ...
```

Détection du format : `export_line_kind(line)` / `dms_annotation_from_line(line)` dans [`src/annotation/m12_export_io.py`](../../src/annotation/m12_export_io.py).

## Ingestion bridge — `structured_preview`

Chaque tâche émise par [`scripts/ingest_to_annotation_bridge.py`](../../scripts/ingest_to_annotation_bridge.py) contient `data.structured_preview` (tables détectées sur les N premières pages, métadonnées pdfplumber). Désactiver : `--structured-preview-pages 0`.
