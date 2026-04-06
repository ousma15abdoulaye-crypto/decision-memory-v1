# Annotations — exports locaux (M12 / LS)

Ce répertoire sert aux **exports JSONL** et inventaires générés hors CI (souvent gitignorés).

## Fichiers supprimés par erreur (récupération)

Si `inventory_m12_latest.md`, `ls_m12_export_latest.jsonl` ou d’autres exports ont disparu :

1. **OneDrive** : clic droit sur le dossier ou le fichier → **Version précédente** / **Historique des versions** → restaurer la copie datée avant le nettoyage.
2. **Régénérer** :
   - Export Label Studio → `scripts/export_ls_to_dms_jsonl.py` (voir `docs/m12/M12_EXPORT.md`).
   - Inventaire : `python scripts/inventory_m12_corpus_jsonl.py <export.jsonl>` (ou alias `scripts/inventory_m12_jsonl.py`).
   - Audit sec : `python scripts/dry_run_m12_export_audit.py <export.jsonl>`.

Ne pas committer de secrets ni de corpus complet sans mandat (voir `.gitignore`).
