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

### Migrations et DB
| Script | Usage | Environnement |
|--------|-------|---------------|
| `run_migration.sh` | Wrapper alembic upgrade head | Local |
| `probe_alembic_head.py` | Vérifier head Railway vs local | Local |
| `backfill_sha256.py` | Backfill documents.sha256 | [RAILWAY] avec GO CTO |

### Exports et diagnostics
| Script | Usage | Environnement |
|--------|-------|---------------|
| `export_annotation_jsonl.py` | Export JSONL entraînement M12 | Local |
| `probe_railway_counts.py` | Vérifier counts tables Railway | Local |

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
