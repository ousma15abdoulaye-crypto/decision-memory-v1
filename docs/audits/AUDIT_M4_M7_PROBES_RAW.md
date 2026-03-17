# AUDIT M4→M7 — PROBES RAW

**Date :** 2026-03-08  
**Nature :** Sorties brutes capturées — lecture seule — aucune interprétation préalable  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF

---

## PROBE 1 — git status (branche active)

```
On branch feat/m7-rebuild-dict-from-terrain
Changes not staged for commit:
  modified:   docs/milestones/HANDOVER_AGENT.md
  modified:   scripts/build_dictionary.py
  modified:   scripts/etl_vendors_wave2.py
  modified:   scripts/seed_taxonomy_v2.py
  modified:   tests/dict/test_m7_3b_legacy_block.py

Untracked files (extrait — 50+ fichiers) :
  alembic_m74.txt
  alembic_m74a.txt
  backfill_dry.txt
  backfill_reel.txt
  build_err.txt
  build_out.txt
  docs/audits/AUDIT_M4_M7_BRANCHES_MALADES.md
  docs/audits/AUDIT_M4_M7_DETTES_CHIRURGICALES.md
  docs/audits/AUDIT_M4_M7_INVARIANTS.md
  docs/audits/AUDIT_M4_M7_PROBES_RAW.md
  docs/audits/AUDIT_M4_M7_RAPPORT_COMPLET_EVALUATION.md
  docs/audits/AUDIT_M4_M7_TRIBUNAL.md
  docs/audits/AUDIT_M4_M7_VERDICT_RECONSTRUCTION.md
  docs/mandates/M7_3_PATH_EXEC_AND_HASH_ALIGNMENT.md
  docs/mandates/M7_4_INGESTION_PROD_TEMPS0_REPORT.md
  docs/mandates/M7_4_T1B_AUDIT_IMPORT_SCRIPTS.md
  docs/milestones/HANDOVER_M74_PHASE_A.md
  docs/milestones/RAPPORT_DEFAILLANCE_M74_PHASE_A.md
  docs/reports/ (répertoire entier)
  dry_run_dict.txt
  dry_run_dict_v2.txt
  gap_analysis.txt
  import_m5_railway.txt
  phase_a_dryrun50.txt
  phase_a_full.txt
  phase_a_sample50.txt
  probe_post.txt
  pytest_m74a.txt
  restore_log.txt
  run_dict_final.txt
  run_dict_reel.txt
  run_dict_v2.txt
  run_dict_v3.txt
  run_vendors_final.txt
  run_vendors_reel.txt
  scripts/_dryrun_wave2_output.txt
  scripts/_err_wave2.txt
  scripts/_out_wave2.txt
  scripts/_preuve_1_2.py
  scripts/_probe_audit_log_schema.py
  scripts/_probe_cov_uid.py
  scripts/_probe_m73_final.py
  scripts/_probe_m73_todo.py
  scripts/_probe_phase_a.py
  scripts/_probe_seed_53.py
  scripts/_probe_step1_db_safe.py
  scripts/_probe_step2_vendors_prod.py
  scripts/_restore_probe.py
  scripts/_verify_m74a_cols.py
  scripts/_wave2_dryrun.txt
  scripts/classify_taxonomy_v2.py
  scripts/fix_backfill_taxonomy.py
  scripts/m7_rebuild_t0_purge.py
  scripts/probe_m74.py
  scripts/probe_m7_3_nerve_center.py
  scripts/probe_users_id_type.py
  scripts/validate_taxo_batch.py
  seed_taxo.txt
  tests/dict/test_m7_4_dict_vivant.py
```

---

## PROBE 2 — alembic heads

```
m7_4a_item_identity_doctrine (head)
```

**Résultat : 1 ligne exactement. Conforme au freeze (invariant 1 head).**

---

## PROBE 3 — alembic current (DB locale)

```
m7_4_dict_vivant
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**Résultat : DB locale sur m7_4_dict_vivant. NON à head. Écart = 1 migration.**

---

## PROBE 4 — git branch -a (extrait branches M4→M7)

```
  feat/m4-patch
  feat/m4-patch-a
  feat/m4-patch-b
  feat/m4-vendor-importer
  feat/m5-cleanup-a
  feat/m5-fix-pre-ingest
  feat/m5-geo-fix
  feat/m5-mercuriale-2026
  feat/m5-mercuriale-clean
  feat/m5-mercuriale-ingest
  feat/m5-patch-imc-ingest
  feat/m5-pre-hardening
  feat/m6-dictionary-build
  feat/m7-2-taxonomy-reset
  feat/m7-3-dict-nerve-center
  feat/m7-3b-deprecate-legacy
  feat/m7-dictionary-enrichment
* feat/m7-rebuild-dict-from-terrain
  freeze/v4.1.0
```

---

## PROBE 5 — git log --oneline --decorate --graph --all -n 150 (extrait M4→M7)

```
* 7219636 (HEAD -> feat/m7-rebuild-dict-from-terrain, main) chore(m7): restore m7_4/m7_4a migrations · alignement Railway prod
* 64d7e12 (origin/main) Merge pull request #170 from feat/m7-3b-deprecate-legacy
* 8079f3b (tag: v4.2.0-m7-3b-done, origin/feat/m7-3b-deprecate-legacy) docs: handover fin mission M7.3b + chat context
* a425332 fix(m7.3b): PR #170 - D1-D5 corrections
* 4f46955 (tag: v4.2.0-m7-3b-legacy-deprecated) feat(m7.3b): deprecate legacy family_id - triggers, migration, tests
* 12de276 docs(adr): ADR-0016 détour M7.2/M7.3 et retour M7 réel
* 7a78a9e (tag: v4.1.0-m7.3-done) docs(M7.3): note fin mission + handover complet
* 6b4ff68 Merge pull request #169 from feat/m7-3-dict-nerve-center
* 52b741c fix(PR#169): D8-D4 corrections CTO revue
* 1dd9efb feat(m7.3): dict nerve center - aligned hash canon B2-A
* eb09dbf (feat/m7-2-taxonomy-reset) feat(m7.2): taxonomy L1/L2/L3 enterprise grade · 15 domaines · 57 familles · 155 sous-familles
* 32b2ef0 (feat/m7-dictionary-enrichment) feat(m7): dictionary enrichment - LLM classification - dict_version 1.1.0
* 316854f (tag: v4.1.0-m6-dictionary) feat(m6): dictionary procurement AOF - v4.1.0-m6-dictionary
* a326329 (feat/m6-dictionary-build) feat(m6): dictionary build - 1488 items - 1596 aliases
* 2a8090e Merge pull request #168 from feat/m5-patch-imc-ingest
* be081f6 (tag: v4.1.0-m5-mercuriale) feat(m5): import mercuriales Mali 2023+2024 - 12285 lignes - 100% geo
* fcfda3a (tags: v4.1.0-m4-done, v4.1.0-m4-patch-done, etc.) Merge pull request #150 from feat/m4-patch-b
```

---

## PROBE 6 — Migrations alembic/versions/ (liste triée)

```
002_add_couche_a.py
003_add_procurement_extensions.py
004_users_rbac.py
005_add_couche_b.py
006_criteria_types.py
007_add_scoring_tables.py
008_merge_heads.py
009_add_supplier_scoring_tables.py
009_supplier_scores_eliminations.py
010_enforce_append_only_audit.py
011_add_missing_schema.py
012_m_extraction_engine.py
013_add_m_extraction_engine_documents_columns.py
014_ensure_extraction_tables.py
015_m_extraction_corrections.py
016_fix_015_views_triggers.py
018_fix_alembic_heads.py
019_consolidate_extraction_corrections.py
020_m_criteria_typing.py
021_m_normalisation_items_tables.py
022_seed_procurement_dict_v1_sahel.py
023_m_criteria_fk.py
024_mercuriale_raw_queue.py
025_alter_scoring_configs.py
026_score_runs_append_only.py
027_add_cases_currency.py
028_create_committee_tables.py
029_create_decision_snapshots.py
030_committee_lock_trigger.py
031_committee_terminal_status.py
032_create_pipeline_runs.py
033_create_pipeline_step_runs.py
034_add_force_recompute_pipeline_runs.py
035_create_analysis_summaries.py
036_db_hardening.py
037_security_baseline.py
038_audit_hash_chain.py
039_hardening_created_at_timestamptz.py    ← M2B (freeze annonce 039_seed_vendors_mali = ABSENT)
040_geo_master_mali.py                     ← M3
040_mercuriale_ingest.py                   ← M5 (double 040 : ANOMALIE)
041_vendor_identities.py                   ← M4 réel (freeze annonce 041_procurement_dictionary = ABSENT)
042_vendor_fixes.py                        ← M4
043_vendor_activity_badge.py               ← M4
784a8b003d2d_merge_heads_020_and_022.py
m4_patch_a_fix.py
m4_patch_a_vendor_structure_v410.py
m5_cleanup_a_committee_event_type_check.py
m5_fix_market_signals_vendor_type.py
m5_geo_fix_master.py
m5_geo_patch_koutiala.py
m5_patch_imc_ingest_v410.py
m5_pre_vendors_consolidation.py
m6_dictionary_build.py
m7_2_taxonomy_reset.py
m7_3_dict_nerve_center.py
m7_3b_deprecate_legacy_families.py
m7_4_dict_vivant.py
m7_4a_item_identity_doctrine.py           ← HEAD repo — NON appliqué local
```

**ANOMALIE PROUVÉE :** Double préfixe 040 — `040_geo_master_mali.py` (M3) ET `040_mercuriale_ingest.py` (M5). Les fichiers Alembic ne peuvent pas coexister avec le même préfixe numérique dans une chaîne linéaire sans ambiguïté. La chaîne de down_revision résout l'ordre réel, mais le nommage est non canonique.

---

## PROBE 7 — Counts DB locale (probe_post.txt — pré-m7_4 migration)

```
PROBE P0→P9 — M7.4 DICT VIVANT · PRÉ-MIGRATION
======================================================================

--- P2_CLASSIFICATION ---
  Total actifs     : 1489
  Avec domain_id   : 0
  Sans domain_id   : 1489   ← à classifier (TOUS sans taxo)
  Seed protégés    : 51
  Labels courts    : 4      ← exclus LLM

--- P3_TAXO_EN_BASE ---
  taxo_l1_domains                  15  OK
  taxo_l2_families                 47  OK
  taxo_l3_subfamilies              23  ⚠ 23 < 50 (attendu ~155 selon seed)

--- P4_PROPOSALS ---
  (vide)

--- P0_TRIGGERS_EXISTANTS ---
  trg_block_legacy_family_insert   BEFORE INSERT
  trg_block_legacy_family_update   BEFORE UPDATE
  trg_compute_quality_score        BEFORE INSERT / UPDATE
  trg_dict_compute_hash            BEFORE UPDATE
  trg_dict_write_audit             AFTER UPDATE

--- STOP SIGNALS ---
  STOP-DB: taxo_l3_subfamilies trop vide (23 < 50)
  STOP: MISTRAL_API_KEY manquante
```

---

## PROBE 8 — Counts post-build_dictionary (run_dict_final.txt — 2026-03-07)

```
BUILD DICTIONARY M6 — IMPORT RÉEL — min_freq=2
======================================================
Schema collision_log : 16 colonnes
Schema proposals     : 8 colonnes
Items seed existants : 52
1573 libellés bruts extraits

ERREUR connexion DB : 'Stylo Bic Bleu Cristal' — server closed the connection unexpectedly
```

**Résultat :** 1573 libellés extraits. Coupure connexion en cours de traitement. Counts finaux non prouvés pour cette exécution.

---

## PROBE 9 — Counts rapport complet (synthèse cross-probes)

| Table | Count prouvé | Source |
|-------|-------------|--------|
| `couche_b.procurement_dict_items` total actifs | 1489 (pré-m7.4) / ~1490 (post) | probe_post.txt |
| `couche_b.procurement_dict_items` human_validated | 51 | probe_post.txt |
| `couche_b.procurement_dict_items` avec domain_id | 0 (pré-classify) | probe_post.txt |
| `couche_b.procurement_dict_aliases` | 1596 | rapport complet |
| `couche_b.dict_proposals` pending | 1439 | rapport complet |
| `couche_b.dict_collision_log` | 0 | rapport complet |
| `couche_b.taxo_l1_domains` | 15 | probe_post.txt |
| `couche_b.taxo_l2_families` | 47 (≠ 57 annoncés) | probe_post.txt |
| `couche_b.taxo_l3_subfamilies` | 23 (≠ 155 annoncés) | probe_post.txt ⚠ |
| `couche_b.taxo_proposals_v2` | 0 (pré) / 1070 (post-Phase A partielle) | probe_post.txt / HANDOVER_M74 |
| taxo_proposals_v2 flagged (Phase A) | 834 / 1070 = 77.9% | HANDOVER_M74_PHASE_A.md |

**ANOMALIE CRITIQUE :** seed_taxonomy_v2.py annonce 155 sous-familles mais DB contient 23 au moment de la probe. Soit seed non exécuté intégralement, soit exécution partielle, soit seed_taxonomy_v2.py a été modifié (fichier dans la liste des modifiés non commités).

---

## PROBE 10 — Gap analysis L3 (gap_analysis.txt — 2026-03-08)

```
GAP ANALYSIS L3 - M7.4a
Codes L3 valides en base   : 23
Items à classifier         : 1485
Codes L3 inventés (LLM)    : 0
Couverture L3              : 100.0%
OK : couverture 100.0% >= 70.0%
```

**Lecture critique :** "Couverture 100.0%" signifie que tous les items qui ont reçu une classification L3 utilisent un code L3 existant — non que 100% des 1485 items sont classifiés. La majority reste sans domain_id. Ce metric est trompeur si interprété hors contexte.

---

## PROBE 11 — Phase A Classification LLM (HANDOVER_M74_PHASE_A.md)

```
Proposals total : 1070
pending         : 236
flagged         : 834    ← 77.9%
DIVERS_NON_CLASSE résiduel : 833 (77.9%)

STOP-V3 : flagged_pct >= 35% → DÉPASSÉ (77.9%)
STOP-V4 : residuel_pct >= 25% → DÉPASSÉ (77.9%)

Cause : LLM invente codes L3 (ex. 'cafe', 'lait', 'farine', 'bois', 'fer', 'bazin')
        qui n'existent pas dans la taxonomie DB (23 codes L3 seulement).
        Items non mappables → DIVERS_NON_CLASSE → flagged.
```

---

## PROBE 12 — Tags Git M4→M7

```
v4.1.0-m4-done
v4.1.0-m4-patch-done
v4.1.0-m4-patch-a
v4.1.0-m4-patch-a-fix
v4.1.0-m4-patch-b-done
v4.1.0-m5-pre-hardening
v4.1.0-m5-fix
v4.1.0-m5-cleanup-a
v4.1.0-m5-mercuriale        (tag: v4.1.0-m5-mercuriale)
v4.1.0-m5-patch-imc-ingest-done
v4.1.0-m6-dictionary        (tag: v4.1.0-m6-dictionary) ← dernier point sûr
v4.1.0-m7.3-done
v4.2.0-m7-3b-done
v4.2.0-m7-3b-legacy-deprecated
```

**Observation :** Les tags M7.4 / M7.4a sont absents. La migration m7_4_dict_vivant est appliquée localement mais aucun tag de clôture n'existe. m7_4a n'est pas encore appliquée. Aucun milestone M7.4 / M7.4a n'est prouvé done.

---

## PROBE 13 — Migrations down_revision (chaîne prouvée par lecture fichiers)

| Migration | revision | down_revision |
|-----------|----------|---------------|
| m6_dictionary_build | m6_dictionary_build | m5_patch_imc_ingest_v410 |
| m7_2_taxonomy_reset | m7_2_taxonomy_reset | m6_dictionary_build |
| m7_3_dict_nerve_center | m7_3_dict_nerve_center | m7_2_taxonomy_reset |
| m7_3b_deprecate_legacy_families | m7_3b_deprecate_legacy_families | m7_3_dict_nerve_center |
| m7_4_dict_vivant | m7_4_dict_vivant | m7_3b_deprecate_legacy_families |
| m7_4a_item_identity_doctrine | m7_4a_item_identity_doctrine | m7_4_dict_vivant |

Chaîne linéaire vérifiée. Aucune bifurcation M6→M7.

---

## PROBE 14 — Vérification delete rules FK (lecture migrations)

| FK | Table source | Table cible | Delete rule prouvée |
|----|-------------|-------------|---------------------|
| domain_id | procurement_dict_items | taxo_l1_domains | REFERENCES ... (pas ON DELETE spécifié) = **NO ACTION** |
| family_l2_id | procurement_dict_items | taxo_l2_families | REFERENCES ... = **NO ACTION** |
| subfamily_id | procurement_dict_items | taxo_l3_subfamilies | REFERENCES ... = **NO ACTION** |
| item_id (dict_proposals) | dict_proposals | procurement_dict_items | **ON DELETE RESTRICT** |
| item_id (dict_price_references) | dict_price_references | procurement_dict_items | **ON DELETE RESTRICT** |
| item_id (taxo_proposals_v2) | taxo_proposals_v2 | procurement_dict_items | **ON DELETE RESTRICT** |
| domain_id (taxo_l2_families) | taxo_l2_families | taxo_l1_domains | **ON DELETE RESTRICT** |
| family_l2_id (taxo_l3_subfamilies) | taxo_l3_subfamilies | taxo_l2_families | **ON DELETE RESTRICT** |

**Conclusion FK :** Pas de CASCADE taxonomie→dictionnaire. Le registre n'est pas détruit par une opération sur la taxonomie. CONFORME.

---

## PROBE 15 — Triggers sur procurement_dict_items (probe_post.txt)

```
trg_block_legacy_family_insert   BEFORE INSERT  — bloque family_id sur INSERT (M7.3b)
trg_block_legacy_family_update   BEFORE UPDATE  — bloque family_id sur UPDATE (M7.3b)
trg_compute_quality_score        BEFORE INSERT OR UPDATE — calcul quality_score O(1) (M7.4)
trg_dict_compute_hash            BEFORE UPDATE  — calcul last_hash SHA256 (M7.3)
trg_dict_write_audit             AFTER UPDATE   — INSERT audit_log entity='DICT_ITEM' (M7.3)
```

**Observation :** 5 triggers actifs sur procurement_dict_items. Trigger quality_score dépend de domain_id (colonnes taxo). Si domain_id NULL → score partiel. Couplage trigger ↔ taxonomie prouvé.

---

## PROBE 16 — Railway (non prouvé)

**Statut :** Aucun accès direct Railway confirmé durant cet audit.  
Les fichiers `alembic_m74.txt` et `import_m5_railway.txt` montrent des tentatives de connexion Railway mais les outputs sont tronqués ou contiennent uniquement des messages INFO Alembic sans counts.

**Verdict Railway :** NON PROUVÉ — aucun count, aucune version alembic Railway confirmée.
