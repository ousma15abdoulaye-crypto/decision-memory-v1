# SCRIPTS DMS v4.1 — INVENTAIRE OFFICIEL
<!-- Ref : DETTE-03 audit CTO senior 2026-03-17 -->
<!-- GO CTO requis avant tout nouveau script officiel -->

## RÈGLES D'UTILISATION
- Scripts officiels : documentés dans ce fichier
- Sondes temporaires : préfixe `_probe_` — jamais committées
- Artefacts de sortie : jamais committés — voir `.gitignore`
- Railway : scripts marqués [RAILWAY] nécessitent DMS_ALLOW_RAILWAY=1

## SCRIPTS OFFICIELS

### Seeds et imports
| Script | Usage | Environnement |
|--------|-------|---------------|
| `seed_mercurials.py` | Import DGMP mercuriales | Local + Railway |
| `seed_zone_context.py` | Initialiser zone_context_registry | Local |
| `seed_market_signals.py` | Compute signaux marché v1.1 | Local + [RAILWAY] |
| `import_imc_entries.py` | Import bulletins INSTAT | Local |
| `etl_vendors_m4.py` | Import fournisseurs Mali (Wave 1 · M4) — voir `README_VENDOR_IMPORT.md` | Local |
| `etl_vendors_wave2.py` | Import fournisseurs Mali (Wave 2 · 663 vendors) — voir `README_VENDOR_IMPORT.md` | Local |

### Migrations et DB
| Script | Usage | Environnement |
|--------|-------|---------------|
| `run_migration.sh` | Wrapper alembic upgrade head | Local |
| `probe_alembic_head.py` | Vérifier head Railway vs local | Local |
| `backfill_sha256.py` | Backfill documents.sha256 | [RAILWAY] avec GO CTO |

### Exports et diagnostics
| Script | Usage | Environnement |
|--------|-------|---------------|
| `export_ls_to_dms_jsonl.py` | Export LS → JSONL M12 (m12-v2 ou `--legacy-mandat-fields`) | Local |
| `export_r2_corpus_to_jsonl.py` | Export R2/S3 → JSONL ; nécessite `-o/--output` (pas de sortie par défaut, pas de lecture de `M12_R2_EXPORT_JSONL`) | Local (S3_* / R2) |
| `m12_corpus_backup.ps1` | Backup horodaté R2 + LS + copie authoritative → `data/annotations/backups/` | Windows |
| `ls_local_autosave.py` | **Anti-perte** — poll LS et sauvegarde toutes les annotations localement (one-shot ou daemon `--loop`). Prévient la perte en cas de déconnexion LS. | Python |
| `validate_annotation.py` | Valide JSONL (schéma DMS + options QA) | Local + CI |
| `derive_pass_0_5_thresholds.py` | Stats texte export LS → seuils Pass 0.5 (voir `docs/contracts/annotation/PASS_0_5_EMPIRICAL_THRESHOLDS.md`) | Local |
| `ingest_to_annotation_bridge.py` | PDF → `ls_tasks.json` (+ `data.structured_preview`) | Local |
| `probe_railway_counts.py` | Vérifier counts tables Railway | Local |

## DOCUMENTATION SPÉCIALISÉE

| Fichier | Contenu |
|---------|---------|
| `README_VENDOR_IMPORT.md` | Guide complet import vendors : schéma, procédure, codes erreur, compatibilité migrations 078/079 |

## SONDES TEMPORAIRES (_probe_*)
Les fichiers `_probe_*.py` sont des diagnostics ad-hoc de session.
Ils ne sont PAS dans git (`.gitignore`).
Ils ne sont PAS maintenus.
Ne pas les utiliser comme référence.

## AJOUTER UN SCRIPT OFFICIEL
1. Créer le script avec docstring complète
2. L'ajouter dans ce README
3. GO CTO obligatoire
4. Commit sur main avec message `scripts: add nom_script`
