# Corpus M12 — règles de protection

## Règle 1 — Ne pas supprimer le JSONL sans backup

Avant tout ré-export ou remplacement de `data/annotations/ls_m12_export_latest.jsonl` :

1. Copie horodatée : `data/annotations/corpus_m12_backup_YYYYMMDD_HHMMSS.jsonl`
2. Upload R2 recommandé : préfixe `corpus-backups/m12/` (mêmes variables S3/R2 que Railway)

## Règle 2 — Le JSONL n’est pas dans Git

Les motifs `data/annotations/*.jsonl` et `corpus_m12_backup_*.jsonl` sont dans `.gitignore`.

Les statistiques et la traçabilité sont dans **`data/annotations/corpus_manifest.json`** (fichier explicitement **non** ignoré).

## Règle 3 — Ingestion = opération documentée

Après chaque ingestion vers `dms_embeddings` :

1. `SELECT COUNT(*) FROM dms_embeddings` (par tenant si besoin)
2. Mettre à jour `corpus_manifest.json` (`dms_embeddings_count_local` / `dms_embeddings_count_prod`)
3. Commiter le manifest (pas le JSONL)

## Règle 4 — `AGENT_RAG_ENABLED`

Ne passer à `true` sur Railway (API **et** worker) que si la base **prod** contient des lignes dans `dms_embeddings` pour le tenant concerné (preuve par requête SQL).

Le défaut dans le code reste `False` tant que l’ingestion prod n’est pas prouvée.

## Règle 5 — Lanceur d’export LS

Ne pas supprimer **`scripts/export_ls_dms_m12.cmd`** (règle Cursor `export-ls-m12-canonical.mdc`).

## Historique

- 2026-04-14 : export 116 lignes M12 ; 111 `export_ok` ; ingestion locale `dms_embeddings` (voir `corpus_manifest.json`) ; ingestion prod et activation RAG prod à finaliser depuis un poste avec accès Railway.
