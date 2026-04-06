# MRD_CURRENT_STATE
# Source de verite unique de l'etat du systeme
# Mis a jour uniquement par AO.
# Exception : agent autorise sous mandat explicite AO
# avec validation finale AO avant merge.
# Derniere mise a jour : 2026-04-06 — M16 Comparatif (PR #340 merge 1c32f51a) + état Alembic dépôt head 084 ; Railway prod **079** jusqu'à apply migrations 081–084 (mandat AO)

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

last_completed        : V4.2.0 Workspace-First (PRs #319–#323, 2026-04-04) + **V4.3.1 BLOC5** (PR #329, 2026-04-05) + **M16 Comparatif contradictoire** — Alembic 081–084, API `/m16`, PV `evaluation.m16`, backfill `scores_matrix` (PR #340, 2026-04-06)
last_completed_at     : 2026-04-06
last_merge_commit     : 1c32f51a (main — merge PR #340 M16 ; incl. ff88173c revue Copilot)
last_tag              : v4.1.0-m12-done (V4.2.0 / V4.3.1 tags pending CTO)
next_milestone        : V4.2.0 Pilote SCI Mali — wiring `src/api/main.py` restant + bascule `ANNOTATION_USE_PASS_ORCHESTRATOR=1` + exécution pilote 5 processus (migrations DB **alignées**)
next_status           : EN ATTENTE GO CTO — wiring routers **main.py** ; ~~migrations Railway 068–079~~ **OK head 079** ; REGLE-23 annotations **OK** (105 sync 2026-04-05) ; orchestrateur Pass **pas** basculé prod
blocked_on            : (1) wiring `src/api/main.py` pour routers V4.2.0 ; ~~(2) apply migrations 068–079 Railway~~ **fait** — head **079** (`079_bloc5_confidence_qualification_signal_log`) ; **(2b) apply migrations 081–084 Railway** — dépôt head **084** (`084_m16_price_line_comparisons`) ; dry-run : `python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py` (requis `RAILWAY_DATABASE_URL` / `.env.railway.local`) ; ~~(3) sync annotations~~ **fait** — 105 `annotation_registry` Railway ; (4) bascule `ANNOTATION_USE_PASS_ORCHESTRATOR=1` (fenêtre hors session annotation) ; (5) **complétude référentiel vendors « national »** = décision produit / hors seul lot M4 — voir `scripts/README_VENDOR_IMPORT.md` (103 = cible lot M4 ; 661 = métrique incident avril 2026)
m13_prerequisites     : M12 Phase 3 PR #289 mergé ; ADR-M13-001 + Pass 2A + config/regulatory PR #292 ; migration 057 appliquée prod 2026-04-02 — persistance m13_* opérationnelle côté schéma ; secrets DB = .env.railway.local + with_railway_env.py (RAILWAY_LOCAL_ENV.md) ; **PR #331** : `with_railway_env` aligne `DATABASE_URL` sur `RAILWAY_DATABASE_URL` (opt-out `WITH_RAILWAY_ENV_PRESERVE_DATABASE_URL=1`)
m14_deliverables      : PR #295 (moteur + API) + PR #297 (dual-app, 059, linking, save_m14_audit, CI, gel) ; ADR-M14-001 + DMS-M14-ARCH-RECONCILIATION ; docs ops Railway (RAILWAY_LOCAL_ENV, with_railway_env)
vendors_ops_2026_04   : PR #330 préflight schéma + `--check-migration-compat` ; PR #332 tranche 661 vs 103 ; import ETL M4 Railway **lot 103 lignes** (2026-04-05) — `scripts/README_VENDOR_IMPORT.md`
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
| M14      | DONE   | (à taguer CTO) | 7913d465 | 2026-04-03 | M14 + correction A+B — PR #297 : dual-app /api/m14, 059 audit, process linking, save_m14_audit, tests + INV-09 |
| DMS V2   | DONE   | (à taguer CTO) | f54a0f00 | 2026-04-03 | DMS VIVANT V2 IA agentique native — PR #300 : H0 (060-067), H1 EventIndex+bridge, H2 PatternDetector+ARQ, H3 RAG+embeddings+langfuse+RAGAS, H4 API views + agent tools — CI 9/9 ✓ |
| M15 ops  | DONE   | (à taguer CTO) | 3aa1f509 | 2026-04-03 | M15 Correction Gaps 8 phases — PR #301 : probe Railway, migrations 059→067, sync annotations, mercurials coverage, 100 items validés, RLS, DR, métriques — CI 9/9 ✓ |
| V4.2.0 P0| DONE   | (à taguer CTO) | 7d5f76e4 | 2026-04-04 | Phase 0 Workspace-First — docs ADRs, pools connexions, checklist routes |
| V4.2.0 P1| DONE   | (à taguer CTO) | 4b7defae | 2026-04-04 | Phase 1 — Migrations 068-073 (15 tables workspace-first) — CI 9/9 ✓ |
| V4.2.0 P2| DONE   | (à taguer CTO) | 7bc0ba7f | 2026-04-04 | Phase 2 — Dual-Write case_id + workspace_id — CI 9/9 ✓ |
| V4.2.0 P3| DONE   | (à taguer CTO) | cac1dbd3 | 2026-04-04 | Phase 3 — Big Bang migrations 074-077 + RBAC + workspace_access — CI 9/9 ✓ |
| V4.2.0 P4| DONE   | (à taguer CTO) | d48f8bbb | 2026-04-04 | Phase 4 — src/assembler/ Pass-1 ZIP→bundles LangGraph — CI 9/9 ✓ |
| V4.2.0 P56| DONE  | (à taguer CTO) | 98c3f2e2 | 2026-04-04 | Phase 5+6 — Routes W1/W2/W3 + WebSocket + ARQ Couche B + Pilote SCI Mali — CI 9/9 ✓ |
| V4.3.1 BLOC5 | DONE | (à taguer CTO) | 63993752 | 2026-04-05 | SPEC V4.3.1 — cognitive helpers, migrations 078/079, `arq_sealed_workspace`, `evaluation_frame`, CI ✓ — PR #329 |
| **V4.3.1 M16** | DONE | v4.3.1-m16 (local tag optionnel CTO) | 1c32f51a | 2026-04-06 | Comparatif contradictoire — migrations 081–084, API M16, PV `evaluation.m16`, XLSX, backfill M14 — PR #340 |

---

## ÉTAT ALEMBIC — MIS À JOUR 2026-04-06 (dépôt **head 084** ; Railway prod **079** jusqu'à apply 081–084)

local_alembic_head       : 084_m16_price_line_comparisons
railway_alembic_head     : 079_bloc5_confidence_qualification_signal_log (prod au 2026-04-06 — **écart 4 migrations** 081–084 tant que non appliquées)
migrations_pending_railway: **081_m16_evaluation_domains → 084_m16_price_line_comparisons** (4 révisions) — apply via runbook CTO / `alembic upgrade head` fenêtre maintenance
last_sync_railway        : 2026-04-05/06 — chaîne 068→079 appliquée prod ; **M16 081–084** : en attente apply Railway post-merge PR #340
last_updated             : 2026-04-06
updated_by               : apply_railway_migrations_safe.py + python scripts/with_railway_env.py (PR #331 : `DATABASE_URL` ← `RAILWAY_DATABASE_URL` si défini)
audit_ref                : docs/audits/AUDIT_CTO_SENIOR_2026-03-17.md
railway_sync_governance  : docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md
evaluation_documents     : migration 056 — consommée par M14 EvaluationEngine (m14_evaluation_repository.py) ; m13_* tables (057+058 déployées prod).

---

## PROBE RAILWAY — 2026-04-03 (Phase 0 M15) — HISTORIQUE PRÉ-MIGRATION

**NOTE P0-DOC-01 — RÉSOLU 2026-04-04** : Cette probe a été exécutée AVANT l'application des
migrations 059→067 (Phase 1 M15). Les résultats reflètent l'état Railway à ce moment.
Après application de ces migrations (aussi le 2026-04-03 via apply_railway_migrations_safe.py),
le head Railway est passé à 067 — aligné avec le dépôt.
État courant Railway : voir section "ÉTAT ALEMBIC" ci-dessus (**head=079**, 0 migration pending vs dépôt).

probe_script             : scripts/probe_railway_full.py
probe_date               : 2026-04-03T15:38:49Z (PRÉ-MIGRATION 059→067)
probe_target             : maglev.proxy.rlwy.net:35451
probe_alembic_head       : 058_m13_correction_log_case_id_index (PRÉ-MIGRATION — obsolète)
probe_alembic_head_post  : 067_fix_market_coverage_trigger (POST-MIGRATION — état courant)

### Resultats probe (PRÉ-migration 059→067 — contexte historique)

| ID | Metrique | Valeur | Statut |
|---|---|---|---|
| P1 | procurement_dict_items — draft | 1490 | ORANGE — 0 validated |
| P2 | mercurials_item_map coverage | 67.38% (1004/1490) | ORANGE — seuil 70% |
| P3 | market_signals_v2 strong+moderate | 90.43% (1002/1108) | VERT |
| P4 | market_surveys count | 21850 (2023-06-01 → 2026-06-01) | VERT |
| P5 | zone_context_registry count | 21 | VERT |
| P6 | annotation_registry validated | 105 (sync delta 2026-04-05 via `--from-m12-jsonl`) | VERT — REGLE-23 OK |
| P7 | decision_snapshots count | 12 | VERT |
| P8 | public.llm_traces | ABSENTE — migration 065 pending | BLEU |
| P9 | public.dms_event_index | ABSENTE — migration 061 pending | BLEU |

### Gates M15 post-probe

| Gate | Critere | Seuil | Etat |
|---|---|---|---|
| REGLE-23 | annotation_registry.is_validated | >= 50 | VERT (105) |
| M15-C3 | strong+moderate signal_quality | >= 40% | VERT |
| M15-I2 | procurement_dict_items validated | >= 100 | ROUGE |
| Phase-3 | mercurials_item_map coverage | >= 70% | ROUGE (67.38%) |

### Actions bloquantes

1. Phase 1 : appliquer migrations 059→067 (P8/P9 PENDING_MIGRATION)
2. Phase 2 : ~~synchroniser 87 annotations locales~~ **fait** — 105 annotations synchronisees Railway (dont 4 anomalies financieres `m12_v2_anomalie_financiere_valide`)
3. Phase 4 : valider 100 items dict (P1 tous draft)
4. Phase 3.1b : mapper ~44 items manquants pour atteindre 70% coverage

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

  Head code dépôt : 059 ; head prod jusqu’à apply : 058 — lancer `apply_railway_migrations_safe.py --apply` pour 059 quand validé.
  Secrets connexion scripts : RAILWAY_DATABASE_URL dans .env.railway.local (gitignored) — docs/ops/RAILWAY_LOCAL_ENV.md.
  Toute nouvelle migration reste sous GO CTO + runbook (ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE).

## M13 — REGULATORY PROFILE ENGINE (merge 2026-04-02)

  pr_merge               : PR #292 — branche feat/M13-regulatory-profile-engine-v5 supprimée sur origin après merge
  merge_commit           : 38733982
  livrables              : ADR-M13-001, config/regulatory/, Pass 2A (ANNOTATION_USE_PASS_2A), orchestrateur FSM,
                           migration 057+058, routes API regulatory_profile, tests procurement/annotation
  ref_adr                : docs/adr/ADR-M13-001_regulatory_profile_engine.md

## DMS VIVANT V2 — ARCHITECTURE IA AGENTIQUE NATIVE (merge 2026-04-03)

  pr_merge               : PR #300 — feat/dms-vivant-v2-architecture → main (squash merge f54a0f00)
  ci_result              : 9/9 SUCCESS (lint, freeze-integrity, check-invariants, Gate·Milestones, Gate·Invariants, Gate·Freeze, Gate·Lint, Gate·Coverage, lint-and-test)

  H0 — Fondations data-native :
    migration_060        : market_coverage auto-refresh trigger (fn_refresh_market_coverage)
    migration_061        : dms_event_index partitionné (2025_h2 + default partition)
    migration_062        : colonnes event_time bitemporal (m12_correction_log, decision_snapshots, market_signals_v2, decision_history)
    migration_063        : candidate_rules + rule_promotions
    migration_064        : dms_embeddings (pgvector vector(1024))
    migration_065        : llm_traces
    migration_066        : bridge triggers (fn_bridge_* → dms_event_index)
    migration_067        : fix CONCURRENTLY dans fn_refresh_market_coverage (non-concurrent refresh uniquement)
    rls_tables           : dms_event_index, dms_embeddings, llm_traces, candidate_rules (RLS tenant_scoped)

  H1 — Memory & Event Index :
    modules              : src/memory/event_index_models.py, event_index_service.py
    bridge               : 066_bridge_triggers.py (m13_correction_log, decision_snapshots, market_signals_v2)
    adapter              : src/db/cursor_adapter.py (PsycopgCursorAdapter — ::type cast safe via negative lookbehind)

  H2 — Pattern Detection & Candidate Rules :
    modules              : pattern_detector.py, pattern_models.py, candidate_rule_generator.py, candidate_rule_service.py
    workers              : src/workers/arq_tasks.py (index_event, detect_patterns, generate_candidate_rules)
    api                  : src/api/views/learning_console.py (/api/learning/corrections, /api/learning/patterns, /api/learning/rules)

  H3 — RAG + Observabilité :
    modules              : chunker.py, embedding_service.py (BGE-M3), reranker.py, rag_service.py, deterministic_retrieval.py
    observability        : langfuse_integration.py (trace LLM), llm_traces (table 065)
    evals                : ragas_evaluator.py (fallback stub si OPENAI_API_KEY absent), golden_dataset_loader.py
    calibration          : auto_calibrator.py, calibration_service.py

  H4 — Agent Tools + API Views :
    api_views            : case_timeline.py, market_memory_card.py (GET /api/views/*)
    annotation_memory    : case_memory_writer.py (append-only → memory_entries)
    agent_tools          : tool_manifest.py (MCP-compatible), regulatory_tools.py

  nouvelles_dependances  : arq==0.26.1, langfuse>=2.0.0, FlagEmbedding>=1.2.5, ragas>=0.1.0
  adr_refs               : ADR-H2-ARQ-001, ADR-H3-LANGFUSE-001, ADR-H3-BGE-M3-001, ADR-CONFIDENCE-SCOPE-001
  freeze_ref             : docs/freeze/DMS_VIVANT_V2_FREEZE.md
  sovereignty_matrix     : docs/freeze/DMS_ARTIFACT_SOVEREIGNTY_MATRIX.yaml + .md

## M15 — CORRECTION GAPS OPERATIONNELS (merge 2026-04-03)

  pr_merge               : PR #301 — feat/m15-gaps-correction-plan → main (squash merge 3aa1f509)
  ci_result              : 9/9 SUCCESS
  copilot_comments       : 12 résolus (SQL injection, secret, docstrings, rowcount, URL guard, CSV newlines)

  Phase 0 — Probe Railway :
    script               : scripts/probe_railway_full.py
    rapport              : docs/PROBE_2026_04_03.md + docs/PROBE_2026_04_03_post_migration.md
    resultats            : voir section "PROBE RAILWAY 2026-04-03" ci-dessus

  Phase 1 — Migrations 059→067 Railway :
    script               : scripts/apply_railway_migrations_safe.py --apply
    resultats            : 9 migrations appliquées séquentiellement
    head_railway_post    : 067_fix_market_coverage_trigger (aligné dépôt)
    tables_V2_creees     : dms_event_index, llm_traces, candidate_rules, dms_embeddings, bridge_triggers

  Phase 2 — Sync annotations :
    script               : scripts/sync_annotations_local_to_railway.py `--from-m12-jsonl` (delta task_id)
    statut               : **appliqué 2026-04-05** — +30 lignes Railway (75→105) ; 4 lignes `document_type=m12_v2_anomalie_financiere_valide`
    gate_regle23         : **VERT** — 105 validated >= 50
    action_requise       : bascule ANNOTATION_USE_PASS_ORCHESTRATOR=1 (Railway Dashboard) — hors scope sync

  Phase 3 — Signal Engine :
    script_coverage      : scripts/probe_mercurials_coverage.py
    coverage_actuelle    : 67.38% (1004/1490 items mappés)
    seuil_m15            : 70% — ORANGE (44 items manquants)
    export               : docs/data/unmapped_items.csv (200 items pour mapping manuel)
    signal_quality       : strong+moderate = 90.43% — VERT (gate >= 40% atteint)
    adr                  : docs/adr/ADR-SIGNAL-TRIGGER-001.md (trigger ARQ post-ingestion)

  Phase 4 — Validation dictionnaire :
    script               : scripts/validate_dict_items.py
    input                : docs/data/dict_top100_to_validate.csv
    resultats            : 100 items label_status=validated ✓ — gate M15-I2 VERT

  Phase 5 — Orchestrateur M12 :
    statut               : ANNOTATION_USE_PASS_ORCHESTRATOR=1 NON ACTIVÉ
    action_requise       : CTO basculer via Railway Dashboard (fenêtre hors session annotation)

  Phase 6 — Isolation tenant / RLS :
    resultats            : 12 politiques RLS actives — VERT
    verification         : pg_policies Railway (2026-04-03)

  Phase 7 — Disaster Recovery :
    doc                  : docs/ops/DISASTER_RECOVERY.md
    statut               : procédures documentées (backup, RTO, RPO, restore)

  Phase 8 — Métriques M15 :
    script               : scripts/measure_m15_metrics.py
    rapport              : docs/reports/M15_METRICS.md

  Gates M15 post-PR #301 :
    C1 coverage_extraction   : 0%    — ROUGE (aucun dossier traité)
    C2 unresolved_rate       : 100%  — ROUGE (0 decisions / 12 snapshots)
    C3 vendor_match_rate     : 0%    — ROUGE (market_surveys sans vendor_id)
    C4 review_queue_rate     : 100%  — ROUGE (metrique review — voir P6 annotation_registry=105)
    C5 signal_quality_cov    : 5.5%  — ORANGE (82/1490 items avec signal)
    C6 drift_by_category     : N/A   — données insuffisantes
    M15-I2 dict validated    : 100/1490 — VERT (gate 100 atteint)
    REGLE-23                 : 105/50 — VERT (gate annotations)

  erreurs_capitalisees     : E-88 (SQL injection f-string), E-89 (secret commité), E-90 (schéma non vérifié), E-91 (audit_log prev_hash NOT NULL)

---

## V4.3.1 BLOC5 — CADRE COGNITIF & MIGRATIONS 078/079 (merge 2026-04-05)

  pr_merge               : PR #329 — `feat/bloc5-v431-complete` → main (merge `63993752`)
  ci_result              : CI Main + Milestone Gates ✓ (session 2026-04-05)
  migrations             : `078_source_package_documents_bloc5` · `079_bloc5_confidence_qualification_signal_log` (tables/colonnes bundle + `signal_relevance_log`)
  modules                : `src/cognitive/` (state, confidence, evaluation_frame, signal_relevance), `src/api/cognitive_helpers.py`, routers `workspaces` / `committee_sessions`, `src/workers/arq_sealed_workspace.py`, `src/workspace/status_transitions.py`
  adr_ref                : `docs/adr/ADR-BLOC5-V431-EVENT-PROJECTION.md`
  suite_ops              : PR #330 préflight import vendors · PR #331 alignement `DATABASE_URL` via `with_railway_env.py` · PR #332 clarification cibles vendors (661 vs 103) dans `scripts/README_VENDOR_IMPORT.md`

---

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

---

## V4.2.0 WORKSPACE-FIRST — ÉTAT PHASE 0 (2026-04-04)

### Décisions architecturales Phase 0

  decision_users_id        : INTEGER (migration 004 réelle) — V4.2.0 FK références en INTEGER
                             Conséquence : DDL migrations 068-075 adaptés (INTEGER au lieu de UUID pour users.id FK)
                             UUID pour users.id = dette future — V4.2.1_PATCH après pilote SCI Mali
  decision_dual_app        : main.py = production (source de vérité routes)
                             Règle P0-OPS-01 : toute nouvelle route workspace DOIT être dans main.py
                             Checklist : docs/ops/WORKSPACE_ROUTES_CHECKLIST.md
  decision_psycopg         : cohabitation psycopg sync (existant) + asyncpg (nouvelles routes workspace)
                             Unification = post-pilote Phase 6

  probe_v420_date          : 2026-04-04 (pré-migration 068)
  alembic_head_v420_start  : 067_fix_market_coverage_trigger
  next_milestone_v420      : MIGRATION-A (migrations 068-073 — Phase 1)

### Gates Phase 0 V4.2.0

  P0-DOC-01                : RÉSOLU — MRD probe annotée comme historique pré-migration
  P0-OPS-01                : RÉSOLU — checklist docs/ops/WORKSPACE_ROUTES_CHECKLIST.md créée
  decision_users_id        : RÉSOLU — INTEGER conservé, adaptation DDL V4.2.0
  pgvector_disponible      : VERT (migration 064 dms_embeddings déjà appliquée — extension présente)
  redis_railway            : À VÉRIFIER — P1-INFRA-01 (REDIS_URL optionnel)
  railway_plan_pro         : À VÉRIFIER — Pool 100 connexions requis Phase 4
  adr_pydantic_ai          : docs/adr/ADR-V420-001-PYDANTIC-AI.md
  adr_langgraph            : docs/adr/ADR-V420-002-LANGGRAPH.md
  adr_langfuse_selfhost    : docs/adr/ADR-V420-003-LANGFUSE-SELFHOSTED.md
  pool_connexions          : docs/adr/ADR-V420-004-CONNECTION-POOL.md

---

## V4.2.0 WORKSPACE-FIRST -- ETAT FINAL (2026-04-04)

### PRs mergees dans main

| PR   | Branche                  | Merge commit | Migrations incluses         |
|------|--------------------------|--------------|-----------------------------|
| #319 | feat/v420-p1-final       | 4b7defae     | 068-073                     |
| #320 | feat/v420-p2-final       | 7bc0ba7f     | aucune (dual-write code)    |
| #321 | feat/v420-p3-final       | cac1dbd3     | 074-077                     |
| #322 | feat/v420-p4-final       | d48f8bbb     | aucune (assembler code)     |
| #323 | feat/v420-p56-final      | 98c3f2e2     | aucune (routes + ARQ code)  |

### Schema V4.2.0 -- tables canoniques

Tables migrées de case_id vers workspace_id (migration 074 DROP COLUMN case_id CASCADE) :
- public.documents, public.dao_criteria, public.offer_extractions
- public.score_history, public.elimination_log, public.evaluation_documents

Nouvelles tables V4.2.0 (068-077) :
- public.process_workspaces (hub workspace)
- public.workspace_access (RBAC tenant scoping)
- public.workspace_events (append-only audit)
- public.supplier_bundles + bundle_documents (Pass-1 output)
- public.vendor_market_signals (Couche B signaux)
- public.market_watchlist_items (watchlist W2)
- public.committee_deliberation_events (W3 comite)
- public.committee_sessions (W3 sessions)
- public.arq_projection_log (idempotence projector ARQ)

### Triggers corrigés V4.2.0

Migration 077 (fix_bridge_triggers_workspace_id) :
- fn_bridge_score_history_to_event_index : NEW.case_id -> NULL (colonne supprimee)
- fn_bridge_elimination_log_to_event_index : NEW.case_id -> NULL

### Nouveaux modules V4.2.0

`
src/assembler/              Pass-1 ZIP -> bundles (LangGraph)
src/couche_a/auth/workspace_access.py  RBAC workspace
src/workers/arq_projector_couche_b.py  ARQ workspace_events -> Couche B
src/api/routers/workspaces.py          W1 /api/workspaces
src/api/routers/market.py              W2 /api/market
src/api/routers/committee_sessions.py  W3 /api/workspaces/committee
src/api/ws/workspace_events.py         WebSocket /ws/workspace/{id}/events
docs/ops/V420_PILOTE_SCI_MALI_RUNBOOK.md
scripts/validate_v420_pilote_gates.py
`

### Dettes techniques identifiees V4.2.0

1. WIRING main.py MANQUANT : les 3 routers V4.2.0 (workspaces, market, committee_sessions)
   ne sont PAS encore inclus dans src/api/main.py -- P0-OPS-01 non respecte.
   Mandat dedie requis.

2. MIGRATIONS RAILWAY PENDING : 068->077 (10 migrations) non appliquees prod.
   Runbook : apply_railway_migrations_safe.py --apply (GO CTO + fenetre maintenance).

3. PILOTE SCI MALI : docs/ops/V420_PILOTE_SCI_MALI_RUNBOOK.md -- a executer apres
   wiring main.py + apply migrations Railway.

4. ANNOTATION_USE_PASS_ORCHESTRATOR=1 : bascule Railway Dashboard pending CTO.

5. ~~REGLE-23 sync annotations~~ **fait** — 105 annotations synchronisees Railway (dont 4 labellisees `m12_v2_anomalie_financiere_valide`). RESTE : bascule ANNOTATION_USE_PASS_ORCHESTRATOR=1.

### Gates V4.2.0 post-merge

| Gate                    | Critere                          | Etat   |
|-------------------------|----------------------------------|--------|
| P0-OPS-01               | Routers cables main.py           | ROUGE  |
| P0-MIGRATION-RAILWAY    | Migrations 068-077 appliquees    | ROUGE  |
| REGLE-23                | >= 50 validated Railway          | VERT (105) |
| P0-CI-ALL-GREEN         | PRs #319-#323 CI 9/9             | VERT   |
| P4-ASSEMBLER            | src/assembler/ fonctionne        | VERT   |
| P5-ROUTES-W1-W2-W3      | Routes implementees (non cablees)| ORANGE |
| P6-PILOTE-SCI           | Pilote 5 processus executes      | ROUGE  |

---

## DMS-MANDAT-PARSING-84PDF-001 — exécution ingestion OCR bridge (2026-04-05)

| Champ | Valeur |
|-------|--------|
| mandat_id | DMS-MANDAT-PARSING-84PDF-001 |
| run_id | DMS-MANDAT-PARSING-84PDF-001 |
| sortie | `data/ingest/mandate_84pdf_001/` |
| pdf vus | 221 |
| tâches émises | 136 (moteur `local` uniquement) |
| skips `scanned_pdf` / `no_text_all_extractors` | **84** (objectif 84/84 non atteint) |
| `mistral_ocr` dans `by_engine` | **0** |
| mitigation SSL | `MISTRAL_HTTPX_VERIFY_SSL=0` appliqué (`.env.local` + `src/extraction/engine.py`) |
| cause constatée (logs) | `APIKeyMissingError` Mistral + Llama — aucune clé résolue dans le processus d’exécution |

Preuve machine : `data/ingest/mandate_84pdf_001/MANDATE_DMS-MANDAT-PARSING-84PDF-001_MACHINE_REPORT.json` + `ingest_report.json` du même dossier.

---

## BLOC6 — pilote SCI Mali bout-en-bout (mandat DMS-BLOC6-PILOTE-SCI-MALI-001) — 2026-04-06

| Champ | Valeur |
|-------|--------|
| rapport | `docs/ops/BLOC6_PILOT_SCI_MALI_REPORT.md` |
| verdict | **ROUGE** — scellement `POST …/committee/seal` en **HTTP 500** sur prod au moment du run ; pas de `seal_hash` / `pv_snapshot` persistés (STOP 6) |
| baseline dépôt (lecture) | `19d8578d3cb41fb977f57114cfe3b8df7ee62634` |
| `workspace_id` pilote | `3a1ebd0e-dc79-4b40-bc94-dcae1de6d33f` |
| `session_id` comité | `890d1984-b1b1-46c6-961e-b6e24225e13e` |
| `reference_code` | `DAO-2026-MOPTI-017-94454af1bc` |
| correctif dépôt (cause probable 500) | `src/api/routers/committee_sessions.py` — `session_id` snapshot PV en `str(session["id"])` avant `json.dumps` (UUID non sérialisable) |
| suite | déployer l’API puis **re-lancer** le scellement sur un workspace de test ou rouvrir pilote pour verdict runtime à jour |

---

## BLOC 6 BIS — fix seal UUID (`feat/bloc6-bis-seal-uuid-fix`) — 2026-04-06

| Champ | Valeur |
|-------|--------|
| mandat | correctif post-rapport BLOC 6 (UUID JSON + helper `safe_json_dumps`) |
| verdict **code** | **VERT** — `src/utils/json_utils.py` + handler seal enrichi (`pv_snapshot` + comptage CDE) + tests `tests/test_json_utils_safe_dumps.py` |
| verdict **prod** | **EN ATTENTE** — merge PR + déploiement Railway ; puis `POST …/committee/seal` à rejouer (session pilote encore **active** + workspace **in_deliberation** au 2026-04-06) |
| `seal_hash` preview (prod) | **NULL** — aucun seal réussi en prod après correctif tant que déploiement + re-run non faits |
| preuve SQL prod (lecture) | `committee_sessions` pilote : `seal_hash` / `pv_snapshot` / `sealed_at` NULL ; `reference_code` = `DAO-2026-MOPTI-017-94454af1bc` |
| doc détaillée | `docs/ops/BLOC6_PILOT_SCI_MALI_REPORT.md` section « BLOC 6 BIS » |
| escalade | si **500** après déploiement du fix : corps de réponse HTTP complet + logs — **STOP** BLOC 7 |

---

## BLOC7 — DOCGEN ENTERPRISE V4.2.1 (implémentation technique)

| Champ | Valeur |
|-------|--------|
| périmètre | Export `committee/pv` depuis snapshot scellé (`json`, `pdf`, `xlsx`) |
| état | **IMPLÉMENTÉ (code + tests ciblés)** |
| endpoint | `GET /api/workspaces/{workspace_id}/committee/pv?format=json|pdf|xlsx` |
| intégrité | Vérification SHA-256 obligatoire (`document_service.get_sealed_session`) ; `409` non scellée ; `500` hash mismatch |
| génération PDF | Templates `templates/pv/*.j2` + `static/pv_design_system.css` + WeasyPrint |
| génération XLSX | `src/services/xlsx_builder.py` (`DataBarRule`, `weighted_score` export-only, onglet traçabilité) |
| câblage API | Router BLOC7 branché dans `src/api/main.py` et `main.py` |
| tests ciblés | `tests/test_jinja_filters.py`, `tests/services/test_pv_builder.py`, `tests/services/test_document_service.py`, `tests/api/test_committee_pv_export.py` (**8 passed**) |
| infra runtime | `Dockerfile` enrichi dépendances WeasyPrint + `railway.toml` build Dockerfile + `requirements.txt` (`weasyprint`) |
| garde-fous | Kill-list exclue du snapshot ; zéro écriture DB en export ; hash recalculé sur snapshot canonique |
