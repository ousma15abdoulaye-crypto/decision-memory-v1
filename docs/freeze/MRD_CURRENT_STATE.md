# MRD_CURRENT_STATE
# Source de verite unique de l'etat du systeme
# Mis a jour uniquement par AO.
# Exception : agent autorise sous mandat explicite AO
# avec validation finale AO avant merge.
# Derniere mise a jour : 2026-03-27 — ancre contexte M12 corpus + migration laptop (agent / mandat)

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

last_completed        : M12
last_completed_at     : 2026-03-26
last_merge_commit     : bde8378 (main — cloture M12 procedure recognizer + corpus R2 / export)
last_tag              : v4.1.0-m12-done
next_milestone        : M13
next_status           : PENDING
blocked_on            : (vide)
m13_prerequisites     : hors registre STOP — ADR LLM (RÈGLE-11), wiring backend.py si GO CTO, sync Railway si GO CTO — détail transition § dans docs/milestones/M12_PROCEDURE_RECOGNIZER_DONE.md
branch_courante       : main

---

## CONTEXT ANCHOR — M12 CORPUS & MIGRATION LAPTOP (2026-03-27)

Section d’ancrage pour handover machine : **ne remplace pas** les champs `last_completed` / jalons ci-dessus ; décrit l’état **données locales** et l’outillage export.

### Où sont les « 57 » (corpus M12 côté disque)

- Les **57** correspondent à **57 lignes JSON** dans **un seul fichier** :
  - `data/annotations/m12_corpus_from_ls.jsonl`
- Ce n’est **pas** 57 fichiers séparés : **une ligne = une annotation** (tâche Label Studio × annotation) exportée via l’API LS (`scripts/export_ls_to_dms_jsonl.py`).
- Le fichier est **gitignoré** (`.gitignore` : `data/annotations/m12_corpus*.jsonl`). Pour le nouveau laptop : **copier ce fichier** avec le reste du dossier `data/` (voir `docs/dev/LAPTOP_MIGRATION.md`).

### Vérité R2 vs export LS

- **R2** (Cloudflare, sink S3 du webhook) peut contenir **plus d’objets** que le JSONL LS (révisions multiples par `content_hash`, backfill).
- Fichier cible **réaligné** (R2 prioritaire + complément LS pour identités absentes du bucket) :
  - `data/annotations/m12_corpus_realigned.jsonl`
- **Sans** variables `S3_BUCKET` / `S3_ENDPOINT` / clés API R2, l’export R2 **échoue** ou produit **0 ligne** ; `LABEL_STUDIO_*` ne suffit **pas** pour lire le bucket.

### Dernier inventaire connu (export LS, réf. avant réalignement R2 réussi)

- 57 lignes `m12-v2`, `project_id` 1.
- `export_ok` : 56 `true`, 1 `false` (tâche ~163).
- `annotation_status` : 56 `validated`, 1 absent (~196).
- Commande : `python scripts/inventory_m12_corpus_jsonl.py data/annotations/m12_corpus_from_ls.jsonl`

### Travaux outillage réalisés (mandat agent, mars 2026)

- `scripts/export_r2_corpus_to_jsonl.py` : chargement `.env`, `.env.local`, `data/annotations/.r2_export_env` ; `--exclude-jsonl` ; `--backfill-from-jsonl` (fusion R2 + lignes LS manquantes dans R2) ; déduplication R2 par `LastModified` S3 ; équivalence filtre statut `validated` / `annotated_validated` ; message d’erreur explicite si `S3_BUCKET` absent.
- `services/annotation-backend/corpus_sink.py` : `iter_corpus_m12_objects_from_s3` (ligne + clé S3 + `LastModified`).
- `data/annotations/r2_export.env.example` ; `.r2_export_env` ajouté au `.gitignore`.
- Tests : `services/annotation-backend/tests/test_corpus_sink.py` (itérateur S3 + wrapper).

### TODO — après rebranchement nouveau laptop

1. Recopier `data/annotations/m12_corpus_from_ls.jsonl` (et tout `data/annotations/` utile) depuis l’ancien PC ou la sauvegarde disque.
2. Renseigner R2 : copier `data/annotations/r2_export.env.example` → `data/annotations/.r2_export_env` **ou** mettre `S3_*` dans `.env.local` (voir `services/annotation-backend/ENVIRONMENT.md`, `docs/m12/M12_EXPORT.md`).
3. Réaligner :  
   `python scripts/export_r2_corpus_to_jsonl.py -o data/annotations/m12_corpus_realigned.jsonl --project-id 1 --backfill-from-jsonl data/annotations/m12_corpus_from_ls.jsonl`
4. Inventaire sur le fichier réaligné :  
   `python scripts/inventory_m12_corpus_jsonl.py data/annotations/m12_corpus_realigned.jsonl`
5. Sécurité : régénérer jetons Label Studio / clés R2 si exposés (terminal, captures).

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

---

## ÉTAT ALEMBIC — MIS À JOUR 2026-03-17

local_alembic_head       : 050_documents_sha256_not_null
railway_alembic_head     : 044_decision_history
migrations_pending_railway:
  - 045_agent_native_foundation
  - 046_imc_category_item_map
  - 046b_imc_map_fix_restrict_indexes
  - 047_couche_a_service_columns
  - 048_vendors_sensitive_data
  - 049_validate_pipeline_runs_fk
  - 050_documents_sha256_not_null
last_sync_railway        : DÉSYNCHRONISÉ — GO CTO requis avant sync
last_updated             : 2026-03-17
updated_by               : AO — post audit CTO senior 2026-03-17 (Mandat 2)
audit_ref                : docs/audits/AUDIT_CTO_SENIOR_2026-03-17.md

## MANDAT 4 — EXTRACTION RÉELLE (2026-03-17)
  merge_commit            : 87942a3 (PR#215)
  tag                     : v4.1.0-pre-m12-extraction-reelle-done
  livrables               : extraction_models.py, llm_router.py (LLMRouter),
                            extraction.py (pont annotation-backend /predict)
  ASAP-11/12              : DONE — stub remplacé par pipeline réel

## MIGRATIONS 049/050 — CRÉÉES MANDAT 2
  - 049_validate_pipeline_runs_fk     (ASAP-05 — trigger drop/recreate)
  - 050_documents_sha256_not_null     (ASAP-06 — backfill pgcrypto/md5)

## DIVERGENCE RAILWAY — CRITIQUE
  7 migrations non appliquées en production.
  Toute fonctionnalité basée sur 045-048 (incl. 046b) est silencieusement
  cassée en production jusqu'à synchronisation.
  GO CTO obligatoire avant alembic upgrade sur Railway.

## STACK ALEMBIC (legacy)

railway_access_method     : RAILWAY_DATABASE_URL dans .env (direct)
railway_cli               : ABSENT (node/npm absents sur ce poste)

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

### Railway (maglev.proxy.rlwy.net:35451/railway — PostgreSQL 17.7)

  alembic_version      : m7_4b  (3 migrations en retard)
  vendors              : 661
  mercurials           : 27 396
  dict_items_actifs    : 0      (pas encore ingere en prod)
  aliases              : 0
  seeds_validated      : 0

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
