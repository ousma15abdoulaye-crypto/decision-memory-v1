# MRD_CURRENT_STATE
# Source de verite unique de l'etat du systeme
# Mis a jour uniquement par AO.
# Exception : agent autorise sous mandat explicite AO
# avec validation finale AO avant merge.
# Derniere mise a jour : 2026-04-02 — audit hardening NC-01/02/03 + migration 058 (fix/m13-audit-hardening PR #293)

---

## mrd_plan_hash_correction

  mrd_plan_hash_correction : 2026-03-10
  ancien_hash              : a0ceb151e36d2eb098d12f9ea6c9d0f712a772fca1db9093492d67464b2854ed
  nouveau_hash             : 5c025e4a8133dd82f40142c8716d47fe900a312a9f20cc24e673a7de225281f3
  raison                   : fichier modifié légitimement post-MRD-0
                             hash non mis à jour — correction ETA-GEL

---

## IDENTITE PLAN

plan_version          : DMS_MRD_PLAN_V1
plan_doc              : docs/freeze/DMS_MRD_PLAN_V1.md
contract_doc          : docs/freeze/SYSTEM_CONTRACT.md
framework_doc         : docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
baseline_doc          : docs/freeze/BASELINE_MRD_PRE_REBUILD.md
freeze_hashes_doc     : docs/freeze/FREEZE_HASHES.md

---

## ETAT COURANT

last_completed        : M13 (moteur profil réglementaire V5 — code + migration 057)
last_completed_at     : 2026-04-02
last_merge_commit     : 38733982 (main — PR #292 feat/M13-regulatory-profile-engine-v5)
last_tag              : v4.1.0-m12-done
next_milestone        : M14
next_status           : PENDING
blocked_on            : (vide)
m13_prerequisites     : M12 Phase 3 PR #289 mergé ; ADR-M13-001 + Pass 2A + config/regulatory PR #292 ; migration 057 appliquée prod 2026-04-02 — persistance m13_* opérationnelle côté schéma ; secrets DB = .env.railway.local + with_railway_env.py (RAILWAY_LOCAL_ENV.md)
branch_courante       : main

---

## JALONS — REGISTRE COMPLET

| Jalon    | Statut | Tag          | Commit  | Date       | Livrables principaux                        |
|----------|--------|--------------|---------|------------|---------------------------------------------|
| PRE0     | DONE   | absent       | d56dd32 | 2026-03-09 | SYSTEM_CONTRACT.md + validate_mrd_state.py  |
| MRD-0    | DONE   | mrd-0-done   | 4b2fab8 | 2026-03-09 | DMS_MRD_PLAN_V1.md + FREEZE_HASHES.md       |
| MRD-1    | DONE   | mrd-1-done   | b939e3b | 2026-03-08 | ADR-MRD-001 + migrations m7_4 + m7_4a       |
| MRD-2    | DONE   | mrd-2-done   | a3067fb | 2026-03-09 | ADR-MRD2-GENETIC + 5 tests contrat          |
| MRD-3    | DONE   | (legacy)     | b905ad4 | 2026-03-08 | CASCADE FK neutralisee DEF-MRD3-01/06       |
| MRD-4    | DONE   | mrd-4-done   | 831117b | 2026-03-09 | fingerprint + triggers + rebuild 1490 items |
| MRD-5    | DONE   | mrd-5-done   | 29efbc6 | 2026-03-09 | item_code LG-YYYYMM-NNNNNN + ADR-MRD5       |
| MRD-6    | DONE   | mrd-6-done   | 226b4dd | 2026-03-09 | taxo L1/L2/L3 + label_status + collisions   |
| M8       | DONE   | m8-done      | PR open | 2026-03-10 | 13 tables + matview + 6 triggers + seeds    |
| M9       | -      | -            | -       | -          | market_signals + formule V1.1               |
| M12      | DONE   | v4.1.0-m12-done | bde8378 | 2026-03-26 | Procedure Recognizer — passes 0 / 0.5 / 1, FSM, corpus Cloudflare R2, export JSONL calibration |
| M13      | DONE   | (à taguer CTO) | 38733982 | 2026-04-02 | Regulatory Profile Engine V5 — Pass 2A, config/regulatory YAML, migration 057+058, ADR-M13-001 |

---

## ÉTAT ALEMBIC — MIS À JOUR 2026-04-02 (dépôt = Railway prod)

local_alembic_head       : 058_m13_correction_log_case_id_index
railway_alembic_head     : 057_m13_regulatory_profile_and_correction_log
migrations_pending_railway:
  - 058_m13_correction_log_case_id_index
last_sync_railway        : 2026-04-02 — apply 057 prod — preuve : diagnose_railway_migrations.py → [OK] synchronisé
last_updated             : 2026-04-02
updated_by               : apply_railway_migrations_safe.py --apply via python scripts/with_railway_env.py (charge .env.railway.local)
audit_ref                : docs/audits/AUDIT_CTO_SENIOR_2026-03-17.md
railway_sync_governance  : docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md
evaluation_documents     : migration 056 ; m13_regulatory_profile_versions + m13_correction_log (RLS) — migration 057 déployée prod ; 058 = index case_id (pending).

## MANDAT 4 — EXTRACTION RÉELLE (2026-03-17)
  merge_commit            : 87942a3 (PR#215)
  tag                     : v4.1.0-pre-m12-extraction-reelle-done
  livrables               : extraction_models.py, llm_router.py (LLMRouter),
                            extraction.py (pont annotation-backend /predict)
  ASAP-11/12              : DONE — stub remplacé par pipeline réel

## MIGRATIONS 049/050 — CRÉÉES MANDAT 2
  - 049_validate_pipeline_runs_fk     (ASAP-05 — trigger drop/recreate)
  - 050_documents_sha256_not_null     (ASAP-06 — backfill pgcrypto/md5)

## RAILWAY — SYNC PROD (2026-04-02)

  Head prod PostgreSQL Railway : 057 (058 pending — PR #293 merged, apply via apply_railway_migrations_safe.py --apply).
  Secrets connexion scripts : RAILWAY_DATABASE_URL dans .env.railway.local (gitignored) — docs/ops/RAILWAY_LOCAL_ENV.md.
  Toute nouvelle migration reste sous GO CTO + runbook (ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE).

## M13 — REGULATORY PROFILE ENGINE (merge 2026-04-02)

  pr_merge               : PR #292 — branche feat/M13-regulatory-profile-engine-v5 supprimée sur origin après merge
  merge_commit           : 38733982
  livrables              : ADR-M13-001, config/regulatory/, Pass 2A (ANNOTATION_USE_PASS_2A), orchestrateur FSM,
                           migration 057+058, routes API regulatory_profile, tests procurement/annotation
  ref_adr                : docs/adr/ADR-M13-001_regulatory_profile_engine.md

## STACK ALEMBIC (legacy)

railway_access_method     : RAILWAY_DATABASE_URL (URL publique proxy Railway ; scripts dms_pg_connect.py + diagnose / apply)
railway_cli               : Railway CLI — lien projet local (.railway/ gitignored) ; voir docs/ops/RAILWAY_CLI_LOCAL_LINK.md

## ANNOTATION-BACKEND — M12 PHASE 3 (orchestrateur /predict)

  pr_integration         : PR #289 — branche feat/m12-phase3-backend-wiring → main (merge = humain) ; livrables code + doc gelée ici (E-82)
  statut_branchement     : implémenté — déploiement prod : ANNOTATION_USE_PASS_ORCHESTRATOR=0 par défaut jusqu’à validation ops ; puis bascule pilotée vers 1
  flags                  : ANNOTATION_USE_PASS_ORCHESTRATOR (défaut 0) ; ANNOTATION_USE_M12_SUBPASSES (aligner avec passes 1A–1D si activé) ; ANNOTATION_PIPELINE_RUNS_DIR (optionnel ; sinon tempfile — voir ENVIRONMENT.md)
  runtime_post_revue     : run_passes_0_to_1 via threadpool (async, ne bloque pas l’event loop) ; run_id uuid5 déterministe (doc + task + version pipeline v1) ; apply_railway_migrations_safe pending = ScriptDirectory.walk_revisions (merges Alembic) ; alembic_database_url IPv6 = host entre crochets dans netloc
  corpus_gate            : dépassé — ≥ 22 annotated_validated (Document B post-M12) ; gate historique 15 clos
  ref_adr                : docs/adr/ADR-M12-PHASE3-BACKEND-WIRING.md
  ref_strangler          : docs/contracts/annotation/ANNOTATION_BACKEND_MIGRATION_STRATEGY.md Phase 3 GO

---

## SCHEMA DB — COUCHE B

### Table couche_b.procurement_dict_items

  Cle primaire   : item_id       TEXT  (pas item_uid — n'existe pas)
  Label reel     : label_fr      TEXT  (pas label — n'existe pas)
  label_en       : TEXT          (present mais non utilise dans MRD)
  fingerprint    : TEXT          sha256(normalize(label_fr)|source_type)
  item_code      : TEXT          format LG-YYYYMM-NNNNNN
  birth_source   : TEXT CHECK    mercuriale|imc|seed|manual|legacy|unknown
  birth_run_id   : UUID
  birth_timestamp: TIMESTAMPTZ
  label_status   : TEXT NOT NULL draft|validated|deprecated  DEFAULT draft
  taxo_l1        : TEXT          (1287/1490 remplis)
  taxo_l2        : TEXT
  taxo_l3        : TEXT
  taxo_version   : TEXT          1.0
  item_type      : TEXT          (pre-existant M7)
  quality_score  : SMALLINT      (pre-existant M7)
  active         : BOOLEAN       DEFAULT TRUE

### Table couche_b.procurement_dict_aliases

  Cle primaire   : alias_id      TEXT
  FK vers items  : item_id       TEXT (RESTRICT — pas CASCADE)
  Colonnes       : alias_raw, normalized_alias, source, confidence
  Note           : PAS de colonne active — table complete = active

### Table public.dict_collision_log

  Schema         : public (V4 — pas couche_b)
  fuzzy_score    : double precision — echelle 0.0 a 1.0 (pas 0-100)
  resolution     : 'unresolved'|'auto_merged'|'proposal_created' (CHECK)
  item_a_id      : varchar(64)   (tronquer si item_id > 64 chars)
  item_b_id      : varchar(64)
  category_match : boolean NOT NULL (mettre FALSE si inconnu)
  unit_match     : boolean NOT NULL (mettre FALSE si inconnu)

### Triggers sur couche_b.procurement_dict_items

  trg_protect_item_identity      BEFORE UPDATE  (immuabilite item_id, fingerprint, item_code, label_fr si validated)
  trg_protect_item_with_aliases  BEFORE DELETE  (interdit si aliases presents)
  trg_block_legacy_family_insert BEFORE INSERT  (block family_id legacy)
  trg_block_legacy_family_update BEFORE UPDATE  (block family_id legacy)
  trg_compute_quality_score      BEFORE INSERT/UPDATE
  trg_dict_compute_hash          BEFORE UPDATE
  trg_dict_write_audit           AFTER UPDATE

---

## DONNEES EN BASE

### Local (localhost:5432/dms)

  dict_items_actifs           : 1490
  dict_items_avec_fingerprint : 1490  (100%)
  dict_items_avec_item_code   : 1490  (100%)
  dict_items_avec_taxo_l1     : 1287  (86.38%)
  dict_items_label_status     : 1490 draft / 0 validated / 0 deprecated
  aliases_total               : 1596
  mercurials                  : 27 396
  vendors                     : 0     (pas d'ETL local execute)
  birth_source_dominant       : unknown (tous les 1490 items)
  item_code_format            : LG-202603-000001 a LG-202603-001490

### Railway (PostgreSQL prod)

  alembic_version      : 056_evaluation_documents (aligné dépôt — sync 2026-04-01)
  mesures compteurs    : non figées ici — probes read-only : scripts/probe_railway_counts.py (avec RAILWAY_DATABASE_URL locale, jamais commitée)

### Collisions detectees

  total_collisions    : 610
  status_unresolved   : 610
  resolution          : humain uniquement (REGLE-26)

---

## DEFAILLANCES MRD-3

  Toutes les 6 defaillances sont CORRIGEES dans MRD-4 :
  DEF-MRD3-01 : numero migration delegue — CORRIGE MRD-4
  DEF-MRD3-02 : cycle test sans alembic current — CORRIGE MRD-4
  DEF-MRD3-03 : downgrade() sans fail-loud — CORRIGE MRD-4
  DEF-MRD3-04 : tests head DB hardcodes — CORRIGE MRD-4 + fix CI
  DEF-MRD3-05 : colonne fingerprint absente — CORRIGE MRD-4
  DEF-MRD3-06 : triggers protection absents — CORRIGE MRD-4

---

## STOPS ACTIFS

  Aucun STOP bloquant actif.
  STOP-TRG-1 : RESOLU — trg_protect_item_identity present
  STOP-TRG-2 : RESOLU — trg_protect_item_with_aliases present

---

## HASH CHAIN DOCUMENTS GELES

  Fichier de reference : docs/freeze/FREEZE_HASHES.md

  DMS_V4.1.0_FREEZE.md              : e892d783471639e67db8fc17c8de9366f81b37172554783b942993b815ea9ad4
  DMS_ORCHESTRATION_FRAMEWORK_V1.md : 66a6961d20f88a51cb9d0efb8bba4531e648cb4e4e5acf40edf3fd2d9f011cf6
  SYSTEM_CONTRACT.md                 : 92acb422b6066db7375e2d7e2b4131c8abe373437c4da6363b8aa8e6735aba27
  DMS_MRD_PLAN_V1.md                 : 5c025e4a8133dd82f40142c8716d47fe900a312a9f20cc24e673a7de225281f3 (corrigé ETA-GEL)
  BASELINE_MRD_PRE_REBUILD.md        : d1093db69e504ae184e15e0ba2db1f9418eada6f2cf79fcb6fac1e51dabab1fd
  DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md
    = c0369ca14803c629bd8dfbc93367791c03cc44e5a14438cf7c542a7b37afac27
    — référencé dans FREEZE_HASHES.md
  ADR-META-001-AMENDMENT-PROCESS.md
    = 0e43674a933acdff0905b874cbf3f25d4d20a2af6e5fbfa5236e2be7a6a54fcd
    — référencé dans FREEZE_HASHES.md

  Verifier integrite : python scripts/validate_mrd_state.py

---

## Architecture enterprise

  eta_v1_status    : GELÉ ✓ 2026-03-10
  adr_meta_001     : GELÉ ✓ 2026-03-10
  cb_actifs        : CB-04 uniquement
  cb_planned_m8    : CB-01 V1, CB-05, CB-08
  cb_planned_m9    : CB-01 V2, CB-02, CB-03, CB-07
  cb_planned_m10a  : CB-06

---

## CI/CD

  Workflows actifs :
    ci-main.yml              — tests principaux
    ci-invariants.yml        — tests invariants
    ci-milestones-gates.yml  — gates milestones
    ci-freeze-integrity.yml  — integrite freeze
    ci-lint-ruff.yml         — linting
    ci-format-black.yml      — formatting
    ci-regenerate-freeze-checksums.yml

  Rappel CI : ruff + black obligatoires avant tout commit migration/script

---

## REGLES OPERATIONNELLES POUR L'AGENT

### Avant toute session de travail

  1. python scripts/validate_mrd_state.py
     Si exit(1) -> STOP. Poster. Attendre GO CTO.
  2. Verifier next_milestone = milestone du mandat recu
  3. Verifier tag mrd-{N-1}-done present si applicable

### Avant tout commit migration

  python -m ruff check alembic/versions/[fichier].py
  python -m black alembic/versions/[fichier].py
  python -m ruff check alembic/versions/[fichier].py  # re-verif
  python -m black --check alembic/versions/[fichier].py  # confirmer

### Cycle migration obligatoire

  alembic current  # verifier point de depart
  alembic upgrade [rev]
  alembic current  # doit = [rev]
  alembic heads    # doit = [rev]
  alembic downgrade [rev-1]
  alembic current  # doit = [rev-1]
  alembic upgrade [rev]
  alembic current  # doit = [rev] — confirmer

### Mise a jour MRD_CURRENT_STATE en fin de milestone

  Mettre a jour :
    last_completed, last_completed_at, last_merge_commit, last_tag
    next_milestone, next_status
    local_alembic_head, local_alembic_current
    donnees en base (counts reels)
    stops actifs
    jalons (tableau)
  Committer avec :
    git commit -m "chore: MRD_CURRENT_STATE last_commit [MRD-N]"

---

## REGLE AGENT — VERIFICATION MILESTONE

  Si next_milestone != milestone du mandat recu
  -> STOP immediat
  -> Format Section 8 DMS_MRD_PLAN_V1.md
  -> Poster au CTO
  -> Zero action
