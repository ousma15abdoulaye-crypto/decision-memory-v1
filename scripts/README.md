# SCRIPTS DMS v4.1 — INVENTAIRE COMPLET
<!-- Audit due diligence 2026-04-08 — 174 scripts Python trackés -->
<!-- GO CTO requis avant tout nouveau script officiel -->

## ÉTAT ACTUEL

| Catégorie | Fichiers | Note |
|-----------|----------|------|
| `_probe_*.py` (temporaires trackés) | 38 | **Anomalie** — devraient être hors git (voir §Nettoyage) |
| `_*.py` (autres temporaires trackés) | 18 | **Anomalie** — même problème |
| Scripts officiels (sans `_`) | 118 | Documentés ci-dessous |
| Total `.py` trackés | 174 | |

## RÈGLES D'UTILISATION
- Scripts officiels : documentés dans ce fichier, nommage `verbe_objet.py`
- Sondes temporaires : préfixe `_probe_` — ne **devraient pas** être committées
- Artefacts de sortie : jamais committés — voir `.gitignore`
- Railway : scripts marqués [RAILWAY] nécessitent `DMS_ALLOW_RAILWAY=1`

---

## SCRIPTS OFFICIELS PAR CATÉGORIE

### Seeds & imports de données

| Script | Usage | Env |
|--------|-------|-----|
| `seed_dms_app_user.py` | Crée un utilisateur `users` + `user_tenants` (même logique que `/auth/register`) — exécuter en **Python** local, pas dans une image Bun-only (`python3: not found`) ; `with_railway_env.py` pour prod | Env: `DMS_SEED_USER_EMAIL`, `DMS_SEED_USER_USERNAME`, `DMS_SEED_USER_PASSWORD` |
| `seed_classification_backfill.py` | Backfill classification taxonomy | Local |
| `seed_decision_history_init.py` | Init decision_history | Local |
| `seed_geo_corridors_mali.py` | Init corridors géo Mali | Local |
| `seed_instat_seasonal_patterns.py` | Import saisonnalité INSTAT | Local |
| `seed_market_surveys_init.py` | Init market_surveys | Local |
| `seed_menaka_corridor.py` | Corridor Ménaka | Local |
| `seed_mercurial_seasonal_patterns.py` | Saisonnalité mercuriales | Local |
| `seed_seasonal_patterns_complete.py` | Saisonnalité complète | Local |
| `seed_seasonal_patterns_mali.py` | Saisonnalité Mali | Local |
| `seed_taxonomy_v2.py` | Taxonomie V2 | Local |
| `seed_tracked_from_mercurials.py` | Tracked items depuis mercuriales | Local |
| `seed_tracked_market_scope.py` | Market scope tracking | Local |
| `seed_tracked_zones_railway.py` | Zones tracked Railway | [RAILWAY] |
| `seed_zone_context_mali.py` | Zone context Mali | Local |
| `seed_zone_context_missing14.py` | Compléter 14 zones manquantes | Local |
| `etl_vendors_m4.py` | Import fournisseurs Mali Wave 1 (M4) | Local |
| `etl_vendors_wave2.py` | Import fournisseurs Mali Wave 2 (663 vendors) | Local |
| `import_imc.py` | Import bulletins INSTAT/IMC | Local |
| `import_market_surveys.py` | Import market surveys | Local |
| `import_mercuriale.py` | Import mercuriales DGMP | Local + [RAILWAY] |
| `enrich_survey_vendor_ids.py` | Enrichir survey → vendor_id | Local |
| `backfill_corpus_from_label_studio.py` | Backfill corpus depuis LS | Local |

### Exports & extraction

| Script | Usage | Env |
|--------|-------|-----|
| `export_annotations_jsonl.py` | Export annotations → JSONL | Local |
| `export_labelstudio_to_registry.py` | Export LS → registry | Local |
| `export_ls_to_dms_jsonl.py` | Export LS → JSONL M12 (m12-v2) | Local |
| `export_r2_corpus_to_jsonl.py` | Export R2/S3 → JSONL | Local (S3/R2) |
| `extract_for_ls.py` | Extraction pour Label Studio | Local |
| `ls_local_autosave.py` | Anti-perte : poll LS + sauvegarde locale | Local |
| `ls_export_filters.py` | Filtres export LS | Local |

### Annotation & M12

| Script | Usage | Env |
|--------|-------|-----|
| `ingest_to_annotation_bridge.py` | PDF → `ls_tasks.json` (+ structured_preview) | Local |
| `consolidate_m12_corpus.py` | Consolider corpus M12 | Local |
| `inventory_m12_corpus_jsonl.py` | Inventaire corpus M12 (JSONL) | Local |
| `inventory_m12_jsonl.py` | Inventaire JSONL M12 | Local |
| `m12_benchmark_against_corpus.py` | Benchmark M12 vs corpus | Local |
| `m12_calibrate_classifier_metrics.py` | Calibrer métriques classifieur M12 | Local |
| `m12_r2_delta_vs_local.py` | Delta R2 vs local (M12) | Local |
| `merge_external_ocr_to_ls_tasks.py` | Merge OCR externe → tasks LS | Local |
| `repair_m12_jsonl_golden_backfill.py` | Réparer golden JSONL M12 | Local |
| `verify_m12_jsonl_corpus.py` | Vérifier corpus JSONL M12 | Local |
| `dry_run_m12_export_audit.py` | Dry-run audit export M12 | Local |
| `smoke_m12_annotation.py` | Smoke test annotation M12 | Local |
| `derive_pass_0_5_thresholds.py` | Stats texte → seuils Pass 0.5 | Local |
| `classify_taxonomy_v2.py` | Classification taxonomie V2 | Local |

### Validation & audit

| Script | Usage | Env |
|--------|-------|-----|
| `validate_annotation.py` | Valide JSONL (schéma DMS + QA) | Local + CI |
| `validate_dict_items.py` | Valide dict items | Local |
| `validate_mrd_state.py` | Valide état MRD | Local |
| `validate_taxo_batch.py` | Valide taxonomie batch | Local |
| `validate_v420_pilote_gates.py` | Valide gates pilote V4.2.0 | Local |
| `audit_criteria_fk_orphans.py` | Audit FK orphelins critères | Local |
| `audit_fastapi_auth_coverage.py` | Audit couverture auth FastAPI | Local + CI |
| `eval_against_golden.py` | Éval contre golden dataset | Local |
| `run_ragas_eval.py` | Évaluation RAGAS | Local |
| `measure_m15_metrics.py` | Métriques M15 | Local |
| `m15_export_gate.py` | Gate export M15 | Local |

### Base de données & migrations

| Script | Usage | Env |
|--------|-------|-----|
| `setup_db.py` | Setup DB initial | Local |
| `setup_db_with_password.py` | Setup DB avec password | Local |
| `create_db_simple.py` | Création DB simple | Local |
| `check_db.py` | Vérifier connexion DB | Local |
| `dms_pg_connect.py` | Connexion Postgres DMS | Local |
| `run_pg_sql.py` | Exécuter SQL Postgres | Local |
| `apply_railway_migrations_safe.py` | Migrations Railway safe | [RAILWAY] |
| `diagnose_railway_migrations.py` | Diagnostiquer migrations Railway | [RAILWAY] |
| `fix_alembic_version_017_to_018.py` | Fix version alembic 017→018 | Local |
| `create_ivfflat_index.py` | Index IVFFlat pgvector | Local |
| `add_signal_engine_indexes.py` | Index signal engine | Local |
| `apply_fk_prod.py` | Appliquer FK en prod | [RAILWAY] |
| `migrate_cases_to_workspaces.py` | Migration cases → workspaces | Local |
| `manage_event_index_partitions.py` | Gestion partitions event_index | Local |
| `hardening_product_sql_checks.py` | Durcissement SQL produit | Local |

### Probes officielles (sans underscore)

| Script | Usage | Env |
|--------|-------|-----|
| `probe_alembic_head.py` | Vérifier head Alembic | Local |
| `probe_h0_table_health.py` | Santé tables H0 | Local |
| `probe_imc_format.py` | Format IMC | Local |
| `probe_m10b.py` | Probe M10b | Local |
| `probe_m11.py` | Probe M11 | Local |
| `probe_m13_files.py` | Fichiers M13 | Local |
| `probe_m13_h0_gates.py` | Gates H0 M13 | Local |
| `probe_m7_3_nerve_center.py` | Nerve center M7.3 | Local |
| `probe_m7_3b.py` | Probe M7.3b | Local |
| `probe_m7_pre.py` | Pre-probe M7 | Local |
| `probe_m7_taxo_reset.py` | Reset taxonomie M7 | Local |
| `probe_m74.py` | Probe M7.4 | Local |
| `probe_mercurials_coverage.py` | Couverture mercuriales | Local |
| `probe_railway_counts.py` | Counts tables Railway | Local |
| `probe_railway_full.py` | Full probe Railway | Local |
| `probe_users_id_type.py` | Type ID utilisateurs | Local |

### Pipeline & scoring

| Script | Usage | Env |
|--------|-------|-----|
| `pipeline_status.py` | Statut pipeline | Local |
| `compute_market_signals.py` | Calcul signaux marché | Local |
| `compute_market_signals_m11.py` | Signaux marché M11 | Local |
| `batch_signal_from_map.py` | Signaux batch depuis map | Local |
| `trigger_extraction_queue.py` | Déclencher queue extraction | Local |
| `test_extraction_e2e.py` | Test E2E extraction | Local |

### MRD (Market Reference Data)

| Script | Usage | Env |
|--------|-------|-----|
| `mrd4_rebuild_canonique.py` | Rebuild canonique MRD4 | Local |
| `mrd5_backfill_item_code.py` | Backfill item_code MRD5 | Local |
| `mrd6_apply_taxonomy.py` | Appliquer taxonomie MRD6 | Local |
| `mrd6_detect_collisions.py` | Détecter collisions MRD6 | Local |
| `triage_collisions_m8.py` | Triage collisions M8 | Local |
| `resolve_collision_tier1.py` | Résoudre collisions tier 1 | Local |
| `semantic_guard_m8.py` | Guard sémantique M8 | Local |
| `semantic_guard_m9.py` | Guard sémantique M9 | Local |
| `map_mercurials_to_dict.py` | Mapping mercuriales → dict | Local |
| `build_dictionary.py` | Build dictionnaire | Local |
| `create_mercurials_mapping.py` | Mapping mercuriales | Local |

### Mercuriales & dictionnaire

| Script | Usage | Env |
|--------|-------|-----|
| `m7_rebuild_t0_purge.py` | Rebuild T0 purge M7 | Local |
| `fix_backfill_taxonomy.py` | Fix backfill taxonomie | Local |
| `fix_template.py` | Fix template | Local |

### Blocs & pilotes

| Script | Usage | Env |
|--------|-------|-----|
| `bloc3_smoke_railway.py` | Smoke Bloc 3 Railway | [RAILWAY] |
| `bloc4_apply_workspace_trigger_v2.py` | Trigger workspace Bloc 4 | Local |
| `bloc4_committee_mandate_run.py` | Committee mandate Bloc 4 | Local |
| `bloc4_seal_validation_postfix.py` | Seal validation Bloc 4 | Local |
| `bloc6_pilot_sci_mali_run.py` | Pilote SCI Mali Bloc 6 | Local |

### Ops & infrastructure

| Script | Usage | Env |
|--------|-------|-----|
| `bridge_validate_env.py` | Valider env bridge | Local |
| `preflight_cto_railway_readonly.py` | Preflight CTO Railway readonly | [RAILWAY] |
| `with_railway_env.py` | Wrapper env Railway | Local |
| `smoke_arq_worker.py` | Smoke test ARQ worker | Local |
| `smoke_postgres.py` | Smoke test Postgres | Local |
| `sync_annotations_local_to_railway.py` | Sync annotations local→Railway | [RAILWAY] |
| `sync_dict_local_to_railway.py` | Sync dict local→Railway | [RAILWAY] |
| `reconcile_skipped_from_freeze_md.py` | Réconcilier skipped depuis freeze | Local |
| `regenerate_freeze_checksums.sh` | Regénérer checksums freeze (Linux) | CI |

---

## SONDES TEMPORAIRES TRACKÉES (56 fichiers — ANOMALIE)

**38 fichiers `_probe_*.py`** et **18 autres `_*.py`** sont trackés dans git.
Selon la politique DMS, ces fichiers ne devraient **pas** être versionnés.

### Nettoyage recommandé (GO CTO requis)

```bash
git rm --cached scripts/_probe_*.py scripts/_*.py
echo "scripts/_probe_*.py" >> .gitignore
echo "scripts/_*.py" >> .gitignore
```

Fichiers concernés (non exhaustif) :
- `_probe_m1.py` .. `_probe_m9_railway_chain.py` (probes milestones)
- `_acte6_option_a.py`, `_action_m10a_ce_soir.py` (actions ponctuelles)
- `_audit_merc_imc.py`, `_audit_schemas_cto.py` (audits ad-hoc)
- `_cleanup_prod_smoke_users.py` (cleanup prod)
- `_generate_golden_dataset.py` (dataset generation)
- `_smoke_m2.py`, `_test_admin_login.py` (tests ad-hoc)

## DOCUMENTATION SPÉCIALISÉE

| Fichier | Contenu |
|---------|---------|
| `README_VENDOR_IMPORT.md` | Guide complet import vendors : schéma, procédure, codes erreur |

## AJOUTER UN SCRIPT OFFICIEL
1. Créer le script avec docstring complète
2. Nommer en `verbe_objet.py` (snake_case)
3. L'ajouter dans la catégorie appropriée de ce README
4. GO CTO obligatoire
5. Commit avec message `scripts: add nom_script`
