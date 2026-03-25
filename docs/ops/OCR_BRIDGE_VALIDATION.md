# OCR bridge — validation d’environnement (BRIDGE_FIX_01)

## Exécution automatique

```bash
python scripts/bridge_validate_env.py
python scripts/bridge_validate_env.py --strict
```

- Sans `--strict` : affiche l’état des clés (code de sortie 0).
- Avec `--strict` : code de sortie 1 si `MISTRAL_API_KEY` ou clé Llama (`LLAMADMS` / `LLAMA_CLOUD_API_KEY`) est absente — à utiliser avant un run `ingest_to_annotation_bridge.py` sur corpus scanné.

Les variables sont lues depuis l’environnement et, si présents, `.env.local` puis `.env` à la racine du dépôt.

## Azure Document Intelligence (optionnel)

Si `AZURE_FORM_RECOGNIZER_ENDPOINT` et `AZURE_FORM_RECOGNIZER_KEY` sont définies, le chemin Mistral peut basculer sur le fallback Azure lorsque le MIME n’est pas reconnu comme PDF/image (`src/extraction/engine.py`, hors périmètre de modification pendant le gel annotation).

## Rapport d’audit (CI / machine sans clés)

Sur un environnement sans `.env` (ex. CI), `bridge_validate_env.py` signale correctement **MISTRAL** et **Llama** en **MISS** : c’est attendu tant que les clés ne sont pas injectées. Les runs OCR réels se font sur une **station de travail** ou un **runner privé** avec secrets.

## Relancer l’ingestion après validation

```bash
python scripts/bridge_validate_env.py --strict
python scripts/ingest_to_annotation_bridge.py --source-root "CHEMIN_VERS_PDFS" --output-root "CHEMIN_SORTIE"
```

Sorties attendues dans le dossier sortie : `ls_tasks.json`, `skipped.json`, `ingest_report.json`, `run_manifest.json`.

## Dénombrement 81 vs 84

La liste tabulaire du freeze compte **84** lignes de documents (`docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md`). Le chiffre « 81 » correspondait à une entrée isolée dans le tableau (ligne #81) ou à un ancien run — la source de vérité alignée est **84** entrées dans `skipped.json` régénéré par `scripts/reconcile_skipped_from_freeze_md.py`.
