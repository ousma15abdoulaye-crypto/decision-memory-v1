# M12 — Export JSONL ground truth (Phase C)

Script : [`scripts/export_ls_to_dms_jsonl.py`](../../scripts/export_ls_to_dms_jsonl.py).

## Prérequis

- `LABEL_STUDIO_URL` — URL publique (ex. `https://label-studio-dms.up.railway.app`)
- `LABEL_STUDIO_API_KEY` — token API LS
- ID projet : `--project-id`

## Commande type

```powershell
$env:LABEL_STUDIO_URL="https://<votre-instance>.up.railway.app"
$env:LABEL_STUDIO_API_KEY="<token>"
python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output data/annotations/m12_batch_001.jsonl
```

## Après export

1. Vérifier lignes JSONL : wrapper **ground_truth**, confiances **0.60 / 0.80 / 1.00** ou null selon RÈGLE-19.
2. Calculer SHA256 du fichier pour traçabilité :

   ```powershell
   Get-FileHash data/annotations/m12_batch_001.jsonl -Algorithm SHA256
   ```

3. Ne **pas** committer de données sensibles : ajuster `.gitignore` si besoin ; archiver hors repo ou espace AO sécurisé.

## Dossier sortie

Les exports M12 sont destinés à [`data/annotations/`](../../data/annotations/README.md).
