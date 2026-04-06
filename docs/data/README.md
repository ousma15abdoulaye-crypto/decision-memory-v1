# Données locales / backups (non canoniques freeze)

Le fichier `annotations_backup_*.jsonl` était un **backup d’annotations** hors dépôt.

## Si le fichier a été supprimé

1. **OneDrive — Version précédente** sur ce dossier ou le fichier.
2. Re-export depuis Label Studio / pipeline (`scripts/export_ls_to_dms_jsonl.py`, voir `docs/m12/M12_EXPORT.md`).
3. Ne pas committer de données sensibles sans mandat ; respecter `.gitignore`.
