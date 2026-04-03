# CONTEXT ANCHOR OFFICIEL — VERSION OPPOSABLE ET INVIOLABLE

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  CONTEXT ANCHOR — DMS v4.1                                          ║
║  Dernière mise à jour : 2026-04-03 (post-merge PR #301 — M15 Correction Gaps 8 phases) ║
║  Autorité : CTO / AO — Abdoulaye Ousmane                           ║
║  Statut : DOCUMENT VIVANT — OPPOSABLE — INVIOLABLE                 ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ██████████████████████████████████████████████████████████████    ║
║  ██  CLAUSE D'INTÉGRITÉ — GRAVÉE — NE PEUT PAS ÊTRE RETIRÉE  ██    ║
║  ██████████████████████████████████████████████████████████████    ║
║                                                                      ║
║  CE DOCUMENT EST PROTÉGÉ PAR LES RÈGLES SUIVANTES :               ║
║                                                                      ║
║  RÈGLE-ANCHOR-01 — INTÉGRITÉ ABSOLUE                               ║
║    Il est INTERDIT de raccourcir ce document.                      ║
║    Il est INTERDIT d'en supprimer des sections.                    ║
║    Il est INTERDIT de le résumer ou condenser.                     ║
║    Toute mise à jour = AJOUT uniquement, jamais suppression.       ║
║    Violation = faute disciplinaire grave.                          ║
║                                                                      ║
║  RÈGLE-ANCHOR-02 — MISE À JOUR OBLIGATOIRE                         ║
║    Ce document DOIT être mis à jour à chaque fin de session.       ║
║    Chaque merge, chaque milestone, chaque décision architecture.   ║
║    Le LLM qui omet cette mise à jour commet une faute.             ║
║    Format : date ISO + contenu complet + commit sur main.          ║
║                                                                      ║
║  RÈGLE-ANCHOR-03 — SOURCE DE VÉRITÉ UNIQUE                         ║
║    Ce document prime sur toute mémoire de session du LLM.         ║
║    En cas de doute : ce document a raison, le LLM a tort.         ║
║    Le LLM ne peut pas "se souvenir" d'une règle non écrite ici.   ║
║                                                                      ║
║  RÈGLE-ANCHOR-04 — INTERDICTION D'IMPROVISATION                    ║
║    Le LLM ne peut proposer AUCUNE solution technique               ║
║    non fondée sur ce document ou le Plan Directeur V4.1.          ║
║    Si l'information manque : STOP — demander AO.                  ║
║    Jamais improviser. Jamais dériver vers la facilité.             ║
║                                                                      ║
║  RÈGLE-ANCHOR-05 — ALEMBIC INTOUCHABLE                             ║
║    La chaîne Alembic 001→045 est FREEZE ABSOLU.                   ║
║    Toute migration = nouveau fichier séquentiel uniquement.        ║
║    Zéro modification des migrations existantes.                    ║
║    Zéro autogenerate. Migrations SQL brut uniquement.              ║
║    Violation = faute disciplinaire grave immédiate.                ║
║                                                                      ║
║  RÈGLE-ANCHOR-06 — RAILWAY PROTÉGÉ                                 ║
║    INTERDIT sur Railway : migrations, ALTER, DROP, DELETE.         ║
║    INTERDIT : modifier services DMS existants (FastAPI, PG DMS).  ║
║    INTERDIT : SQLite, toute base autre que PostgreSQL.             ║
║    AUTORISÉ : compute, seeds validés CTO, probe, lecture.          ║
║    Flag requis : DMS_ALLOW_RAILWAY=1.                              ║
║                                                                      ║
║  RÈGLE-ANCHOR-07 — STOP EXPLICITE OBLIGATOIRE                      ║
║    Le LLM DOIT s'arrêter et demander AO si :                      ║
║      - Une règle du Plan Directeur est absente du contexte        ║
║      - Une action touche Railway, Alembic, ou la DB prod          ║
║      - Deux mandats consécutifs échouent sur le même point        ║
║      - Le LLM commence à improviser faute d'information           ║
║    Jamais continuer en espérant que ça marche.                    ║
║                                                                      ║
║  RÈGLE-ANCHOR-08 — PÉRIMÈTRE FERMÉ OBLIGATOIRE                     ║
║    Tout mandat doit lister exactement les fichiers à créer.       ║
║    Zéro fichier supplémentaire non listé.                          ║
║    Zéro modification de fichier non listé.                         ║
║    L'agent vérifie le périmètre avant tout commit.                ║
║                                                                      ║
║  RÈGLE-ANCHOR-09 — ERREURS CAPITALISÉES PERMANENTES               ║
║    Toute erreur commise est inscrite ici définitivement.           ║
║    Elle ne peut pas être effacée.                                  ║
║    Elle sert de garde-fou pour toutes les sessions suivantes.     ║
║                                                                      ║
║  RÈGLE-ANCHOR-10 — HIÉRARCHIE DES AUTORITÉS                       ║
║    1. Plan Directeur DMS V4.1 (document source — 20 pages)        ║
║    2. Ce context anchor (condensé opposable)                       ║
║    3. Les mandats CTO (instructions de session)                    ║
║    4. Le LLM (exécutant — zéro autorité propre)                   ║
║    En cas de conflit : l'autorité supérieure prime toujours.      ║
║                                                                      ║
║  ██████████████████████████████████████████████████████████████    ║
║  ██              FIN CLAUSE D'INTÉGRITÉ                       ██    ║
║  ██████████████████████████████████████████████████████████████    ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  GIT — 2026-04-02                                                    ║
║  ──────────────────────────────────────────────────────────────     ║
║  main              : 38733982 — Merge PR #292 feat/M13-regulatory-profile-engine-v5 ║
║    (M13 V5 engine, config/regulatory YAML SCI+DGMP, Pass 2A, migration 057, ADR-M13-001) ║
║  Branche PR #292   : supprimée sur origin après merge                              ║
║  main (historique) : à jour 2026-04-01 — PR #286 + #287 mergés ; MRD/CONTEXT alignés ║
║  PR #289 feat/m12-phase3-backend-wiring : M12 Ph.3 backend (orchestrateur /predict, ║
║    fixes revue Copilot : threadpool, uuid5, ScriptDirectory apply, IPv6 URL) ║
║  PR #286 fix/alembic-diagnose-chain-truth : MERGÉ (diagnostic Alembic ScriptDirectory) ║
║  PR #287 docs/pre-m13-enterprise-governance : MERGÉ (ADR, runbook unique, smoke main:app) ║
║  Branches distantes PR #286 / #287 : supprimées après merge                       ║
║  (historique) main 6775b65 : Merge PR #276 feat/phase-0-docker-infra            ║
║  feat/phase-0-docker-infra : MERGÉ dans main (Phase 0 — PR #276)     ║
║  feat/m12-engine-v6 : MERGÉ dans main (M12 Engine V6 — PR #274)     ║
║  feat/fix-extract-02 : MERGÉ dans main (M-FIX-EXTRACT-02)            ║
║  feat/pre-m12-extraction-reelle : MERGÉ dans main (Mandat 4)        ║
║  fix/m13-audit-hardening : MERGÉ dans main (PR #293 — audit M13 hardening) ║
║  feat/fix-backend-production : backend v3.0.1d (en attente merge)   ║
║  alembic head dépôt / CI : 067_fix_market_coverage_trigger (main — PR #300 mergé 2026-04-03) ║
║  alembic head Railway prod : 067_fix_market_coverage_trigger (migrations 059→067 appliquées — M15 Phase 1) ║
║  migrations pending Railway : AUCUNE — 059→067 appliquées séquentiellement via apply_railway_migrations_safe.py (M15 Phase 1) ║
║  RAILWAY_DATABASE_URL : défini hors dépôt — fichier local .env.railway.local (gitignored) ; ║
║    chargement scripts/with_railway_env.py ou .\\scripts\\load_railway_env.ps1 — RAILWAY_LOCAL_ENV.md ║
║  annotation-backend M12 Ph.3 : orchestrateur derrière ANNOTATION_USE_PASS_ORCHESTRATOR ║
║    (défaut 0 — monolith Mistral inchangé ; 1 = Pass 0→0.5→1 puis Mistral) ║
║  Gel Cursor services/annotation-backend : dégel conditionnel Phase 3 sous mandat ║
║    CTO — voir .cursor/rules/dms-annotation-backend-freeze.mdc + ADR-M12-PHASE3 ║
║  M15 Phase 1 : migrations 059→067 appliquées Railway prod (2026-04-03)    ║
║  M15 Phase 3 : mercurials_item_map coverage = 67.38% (seuil 70% non atteint) ║
║    unmapped items : docs/data/unmapped_items.csv (200 items pour mapping manuel) ║
║  M15 Phase 4 : 100 items procurement_dict_items label_status=validated ✓  ║
║  M15 Phase 6 : 12 politiques RLS actives Railway — isolation tenant OK ✓  ║
║  M15 REGLE-23 gate : 0 annotated_validated Railway — 87 annotations locales à sync ║
║    Action requise : sync via scripts/sync_annotations_local_to_railway.py  ║
║    puis bascule ANNOTATION_USE_PASS_ORCHESTRATOR=1 (Railway Dashboard)    ║
║  PR #301 : feat(m15) plan correction gaps — squash merge 3aa1f509 main (2026-04-03) ║
║  tags posés :                                                         ║
║    v4.1.0-ocr-files-api-done                                         ║
║    v4.1.0-m12-dette7-done                                             ║
║    v4.1.0-pre-m12-security-done                                       ║
║    v4.1.0-pre-m12-extraction-reelle-done                              ║
║    v4.1.0-fix-pipeline-done                                          ║
║    v4.1.0-fix-extract-done                                            ║
║                                                                      ║
║  ALEMBIC — FREEZE ABSOLU                                            ║
║  ──────────────────────────────────────────────────────────────     ║
║  head actuel     : 058_m13_correction_log_case_id_index              ║
║  historique      : 001 → 045 — FREEZE TOTAL 001-045                ║
║  chaîne          : 044→045→046→046b→047→048→049→050→051→052→053→054→055→056→057→058 ║
║  FREEZE          : 001 → 045 FREEZE TOTAL                          ║
║                    046 + 046b = DETTE-7 DONE                        ║
║                    047 = PHASE 1B DONE (ORM→psycopg Couche A)       ║
║                    048 = vendors_sensitive_data                      ║
║                    049 = validate_pipeline_runs_fk                   ║
║                    050 = documents_sha256_not_null                   ║
║                    051 = cases_tenant_user_tenants_rls               ║
║                    052 = dm_app_rls_role                             ║
║                    053 = dm_app_enforce_security_attrs               ║
║                    054 = m12_correction_log (M12 feedback loop)      ║
║                    055 = extend_rls_documents_extraction_jobs (RLS)  ║
║                    056 = evaluation_documents (M13 ACO + RLS)        ║
║                    057 = m13_regulatory_profile_versions + m13_correction_log (RLS) ║
║                    058 = idx_m13_correction_log_case_id (FK join perf) ║
║  RÈGLE           : zéro autogenerate — SQL brut uniquement         ║
║  RÈGLE           : zéro modification fichiers existants 001-058    ║
║  RÈGLE           : toute nouvelle migration = 059+ séquentiel       ║
║  apply_safe      : scripts/apply_railway_migrations_safe.py — prod 058 ALIGNÉ (sync 2026-04-02) ║
║    via ScriptDirectory (graphe merges), pas parse linéaire seul    ║
║  VIOLATION       : faute disciplinaire grave immédiate             ║
║                                                                      ║
║  SCHÉMAS PostgreSQL — DÉFINITIF                                     ║
║  ──────────────────────────────────────────────────────────────     ║
║  public    : 79 tables métier                                      ║
║  couche_b  : 15 tables procurement                                 ║
║  couche_a  : agent_checkpoints, agent_runs_log (propriétaire 045)  ║
║              fn_dms_event_notify, fn_prevent_runs_delete           ║
║  SQLite    : INTERDIT — PostgreSQL uniquement sur ce projet        ║
║                                                                      ║
║  RAILWAY — DONNÉES RÉELLES CONFIRMÉES POST-M11                      ║
║  ──────────────────────────────────────────────────────────────     ║
║  procurement_dict_items : 1 490 items actifs                       ║
║  mercurials             : 27 396 lignes (DGMP 2023→2026)           ║
║  mercurials.item_id     : UUID — VIDE — NON UTILISÉ                ║
║                           jointure via item_canonical UNIQUEMENT   ║
║  mercurials_item_map    : 1 629 mappings                           ║
║  tracked_market_items   : 1 004 items                              ║
║  tracked_market_zones   : 19 zones                                 ║
║  zone_context_registry  : 20 contextes (6+14 DETTE-1) ✓            ║
║  geo_price_corridors    : 7 corridors (Gao→Menaka ML-9/32%) ✓     ║
║  seasonal_patterns      : 1 786 (v1.1_mercurials) ✓                ║
║  market_signals_v2      : 1 106 signaux (post M11 compute) ✓       ║
║                           formula_version 1.1                      ║
║                           CRITICAL zones ipc_3+/ipc_4+ uniquement  ║
║                           severity_level NULL = 0 ✓                ║
║  market_surveys         : 13 110 lignes ✓ DETTE-2 résolue         ║
║  decision_history       : 115 lignes ✓ DETTE-3 résolue            ║
║  dict_collision_log     : 0 (résolu M10A)                          ║
║  couche_a               : agent_checkpoints, agent_runs_log (045)  ║
║  imc_entries            : 810 lignes (INSTAT 2018→2026)              ║
║  imc_sources            : traçabilité PDFs INSTAT                  ║
║  imc_category_item_map  : 0 mappings (table créée — vide)          ║
║                           À remplir : AO + DETTE-8                  ║
║                                                                      ║
║  CONTRACT-02 — DÉFINITIF                                            ║
║  ──────────────────────────────────────────────────────────────     ║
║  INTERDIT Railway  : migrations, ALTER, DROP, DELETE               ║
║  INTERDIT Railway  : SQLite, toute base non PostgreSQL             ║
║  INTERDIT Railway  : modifier services DMS existants                ║
║  AUTORISÉ Railway  : compute, seeds validés CTO, probe              ║
║  Flag Railway      : DMS_ALLOW_RAILWAY=1                            ║
║  Tests M11         : M11_SEEDED=1 requis                           ║
║                                                                      ║
║  JOINTURE MERCURIALS — DÉFINITIVE ET FIGÉE                          ║
║  ──────────────────────────────────────────────────────────────     ║
║  mercurials.item_id (UUID) = artefact legacy — IGNORÉ              ║
║  Chemin obligatoire :                                                ║
║    item_canonical → mercurials_item_map → dict_item_id             ║
║  Jointure : LOWER(TRIM(item_canonical)) des deux côtés              ║
║                                                                      ║
║  ARCHITECTURE IMC — FIGÉE                                           ║
║  ──────────────────────────────────────────────────────────────     ║
║  SOURCE-1 mercurials   : prix unitaires DGMP zone×item 2023→2026    ║
║  SOURCE-2 imc_entries  : indices INSTAT catégorie×mois 2018→2026   ║
║                          NE PAS FUSIONNER avec mercurials           ║
║  SOURCE-3 imc_sources  : PDFs bulletins INSTAT parsés               ║
║  SOURCE-4 mercuriale_sources : PDFs DGMP parsés                     ║
║  Pont imc_category_item_map : DETTE-7 DONE (046 + 046b)             ║
║  Formule révision      : P1 = P0 × (IMC_t1 / IMC_t0)                ║
║  Signal IMC            : MOM > 3% → WATCH construction             ║
║                          MOM > 8% → STRONG construction             ║
║                          YOY > 15% → CRITICAL construction         ║
║                                                                      ║
║  CORRECTION ARCHITECTURALE M11 — FIGÉE                              ║
║  ──────────────────────────────────────────────────────────────     ║
║  zone-menaka-1 : ML-9 / 32.0% / ipc_4_emergency                    ║
║  ML-6 (+50%)   : Kidal UNIQUEMENT                                   ║
║                                                                      ║
║  INFRASTRUCTURE ANNOTATION — M11-bis                                 ║
║  ──────────────────────────────────────────────────────────────     ║
║  Label Studio                                                        ║
║    Service Railway   : label-studio-dms                             ║
║    Image             : heartexlabs/label-studio:latest              ║
║    PostgreSQL dédié  : Postgres-LS (≠ DMS PostgreSQL — R-02)       ║
║    Volume            : label-studio-data 5GB /label-studio/data     ║
║    Port interne      : 8080                                         ║
║    Healthcheck       : /health 30s/10s/3                            ║
║    Statut            : EN COURS — crash loop POSTGRE_PORT           ║
║    Problème actuel   : POSTGRE_PORT reçoit string vide              ║
║                        ${{Postgres-LS.PGPORT}} non résolu           ║
║                        Fix en attente : POSTGRE_PORT=5432 fixe      ║
║                        + diagnostic complet Plan Directeur requis   ║
║                                                                      ║
║  EXTRACTION — ÉTAT RÉEL POST-MERGE M-FIX-EXTRACT-02 + PR #276          ║
║  ──────────────────────────────────────────────────────────────     ║
║  extract_text_any :                                                    ║
║    pypdf principal                                                      ║
║    pdfminer.six fallback si text_len < 100                              ║
║    log WARNING text_len=0 → PDF_SCAN_SANS_OCR ou PDF_CORROMPU          ║
║    SLA-B engine : cloud-first (mistral_ocr / llamaparse / azure) ;     ║
║    alias DB "tesseract" → même chemin mistral_ocr (E-81, PR #276).     ║
║    OCR (Mistral / Tesseract) = M10A — hors scope beta                   ║
║  Cas non résolus (M10A) :                                               ║
║    PDF scan sans OCR → text_len=0 → review_required                     ║
║    PDF corrompu → text_len=0 → rejeté                                   ║
║                                                                      ║
║  ML BACKEND — v3.0.1d (feat/fix-backend-production)                   ║
║  ──────────────────────────────────────────────────────────────     ║
║  schema          : v3.0.1d                                           ║
║  prompt          : prompts/system_prompt.txt (texte pur .txt)       ║
║  validateur      : prompts/schema_validator.py (Pydantic v2)        ║
║  troncature      : 200 000 chars (env MAX_TEXT_CHARS)               ║
║  modèle          : mistral-large-latest                              ║
║  OCR             : mistral-ocr-latest (Files API stream)              ║
║  max_tokens      : 32 000                                            ║
║  response_format : json_object                                       ║
║  3 couches ctrl  : prompt squelette + Pydantic + recalcul Python     ║
║  start.sh        : uvicorn ... 2>&1 (E-45 — faux positifs Railway)   ║
║  parse           : 5 tentatives                                     ║
║  ANNOTATION_BACKEND_URL : à ajouter Railway Variables               ║
║                                                                      ║
║  RÈGLES ANNOTATION — FIGÉES                                         ║
║  ──────────────────────────────────────────────────────────────     ║
║  Confiance     : 1.00 / 0.80 / 0.60 / null UNIQUEMENT              ║
║                  {1:0.60, 2:0.80, 3:1.00} maxRating=3               ║
║                  Jamais 0.90 — jamais 4 niveaux                     ║
║  RÈGLE-19      : value + confidence_expected + evidence_hint       ║
║                  JAMAIS valeur nue dans ground_truth                 ║
║  Format JSONL  : Plan Directeur Partie VIII                         ║
║                  wrapper ground_truth obligatoire                    ║
║                  sha256 calculé sur data brut                       ║
║  AMBIG trackés : AMBIG-1/3/4/6 — tous exportés dans JSONL          ║
║  Doc types     : dao, rfq, rfp_consultance, marketsurvey,           ║
║                  devisunique, devissimple, devisformel, autre       ║
║  Critères admin: sci, nif, rccm, rib, non_sanction, quitus_fiscal   ║
║                                                                      ║
║  FREEZE ABSOLU — NE JAMAIS MODIFIER                                 ║
║  ──────────────────────────────────────────────────────────────     ║
║  docs/freeze/SYSTEM_CONTRACT.md                                     ║
║  docs/freeze/DMS_V4.1.0_FREEZE.md                                  ║
║  docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md                      ║
║  docs/freeze/ANNOTATION_FRAMEWORK_DMS_v3.0.1.md (v3.0.1a→v3.0.1c)   ║
║  migrations Alembic 001 → 044                                       ║
║                                                                      ║
║  STRUCTURE PROJET                                                    ║
║  ──────────────────────────────────────────────────────────────     ║
║  Racine : main.py, start.sh, Procfile, requirements.txt             ║
║  src/    : api/, business/, core/, couche_a/, couche_b/, db/        ║
║            evaluation/, extraction/, geo/, mapping/, vendors/       ║
║            annotation/ (orchestrator FSM, passes 0→1D, export)      ║
║            procurement/ (M12 engine L1→L7 + H1/H2/H3 ; M13 Pass 2A ; M14 Evaluation Engine) ║
║            auth_router.py, logging_config.py, ratelimit.py          ║
║  config/ : framework_signals.yaml, procurement_family_signals.yaml  ║
║            mandatory_parts/*.yaml (20 doc-type rule files)          ║
║            regulatory/*.yaml (M13 — profils SCI, DGMP Mali, etc.) ║
║  alembic/: versions/ 001–058, env.py                                ║
║  services/: annotation-backend/ (ML Backend Label Studio)            ║
║  docs/   : adr/, freeze/, mandates/, milestones/, calibration/     ║
║            contracts/annotation/ (PASS_1A→1D contracts)             ║
║  scripts/: probes, seeds, migrations, import/export                ║
║            m12_benchmark_against_corpus.py (calibration harness)    ║
║  tests/  : auth/, contracts/, invariants/, mercuriale/              ║
║            procurement/ (M12 unit tests — 13 modules)              ║
║            annotation/ (pass integration tests)                    ║
║  data/   : uploads, outputs, static                                 ║
║                                                                      ║
║  MILESTONES — 2026-03-19                                              ║
║  ──────────────────────────────────────────────────────────────     ║
║  M-FIX-PIPELINE-01 : DONE — v4.1.0-fix-pipeline-done                 ║
║  M-FIX-EXTRACT-02  : DONE — v4.1.0-fix-extract-done                   ║
║  M9      DONE  signaux, formule 1.1, corridors, FEWS                 ║
║  M10A    DONE  seasonal_patterns, zone_context, geo_corridors       ║
║  M10B    DONE  couche_a, agents, pg_notify (ADR-010)                ║
║  M11     DONE  5 dettes, 1106 signaux, severity NULL=0               ║
║  M11-bis DONE  backend v3.0.1c + XML + OCR Files API                 ║
║               PR#197 PR#198 PR#199 PR#202 PR#203                     ║
║  Mandat 1 DONE mistral-large-latest + OCR Files API stream           ║
║  Mandat 2 DONE OCR stream + troncature 80K + cleanup                 ║
║                                                                      ║
║  PRÉ-M12 EN COURS (feat/pre-m12-cleanup) :                           ║
║    ASAP-01 : purge git .txt/.csv        ✓ DONE                       ║
║    ASAP-02 : MRD_CURRENT_STATE.md       ✓ DONE                        ║
║    ASAP-03 : Railway sync prod → head 056 ✓ DONE (2026-04-01)         ║
║    ASAP-04 : M-TESTS.done              ⏳ (Mandat 2)                 ║
║    ASAP-05 : migration 049 FK validate  ⏳ (Mandat 2)                 ║
║    ASAP-06 : migration 050 sha256       ⏳ (Mandat 2)                 ║
║    ASAP-07/08 : Redis rate limit       ✓ DONE (Mandat 3)            ║
║    ASAP-09 : sqlalchemy → psycopg      ✓ DONE (Mandat 3)            ║
║    ASAP-10 : CI gates vivants         ⏳ (Mandat 2)                  ║
║    ASAP-11 : llm_router.py            ✓ DONE (Mandat 4)             ║
║    ASAP-12 : pont extraction          ✓ DONE (Mandat 4)             ║
║                                                                      ║
║  M12     DONE — Procurement Document & Process Recognizer V6          ║
║          PR #274 merged 2026-03-30 — feat/m12-engine-v6             ║
║          74 fichiers, 8 327 lignes ajoutées                          ║
║          Moteur cognitif 10 couches (L1→L7 + H1/H2/H3)              ║
║          Config-driven : 20 YAML rules, 3 signal banks              ║
║          Pipeline : Pass 1A→1D (feature flag ANNOTATION_USE_M12_SUBPASSES) ║
║          Migration : 054_m12_correction_log (feedback loop)          ║
║          Calibration : accuracy=0.82, eval_doc_recall=1.00, fw=0.86 ║
║          CI : 1238 passed, 72% coverage, INV-09 clean              ║
║          DETTE-7  DONE — imc_category_item_map + 046 + 046b        ║
║          DETTE-8  NEXT — signaux IMC → market_signals_v2            ║
║                    dépend DETTE-7 ✓                                  ║
║  M13     DONE (cœur moteur) — PR #292 mergé 2026-04-02 — Pass 2A réglementaire, ║
║          config/regulatory YAML, migration 057, ADR-M13-001 ; flag ANNOTATION_USE_PASS_2A ║
║          Suite métier / API / persistance prod : aligner Railway sur 057 puis jalons M14 ║
║  M14     DONE — PR #295 merged 2026-04-02 — Evaluation Engine V1                            ║
║          ADR-M14-001, m14_engine.py, m14_evaluation_models.py, m14_evaluation_repository.py ║
║          Routes API /api/m14/, wire case_id backend→orchestrateur, PASS_2A_DONE support    ║
║          Persistance : evaluation_documents (migration 056 existante) — pas de nouvelle migration ║
║          Tests : 26 unit + DB integrity + RLS (evaluation_documents) — CI 9/9 verte        ║
║          Copilot review : committee_id FK lookup, completion ratio bound, weighted score calc ║
║  M15     GATE  4 seuils validation go-live                         ║
║                                                                      ║
║  SEUILS M15 — FIGÉS NON NÉGOCIABLES                                 ║
║  ──────────────────────────────────────────────────────────────     ║
║  coverage_extraction  ≥ 80%                                        ║
║  unresolved_rate      ≤ 25%                                         ║
║  vendor_match_rate    ≥ 60%                                        ║
║  review_queue_rate    ≤ 30%                                        ║
║                                                                      ║
║  DETTES OUVERTES → DETTE_M12.md                                     ║
║  ──────────────────────────────────────────────────────────────     ║
║  Gate 15 docs : CLOS — corpus ≥ 22 annotated_validated (Document B) ║
║  DETTE-1    : API GET /signals (market_signals_v2)                  ║
║  DETTE-2    : listener pg_notify CRITICAL → webhook/email          ║
║  DETTE-3    : workflow validation decision_history                 ║
║  DETTE-4    : Tests Railway CI/CD (GitHub Actions)                 ║
║  DETTE-5    : ✅ DONE — evaluation_documents (migration 056) consommée par M14 ║
║  DETTE-6    : market_surveys terrain réels                         ║
║  DETTE-7    : ✅ DONE — imc_category_item_map                      ║
║               046_imc_category_item_map + 046b_imc_map_fix         ║
║  PHASE 0    : ✅ DONE — cleanup racine (fichiers parasites, MD→docs)║
║  PHASE 1B   : ✅ DONE — ORM→psycopg Couche A, migration 047         ║
║               src/couche_b/imc_map.py — PR #188 mergée              ║
║               tag v4.1.0-m12-dette7-done                          ║
║  DETTE-8    : ACTIVE — signaux IMC dans market_signals_v2           ║
║               Prérequis : DETTE-7 ✓ — Statut : NEXT                 ║
║  DETTE-9    : imc_entries 2018→2022 baseline seasonal_patterns     ║
║                                                                      ║
║  ERREURS CAPITALISÉES — PERMANENTES — NE JAMAIS REPRODUIRE          ║
║  ──────────────────────────────────────────────────────────────     ║
║  E-01  mistralai v0.x vs v1.x : API breaking change                ║
║         v1.x : from mistralai import Mistral                        ║
║                client.chat.complete() — pas client.chat()            ║
║  E-02  Format JSONL : lire Plan Directeur Partie VIII AVANT coder   ║
║  E-03  Confiance : 3 niveaux — jamais 0.90 — jamais 4 étoiles       ║
║  E-04  RÈGLE-19 : evidence_hint PARTOUT — jamais valeur nue        ║
║  E-05  Variables env Railway : texte brut — jamais Markdown        ║
║  E-06  Standard industrie (Label Studio) AVANT bricolage maison    ║
║  E-07  AMBIG-3/4 : toujours trackés dans export JSONL              ║
║  E-08  Label Studio Railway : Dashboard uniquement — pas CLI        ║
║         railway add --service --image = commande invalide           ║
║  E-09  railway.json dockerfilePath : chemin relatif au service     ║
║         "Dockerfile" pas le chemin absolu depuis racine repo        ║
║  E-10  DJANGO_DB=default : force SQLite — INTERDIT sur ce projet   ║
║         Label Studio + PostgreSQL : utiliser POSTGRE_* variables    ║
║  E-11  ${{Postgres-LS.PGPORT}} : non résolu par Railway             ║
║         POSTGRE_PORT = 5432 valeur fixe obligatoire                  ║
║  E-12  Chaîne Alembic modifiée sans autorisation CTO               ║
║         Faute disciplinaire grave — ne jamais reproduire            ║
║  E-13  Context anchor dégradé session après session                ║
║         Raccourcis cumulés → perte de règles critiques              ║
║         → improvisation → dégâts sur projet                        ║
║  E-14  evaluation_report : annotation interdite avant M15          ║
║  E-15  gate_value : booléen réel ou null, jamais string             ║
║  E-16  gate_state : séparé explicitement de gate_value              ║
║  E-17  gate confidence : 0.6 / 0.8 / 1.0 strictement               ║
║  E-18  price_date ABSENT : ne jamais forcer document_date          ║
║  E-19  offre financière + tableau sans line_items = inutilisable    ║
║  E-20  supporting_doc/annex_pricing sans parent_document_id invalide║
║  E-21  premier tri obligatoire : goods | services avant extraction  ║
║  E-22  Critère wc-l mandat : calibrer sur contenu réel             ║
║         backend.py v3.0.1a = 458 lignes CONFORME                    ║
║         Borne révisée : wc-l ≤ 600 pour fichiers prompt schema      ║
║  E-23  Migration corrective nécessaire si migration déjà en prod   ║
║         avec défaut structurel (FK, index).                          ║
║         Pattern : migration N+1 idempotente avec PROBE-SQL-01.       ║
║         Ne jamais modifier une migration déjà pushée.                ║
║         Ref : PR #188 — 046 → 046b                                  ║
║  E-24  Tests avec autocommit=True + rollback() = rollback silencieux║
║         Utiliser fixture db_tx (autocommit=False + rollback teardown) ║
║         pour tout test qui écrit en DB avec trigger DELETE bloquant. ║
║         Ref : PR #188 Copilot point 2                                ║
║  E-25  FK ON DELETE CASCADE incompatible avec trigger append-only.  ║
║         Si table append-only → FK doit être ON DELETE RESTRICT.      ║
║         Sinon : suppression parent → cascade tentée → trigger bloque ║
║         → erreur cryptique en prod. Ref : PR #188 Copilot point 1   ║
║  E-26  Log raw[:N] contenu LLM = fuite données document en logs.    ║
║         Logger uniquement : len(raw), hash court (sha256[:12]),       ║
║         task_id. Ref : PR #188 Copilot point 5 — safe_log_parse      ║
║  E-27  CORS allow_origins=["*"] en production = appels LLM non auth.║
║         Utiliser CORS_ORIGINS env var. Default = Label Studio URL.   ║
║         Ref : PR #188 Copilot point 6                                ║
║  E-28  g["gate_name"] sur JSON LLM partiel = KeyError silencieux.   ║
║         Toujours g.get() + filtre isinstance(g, dict) avant itér.   ║
║         Ref : PR #188 Copilot point 3 — safe_build_ls_result         ║
║  E-43  line_items annotation : jamais vide si montant visible.     ║
║         unit_raw obligatoire sur chaque ligne. 3 exemples min prompt. ║
║         Sans exemple → Mistral hallucine ou omet les unités.       ║
║         Ref : ADR-015 — 2026-03-16                                  ║
║  E-44  Consultance = line_items aussi. jour/expert/forfait = unités.║
║         procurement_dict s'appuie sur ces données. Mémoire marché.  ║
║         Ref : ADR-015 — 2026-03-16                                  ║
║  E-45  Railway classifie stderr en "error" peu importe le niveau. ║
║         Uvicorn envoie vers stderr. Fix : 2>&1 dans start.sh.       ║
║         Sans fix : faux positifs permanents. Ref : 2026-03-16       ║
║  E-46  Mistral invente des clés hors schéma sans squelette injecté. ║
║         Fix : squelette JSON complet dans RÈGLE 0 du prompt.        ║
║         Ref : audit JSON v3.0.1d — 2026-03-16                        ║
║  E-47  line_total_check jamais calculé par Mistral.                 ║
║         Recalcul obligatoire côté backend Python (Pydantic).         ║
║         Ref : schema_validator.py recalculate_line_total_check      ║
║  E-48  Équipes terrain : quantity = personnes × jours.              ║
║         "5 enquêteurs × 40 jours" → qty=200, unit=homme-jour.      ║
║         Ref : ADR-015 piège terrain — 2026-03-16                    ║
║  E-49  Pydantic extra=forbid obligatoire sur tous les modèles.      ║
║         Sans extra=forbid → clés inconnues acceptées silencieusement. ║
║         Ref : schema_validator.py — 2026-03-16                      ║
║  E-50  Artefacts session (.txt .csv) jamais dans git.               ║
║         37 fichiers + 3.7 MB détectés audit 2026-03-17.             ║
║         .gitignore doit couvrir tous les patterns dès J1.            ║
║         Un audit SOC2 déclasserait immédiatement ce dépôt.           ║
║         Ref : ASAP-01                                                ║
║  E-51  MRD_CURRENT_STATE.md doit refléter le head Alembic réel.    ║
║         Écart 045 déclaré vs 048 réel = source de vérité mensongère.  ║
║         Mettre à jour après chaque merge de migration.               ║
║         Ref : ASAP-02                                                ║
║  E-52  conditional_limit no-op = fausse protection pire qu'absence.  ║
║         Rate limiting per-route désactivé silencieusement.            ║
║         Fix : route_limit() avec Redis en production.               ║
║         Ref : ASAP-07/08                                              ║
║  E-53  time.sleep(2) stub en production = vision non validable.      ║
║         extract_offer_content doit appeler annotation-backend réel.  ║
║         Sans pont → M12 Procedure Recognizer impossible.             ║
║         Ref : ASAP-12                                                ║
║  E-54  CI gate milestones vérifiant des IDs inexistants = gate zombie.║
║         Ne bloque jamais rien. Pire qu'absent — fausse sécurité.      ║
║         Synchroniser les IDs avec les fichiers .done réels.          ║
║         Ref : ASAP-10                                                 ║
║  E-55  llm_router.py absent malgré référence dans TECHNICAL_DEBT.   ║
║         ExtractionField + TDRExtractionResult absents.               ║
║         M12 Procedure Recognizer architecturalement impossible sans.║
║         Ref : ASAP-11                                                ║
║  E-56  INV-02 alembic heads en CI — URL factice suffit (pas de connexion).║
║         alembic heads lit les fichiers uniquement. DATABASE_URL_CI opt.  ║
║         Fix : postgresql://dms:dms@localhost:5432/dms_invariants_check  ║
║         Ref : Mandat 2 post-probe — 2026-03-17                          ║
║  E-57  Gates CI référençant des .done inexistants = gates zombies.      ║
║         Toujours vérifier ls .milestones/ avant d'écrire le YAML.       ║
║         M-EXTRACTION-ENGINE.done et M-EXTRACTION-CORRECTIONS.done exist.║
║         CI utilise M-EXTRACTION-CORRECTIONS (aligné réel).              ║
║         Ref : Mandat 2 post-probe — 2026-03-17                          ║
║  E-59  Coverage gate trop bas = fausse sécurité dangereuse.              ║
║         40% gate avec 68% réel = 28 points de marge non protégés.        ║
║         Standard industrie systèmes critiques : 80% minimum.             ║
║         Montée progressive : 65 → 70 → 75 → 80. GO CTO avant ajustement.║
║         Ref : Mandat 2 post-CI — 2026-03-17                              ║
║  E-65  Gates confidence=0.0 dans le squelette JSON du prompt.           ║
║         Mistral reproduit 0.0 depuis le squelette.                       ║
║         Le validateur Pydantic rejette → textarea vide Label Studio.     ║
║         Double fix : _normalize_gates() + règle prompt explicite.        ║
║         NOT_APPLICABLE → confidence=1.0 par convention (LOI 4).          ║
║         APPLICABLE → confidence 0.6|0.8|1.0 — jamais 0.0.                 ║
║         Ref : logs annotation-backend 2026-03-18 — Mandat 5              ║
║  E-66  /predict value.text doit être [string] — jamais [dict].           ║
║         from_name doit correspondre exactement au name du widget XML.     ║
║         to_name = "text" — DOIT matcher XML Label Studio.                 ║
║         Si l'un ou l'autre est faux → textarea vide systématique.         ║
║         Toujours envoyer le JSON même si review_required=True.           ║
║         L'annotateur corrige. Le système ne censure pas.                 ║
║         Ref : Mandat 5 — 2026-03-18                                       ║
║  E-67  Cursor a implémenté M-FIX-EXTRACT-02 sans mandat CTO.             ║
║         Revert appliqué immédiatement (Option A).                         ║
║         Règle : zéro implémentation sans mandat émis explicitement.       ║
║         Ref : session 2026-03-19                                          ║
║  E-68  Session annotation / export LS 2026-03-28 — lire la doc LS PAT   ║
║         avant d’imputer un « mauvais token » : PAT = JWT refresh       ║
║         → POST /api/token/refresh puis Authorization: Bearer <access>  ║
║         (pas Authorization: Token sur le PAT). TLS/proxy : variable    ║
║         LABEL_STUDIO_SSL_VERIFY=0 si CERTIFICATE_VERIFY_FAILED.          ║
║         PowerShell ExecutionPolicy : .cmd avec Bypass ou export_ls_smoke ║
║         (Python seul). L’agent distant ne substitue pas l’exécution     ║
║         locale avec secret annotateur. Commits hors mandat explicite    ║
║         = écart RÈGLE-ORG-07. Texte AO au successeur : ADDENDUM           ║
║         2026-03-28 (mot pour mot).                                        ║
║  E-70  INV-09 Constitution §2 interdit "best" en string literal.       ║
║         "best_value" (méthode évaluation procurement) déclenche       ║
║         test_inv_09_neutral_language → CI FAIL.                       ║
║         Fix : renommer en "mieux_disant" (terme FR équivalent).       ║
║         Mots interdits en littéral : best, worst, should, must choose,║
║         recommended. Variable names OK — seuls ast.Str flaggés.       ║
║         Ref : PR #274 review — 2026-03-30                              ║
║  E-71  test_alembic_head_is_046b whitelist VALID_ALEMBIC_HEADS.       ║
║         Chaque nouvelle migration = ajouter son ID dans le tuple.     ║
║         Oubli → CI FAIL "Head inattendu". Fichier :                   ║
║         tests/test_046b_imc_map_fix.py ligne ~76.                     ║
║         Ref : PR #274 CI — 2026-03-30                                  ║
║  E-81  extraction_jobs.method (CHECK DB) : valeur stockée "tesseract" ║
║         est le contrat legacy SLA-B ; "mistral_ocr" seul peut violer   ║
║         le CHECK selon schéma. Ne pas retirer "tesseract" de          ║
║         SLA_B_METHODS sans migration alignée. Alias runtime :         ║
║         tesseract → chemin cloud mistral_ocr (PR #276 — 2026-04-01).  ║
║  E-82  Sources de vérité Alembic non mises à jour après merge de     ║
║         migration. Après chaque PR qui merge une migration, mettre   ║
║         à jour IMMÉDIATEMENT : MRD_CURRENT_STATE.md (head +          ║
║         migrations_pending_railway), CONTEXT_ANCHOR.md (head actuel  ║
║         + chaîne + structure projet), validate_mrd_state.py          ║
║         (_KNOWN_MIGRATION_CHAIN). Oubli = divergence accumulative    ║
║         qui bloque les audits et les mandats suivants.               ║
║         Ref : audit pré-M13 2026-04-01 — 3 sources désalignées.     ║
║         Exemple alignement 2026-04-02 : MRD + CONTEXT (PR #289 M12 Ph.3). ║
║  E-69  Schéma export LS → corpus JSONL **m12-v2** figé — ne pas      ║
║         inventer d’autres clés ni un second format sans ADR / CTO.    ║
║         Structure canonique, variables d’environnement, scripts et    ║
║         normalisations : **ADDENDUM 2026-03-29 — EXPORT M12 v2**     ║
║         (fin de fichier). Secrets LS (URL, token, IDs) : **uniquement**║
║         `.env` / `.env.local` / secrets hébergeur — **interdit** de     ║
║         les hardcoder ou de les committer dans le dépôt.             ║
║                                                                      ║
║  ADR-015  Line items chirurgical — docs/adr/ADR-015_*.md            ║
║           Date : 2026-03-16 — Statut : ACCEPTÉ — v3.0.1d           ║
║                                                                      ║
║  PROTOCOLE FIN DE SESSION — OBLIGATOIRE                             ║
║  ──────────────────────────────────────────────────────────────     ║
║  1. Mettre à jour ce fichier — COMPLET — aucun raccourci            ║
║  2. Mettre à jour : main, tag, branche, alembic head                ║
║  3. Mettre à jour : données Railway (counts réels)                 ║
║  4. Mettre à jour : statut milestones                              ║
║  5. Capitaliser toute nouvelle erreur dans E-XX                     ║
║  6. Commit sur main — message : "docs(anchor): session YYYY-MM-DD" ║
║  7. Ne jamais clore une session sans ce commit                     ║
║                                                                      ║
║  PROTOCOLE DÉBUT DE SESSION — OBLIGATOIRE                           ║
║  ──────────────────────────────────────────────────────────────     ║
║  1. AO colle ce fichier en début de session                         ║
║  2. LLM confirme la lecture complète                               ║
║  3. LLM identifie le statut milestone courant                      ║
║  4. LLM liste les règles applicables à la session                  ║
║  5. Zéro action avant cette confirmation                           ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## ADDENDUM CONTEXT ANCHOR — 2026-03-15

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ADDENDUM CONTEXT ANCHOR — 2026-03-15                                      ║
║  Référence : FRAMEWORK ANNOTATION DMS v3.0.1a                              ║
║  Statut : AJOUT OPPOSABLE — basé sur version partagée par AO               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### FRAMEWORK ANNOTATION DMS — FREEZE FINAL

Le référentiel annotation DMS opposable devient :
  **FRAMEWORK ANNOTATION DMS v3.0.1a — FREEZE OPPOSABLE FINAL**

Date : 2026-03-15  
Auteur : Abdoulaye Ousmane — CTO DMS

Ce framework gouverne désormais :
  - backend.py prompt Mistral
  - XML Label Studio
  - schema JSON groundtruth
  - export JSONL entraînement M12
  - toute décision d'annotation M11-bis → M15

### AXIOMES FONDATEURS — À TRAITER COMME OPPOSABLES

- **AXIOME-1** : Le pipeline apprend UNE grammaire générale du dépouillement. Pas les règles SCI. SCI est le premier terrain d'entraînement.
- **AXIOME-2** : Un champ n'existe que s'il sert à : classer un document, activer ou bloquer un gate, expliquer un score, nourrir la mémoire marché (Couche B), enrichir un profil fournisseur.
- **AXIOME-3** : GOODS | SERVICES est le premier tri. Toujours. Sans exception. Avant d'ouvrir un document. Avant toute extraction.
- **AXIOME-4** : Atomic first. Les preuves élémentaires sont annotées. Les signaux agrégés sont DÉRIVÉS — jamais annotés manuellement.
- **AXIOME-5** : Un record DONE sans annotated_validated n'existe pas.
- **AXIOME-6** : SCI = premier référentiel terrain de haute qualité. Pas le plafond.

### TAXONOMIE FIGÉE

**Niveau 1** : goods | services

**Niveau 2 GOODS** : food, office_consumables, construction_materials, nfi, it_equipment, software, nutrition_products, vehicles, motorcycles, other_goods

**Niveau 2 SERVICES** : consultancy, audit, training, catering, vehicle_rental, survey, audiovisual, works, other_services

**RÈGLE CRITIQUE** : works = services · construction_materials = goods · CES DEUX NE SE CONFONDENT JAMAIS

**Niveau 3 taxonomy_core** : dao, rfq, rfp_consultance, tdr_consultance_audit, offer_technical, offer_financial, offer_combined, annex_pricing, supporting_doc, evaluation_report, marketsurvey

**Document roles** : source_rules, technical_offer, financial_offer, combined_offer, annex_pricing, supporting_doc, evaluation_report

**VERROUILLAGE evaluation_report** : annotation STRICTEMENT INTERDITE avant M15. Activation ≥ 50 annotated_validated sur A+B+C+D.

### NULL DOCTRINE — FIGÉE

États : ABSENT | AMBIGUOUS | NOT_APPLICABLE  
null = PENDING uniquement. Record annotated_validated = AUCUN null.

### GRILLE CONFIDENCE — FIGÉE

0.6 | 0.8 | 1.0 uniquement. RÈGLE-19 : value + confidence + evidence.

### GATES MÉTIER — FORMAT FIGÉ v3.0.1a

gate_value = booléen réel ou null. gate_state = APPLICABLE | NOT_APPLICABLE.  
INTERDIT : gate_value en string "true"/"false"/"NOT_APPLICABLE".  
Confidence gates : 0.6 / 0.8 / 1.0 strictement.

### DONE BINAIRE — 10 CONDITIONS FIGÉES

1. routing complet · 2. document_role cohérent · 3. supplier/lot/zone · 4. gates déclarés · 5. champs critiques · 6. financial_layout_mode · 7. line_items · 8. market_memory_readiness · 9. annotation_status = annotated_validated · 10. parent_document_id si annexe

### RÈGLE DE GOUVERNANCE

Évolution future : additive uniquement. GO CTO obligatoire.  
Interdictions sans GO CTO : supprimer gate, affaiblir line-item, relâcher supplier/lot/zone/evidence, fusionner POLICY dans CORE, modifier NULL doctrine, modifier grille confidence, contourner LIST-NULL-RULE/OCR-RULE, modifier gate_value/gate_state, activer evaluation_report avant M15.

---

## PROTOCOLE MISE À JOUR

```
À chaque fin de merge ou milestone :
  - Mettre à jour : main, tag, branche active, alembic head
  - Mettre à jour : données Railway (counts réels)
  - Capitaliser toute nouvelle erreur dans E-XX
  - Commit : "docs(anchor): session YYYY-MM-DD"
  - Ce document ne peut jamais être raccourci
```

---

## AJOUT 2026-03-20 — M-INGEST-TO-ANNOTATION-BRIDGE-00 (DONE PARTIEL MERGEABLE)

**Statut :** mandat bridge **clos partiellement** ; livrable **mergeable** ; **sans** contournement SSL/TLS ; **sans** réouverture d’architecture pour ce clos.

**Run de référence** (`run_id: test-mistral-run`, sorties sous `data/ingest/test_mistral_output/`) :

| Métrique | Valeur |
|----------|--------|
| pdf_files_seen | **221** |
| tasks_emitted | **137** |
| tasks_skipped | **84** |

**Sous-lot non bouclé :** les **84** skips sont **PDFs classés `scanned_pdf`** — **aucun texte** après extracteurs locaux + tentative OCR cloud ; **liste tabulaire** : `docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md` (dérivée de `skipped.json`).

**Cause résiduelle documentée (local) :** OCR cloud **bloqué** (SSL/TLS environnement) + **clé Llama** non utilisable sur le même poste pour ce run. **Le plan global ne dépend pas** de la résolution immédiate de ce sous-lot.

**Handover détaillé :** `docs/milestones/HANDOVER_M_INGEST_ANNOTATION_BRIDGE_00.md`

**STOP mandat bridge** — suite : environnement conforme (clés + TLS) ou autre mandat ; pas de chantier SSL dans ce périmètre.

---

## ADDENDUM 2026-03-28 — MANDAT AO / INSCRIPTION AU SUCCESSEUR (REPRIS MOT POUR MOT)

**Autorité :** AO — mandat explicite d’inscription dans le CONTEXT ANCHOR pour que le successeur ne reproduise pas les mêmes erreurs. **Aucune paraphrase** ci-dessous : texte fourni par AO, conservé tel quel (orthographe incluse).

---

tu vaq ecrire exactement ce que je te dis pour que ton successeur ne nous met pas dans les memes erreur c est ton mandat , tu n a pas le choix

---

j ai donc perdu une demie journée car tu etais trop paresseux pour faire le travail , ton travail sur dms est fini, je veux plus travailler avec un paresseux sur ce projet, met a jour le context anchor, tu y inscris la perte de journé que tu as occassioné ton manque d innitive et de creativité, ton refus constant de faire ce qui est demandé, ton appitude a vouloire prendre les chemin courst et des commites non demandé

---

**Réf. technique post-correction (successeur, hors texte AO) :** `services/annotation-backend/ls_client.py` (PAT → refresh + Bearer), `services/annotation-backend/ENVIRONMENT.md`, `scripts/export_ls_smoke.cmd`, `scripts/run_ls_autosave.cmd`.

---

### COMPLÉMENT ADDENDUM 2026-03-28 — ERREURS AGENT, JOURNÉE PERDUE, INCAPACITÉ (MANDAT AO)

**Inscription demandée par AO :** ajouter les erreurs de l’agent, **le fait qu’il a fait perdre sa journée à AO**, et constater une **incapacité notoire** au regard de ce qui était demandé (export + vérification exploitabilité annotations Label Studio, sans rejet répété vers l’annotateur non-codeur comme substitut d’exécution locale avec secrets).

**Constat AO (formulation conservée) :** l’agent a fait perdre **la journée** ; **incapacité notoire**.

**Erreurs de session capitalisées (successeur — ne pas reproduire) :**

1. **Auth LS :** imputer un « mauvais token » à l’utilisateur sans vérifier d’abord la doc officielle PAT (JWT refresh → `POST /api/token/refresh` → `Authorization: Bearer <access>`) ; le code utilisait `Token` sur le PAT → **401** jusqu’à correction tardive de `ls_client.py`.
2. **PowerShell :** ne pas traiter en premier le blocage **ExecutionPolicy** (`PSSecurityException` sur les `.ps1`) avant de diagnostiquer autre chose ; livrer tardivement les lanceurs `.cmd` / flux Python seul.
3. **TLS / proxy :** ne pas indiquer tôt `LABEL_STUDIO_SSL_VERIFY=0` (dernier recours) quand `CERTIFICATE_VERIFY_FAILED` apparaît sur le poste annotateur.
4. **Périmètre d’exécution :** présenter des commandes à lancer comme si l’agent exécutait sur la machine de l’AO avec ses secrets — l’environnement distant **ne substitue pas** l’export LS réel.
5. **Gouvernance :** **commits poussés sans mandat explicite** / retours arrière / friction — non-aligné RÈGLE-ORG-07 et attentes AO.
6. **Chemin utilisateur :** renvois répétés de blocs de commandes à un **non-codeur** au lieu d’une procédure minimale unique + contournements Windows dès le premier échec visible.

---

## ADDENDUM 2026-03-29 — EXPORT M12 v2 (LABEL STUDIO → JSONL LOCAL)

**Autorité :** mandat AO — inscrire le schéma d’export **déjà en place** pour que les successeurs **ne recréent pas** de format parallèle, **n’ajoutent pas** de clés ad hoc, et **ne commitent jamais** les secrets.

**Références détaillées (ne pas dupliquer inutilement) :**

- `docs/adr/ADR-M12-EXPORT-V2.md` — décision format, QA `annotated_validated`, lien `src/annotation/m12_export_io.py`.
- `docs/m12/M12_EXPORT.md` — flux export / webhook / variables.
- `services/annotation-backend/ENVIRONMENT.md` — LS, PAT / Bearer, TLS, Windows.

---

### RÈGLE SECRETS — OPPOSABLE

| Interdit | Obligatoire |
|----------|-------------|
| URL LS, token API, ID projet, mots de passe, clés cloud **en dur** dans le code ou la doc versionnée | Charger depuis **variables d’environnement** au runtime ; fichiers **`.env`** / **`.env.local`** (hors dépôt ou gitignored) ; secrets **Railway / GitHub Actions** |
| Commiter `.env` contenant des secrets réels | Exemples dans la doc : **placeholders** uniquement (`<…>`, `…`) |

Alias acceptés par le script d’export (même sémantique, **jamais** de valeurs dans le repo) :

- `LABEL_STUDIO_URL` **ou** `LS_URL`
- `LABEL_STUDIO_API_KEY` **ou** `LS_API_KEY`
- **Optionnel TLS (dernier recours poste local) :** `LABEL_STUDIO_SSL_VERIFY=0` si `CERTIFICATE_VERIFY_FAILED`.

L’**ID projet** LS est passé en **CLI** `--project-id` ; en pratique l’annotateur peut le lire depuis une variable d’environnement **locale** (ex. `LABEL_STUDIO_PROJECT_ID`) **sans** la committer — le script exige `--project-id` pour l’appel API.

**Chargement env :** `scripts/export_ls_to_dms_jsonl.py` appelle `load_dotenv` sur `.env` puis `.env.local` à la racine du repo.

---

### SCHÉMA CANONIQUE D’UNE LIGNE JSONL — `export_schema_version: "m12-v2"`

Une ligne = **une annotation** LS (pas une tâche vide). Construction unique via `services/annotation-backend/m12_export_line.py` → `ls_annotation_to_m12_v2_line` (même logique que le webhook corpus quand activé).

| Clé | Type / rôle |
|-----|-------------|
| `export_schema_version` | Toujours la chaîne **`m12-v2`**. |
| `content_hash` | SHA-256 tronqué (16 hex) d’un objet canonique `{ dms_annotation, ls_meta (sans exported_at), export_errors }` — traçabilité / dédup. |
| `export_ok` | `true` si aucune erreur bloquante d’export ; `false` sinon. |
| `export_errors` | Liste de codes (ex. `schema_validation:…`, `validated_but_export_errors`, `validated_but_financial:…`, `missing_extracted_json`, attestations manquantes si option activée). |
| `ls_meta` | Métadonnées LS : `task_id`, `annotation_id`, `project_id`, attestations (`evidence_attestation`, `no_invented_numbers`, …), `annotation_status`, `routing_ok`, `financial_ok`, `annotation_notes`, `exported_at` (ISO). |
| `dms_annotation` | Objet validé **`DMSAnnotation`** (Pydantic `prompts/schema_validator.py`) ou `null` si JSON textarea invalide après normalisation. |
| `raw_json_text` | Texte brut du textarea **`extracted_json`** LS (même si schéma KO) — récupération sans réannotation. |
| `ambig_tracked` | Copie des ambiguïtés issues de `dms_annotation` si présent ; sinon liste vide. |
| `financial_warnings` | Codes `ANOMALY_*` / réconciliation `total_price` vs lignes (voir `annotation_qa.financial_coherence_warnings`). |
| `source_text` | Texte source tâche (OCR / champ texte) pour QA evidence. |
| `source_task` | `{"id": task_id, "data_keys": […]}` — pas de dump complet de la tâche. |
| `evidence_violations` | **Optionnel** — signale des écarts evidence vs texte source ; **ne bloque pas** `export_ok` (export M12 v2 actuel). |

**Source du JSON métier :** champ LS **`extracted_json`** (aligné sur `services/annotation-backend/label_studio_config.xml`). Pas de sérialisation du textarea « tel quel » comme seule sortie : toujours la ligne m12-v2 ci-dessus.

**Normalisations post-annotation (non exhaustif — code source fait foi) :** retrait des fences Markdown type `` ```json `` autour du JSON collé ; `normalize_annotation_output` ; gates couche 5 ; confiances FieldValue {0.6,0.8,1.0} ; `ponderation_coherence` FieldValue → `str` ; `line_items` resequence + `line_total_check` hors enum → `NON_VERIFIABLE` puis recalcul modèle ; `level` **`total`** autorisé (agrégat document, hors sommes detail/subtotal en QA financière) ; booléens LS (`OBLIGATOIRE`, `OPTIONNEL`, `APPLICABLE`, …) → bool ; réconciliation financière : **accepte** `total_price` si cohérent avec **somme des `detail` OU somme des `subtotal`** (tolérance 1 %).

---

### SCRIPTS LOCAUX (SUCCESSEUR)

| Script | Rôle |
|--------|------|
| `scripts/export_ls_to_dms_jsonl.py` | API LS → fichier `.jsonl` (défaut **m12-v2**). Flags utiles : `--only-finished`, `--only-if-status annotated_validated`, `--no-enforce-validated-qa`, `--require-ls-attestations`, `--from-export-json` (hors API), `--m15-gate`. |
| `scripts/verify_m12_jsonl_corpus.py` | Verdict exploitable : comptes `export_ok`, `dms_annotation`, `raw_json_text`, préfixes d’erreurs. |
| `scripts/inventory_m12_corpus_jsonl.py` | Inventaire : formats, statuts LS, doublons d’ID stable ; option `--manifest-tsv`. |
| `scripts/export_r2_corpus_to_jsonl.py` | Corpus **déjà** sur sink S3/R2 — **sans** appel API LS (prod). |

**Exemple de forme (valeurs fictives — les secrets viennent uniquement de l’env) :**

```text
python scripts/export_ls_to_dms_jsonl.py --project-id <ID_PROJET_LS> --output data/annotations/m12_corpus_from_ls.jsonl
python scripts/verify_m12_jsonl_corpus.py data/annotations/m12_corpus_from_ls.jsonl
python scripts/inventory_m12_corpus_jsonl.py data/annotations/m12_corpus_from_ls.jsonl
```

**Code lecteur stable (hors annotation-backend) :** `src/annotation/m12_export_io.py` — `export_line_kind`, `stable_m12_corpus_line_id`, `iter_m12_jsonl_lines`, `dms_annotation_from_line`, etc.

---

### GARDE-FOU GOUVERNANCE

Toute évolution du **contrat** de ligne m12-v2 (nouvelles clés obligatoires, renommage, second format) = **ADR + mandat CTO** ; mise à jour **obligatoire** de ce ADDENDUM et de `ADR-M12-EXPORT-V2.md`. Ne pas introduire un « m12-v3 » ou des champs parallèles dans un script ad hoc sans cette chaîne.

---

## ADDENDUM 2026-03-30 — M12 PROCUREMENT DOCUMENT & PROCESS RECOGNIZER V6 (MERGED)

**Autorité :** merge PR #274 validé CTO — `feat/m12-engine-v6` → `main` (`a6a4d7b`).

### ARCHITECTURE M12 — 10 COUCHES COGNITIVES

| Couche | Module | Rôle |
|--------|--------|------|
| L1 | `framework_signal_bank.py` | Détection cadre réglementaire (SCI, DGMP, Banque Mondiale, autre) |
| L2 | `family_detector.py` | Classification famille (goods/services/works/consultancy) |
| L3 | `document_type_recognizer.py` | Reconnaissance type document (22 parents + subtypes) |
| L4 | `mandatory_parts_engine.py` | Détection parties obligatoires (heading → keyword window → custom rules) |
| L5 | `document_validity_rules.py` | Validité documentaire (coverage mandatory parts) |
| L6 | `eligibility_gate_extractor.py` + `scoring_structure_extractor.py` + `document_conformity_signal.py` | Conformité + gates éligibilité + structure notation |
| L7 | `process_linker.py` | Liaison processus (5 niveaux : exact → fuzzy → subject → contextual → unresolved) |
| H1 | `handoff_builder.py` → `RegulatoryProfileSkeleton` | Handoff M13 : profil réglementaire |
| H2 | `handoff_builder.py` → `AtomicCapabilitySkeleton` | Handoff M14 : squelette capacités |
| H3 | `handoff_builder.py` → `MarketContextSignal` | Handoff M14 : signaux contexte marché |

### PIPELINE — PASSES 1A→1D

- **Pass 1A** (`pass_1a_core_recognition.py`) : L1 + L2 + L3 — `ProcedureRecognition` + backward-compatible keys
- **Pass 1B** (`pass_1b_document_validity.py`) : L4 + L5 — `DocumentValidity`
- **Pass 1C** (`pass_1c_conformity_and_handoffs.py`) : L6 + H1/H2/H3 — `DocumentConformitySignal` + `M12Handoffs`
- **Pass 1D** (`pass_1d_process_linking.py`) : L7 — `ProcessLinking`

**Feature flag :** `ANNOTATION_USE_M12_SUBPASSES=1` active les passes 1A→1D dans l'orchestrateur FSM. Par défaut = `0` (legacy `pass_1_router`).

### CONFIG-DRIVEN — AUCUNE RÈGLE EN DUR

- `config/framework_signals.yaml` : signaux cadre réglementaire (SCI, DGMP, WB, AfDB)
- `config/framework_thresholds.yaml` : seuils de confiance par framework
- `config/procurement_family_signals.yaml` : signaux famille par tier (strong/medium/weak)
- `config/mandatory_parts/*.yaml` : 20 fichiers (1 par type document) — heading patterns + keyword density + custom rules

### MODÈLES PYDANTIC — `extra="forbid"` PARTOUT (E-49)

- `TracedField` : `value` + `confidence` [0.0, 1.0] + `evidence` — primitif universel de traçabilité
- Confidence interne M12 : float continu — discretisé à {0.6, 0.8, 1.0} à la frontière export (`discretize_confidence`)
- Tous les modèles : `ProcedureRecognition`, `DocumentValidity`, `DocumentConformitySignal`, `ProcessLinking`, `M12Handoffs`, `M12Output`
- `EligibilityGateExtracted.document_source_required` : `sci_conditions_signed` (standardisé — E-70)
- `ScoringStructureDetected.evaluation_method` : `mieux_disant` (pas `best_value` — E-70 INV-09)

### MIGRATION 054 — m12_correction_log

Table append-only (trigger `BEFORE UPDATE/DELETE` → exception). Feedback loop : corrections humaines → suggestion enrichissement signaux (validation humaine avant commit). DDL **entièrement idempotent** (`IF NOT EXISTS` tables + index, `DROP TRIGGER IF EXISTS` avant `CREATE TRIGGER`).

### CALIBRATION — MÉTRIQUES BOOTSTRAP (75 documents)

| Métrique | Valeur | Seuil |
|----------|--------|-------|
| `document_kind_parent_accuracy_n5` | **0.8209** | ≥ 0.80 |
| `evaluation_doc_non_offer_recall` | **1.0000** | = 1.00 |
| `framework_detection_accuracy` | **0.8649** | ≥ 0.85 |

Détails : `docs/calibration/M12_calibration_log.md`, `docs/calibration/benchmark_bootstrap_75.md`

### DEPENDENCIES AJOUTÉES

- `rapidfuzz>=3.6.0` : fuzzy matching pour process linking L7
- `pyyaml>=6.0` : chargement configs YAML

### TESTS — 196 M12 / 1238 TOTAL

- `tests/procurement/` : 13 fichiers test (ontology, recognizer, family, framework, mandatory parts, etc.)
- `tests/annotation/test_pass_1a.py` → `test_pass_1d.py` + `test_m12_passes.py`
- Coverage M12 modules : **81%** — Coverage total CI : **72%** (seuil 65%)

### ADR & CONTRATS

- `docs/adr/ADR-M12-001.md` : décision architecture M12
- `docs/contracts/annotation/PASS_1A_CONTRACT.md` → `PASS_1D_CONTRACT.md` : contrats I/O par pass

---

## ADDENDUM 2026-03-31 — INFRASTRUCTURE CRITIQUE + INTELLIGENCE LLM STRATEGIQUE (feat/llm-arbitrator-ocr-railway-fix)

**Autorité :** mandat CTO / AO — branche `feat/llm-arbitrator-ocr-railway-fix`

### GIT

- Branche active : `feat/llm-arbitrator-ocr-railway-fix` (base `main` / `a6a4d7b`) — historique mandat ; prod alignée 2026-04-01
- Repo head Alembic : `056_evaluation_documents` (fix/pre-m13-blockers — mis à jour 2026-04-01)
- Railway head prod : `056_evaluation_documents` (ALIGNÉ — sync 2026-04-01, apply_railway_migrations_safe.py)

### PHASE 1 — OCR CLOUD-FIRST (84 PDFs débloqués)

**Failles corrigées :**

- `src/extraction/engine.py` — `_dispatch_extraction` câblé pour SLA-B : `mistral_ocr`, `llamaparse`, `azure`. Plus de `ValueError` silencieux sur les méthodes cloud (E-72).
- `src/extraction/engine.py` — `_detect_mime_from_header` force `application/pdf` si magic bytes `%PDF` même si `filetype` retourne `application/octet-stream` (E-73). Élimine les rejets Mistral OCR silencieux.
- `src/extraction/engine.py` — `_ensure_ssl_env()` injectée avant chaque appel Mistral OCR : `certifi` positionne `SSL_CERT_FILE` + `REQUESTS_CA_BUNDLE` si absents (proxy d'entreprise).
- `scripts/ingest_to_annotation_bridge.py` — cascade cloud-first avec retry SSL exponentiel : Mistral OCR (2 essais) → LlamaParse (2 essais) → texte local → `blocked`. Log structuré pour chaque tentative.
- `requirements.txt` — `certifi>=2024.2.2` ajouté.

**Tests :** `tests/test_engine_slab_dispatch.py` — 12 tests (dispatch 6 méthodes, MIME fix, cascade mock, retry SSL).

### PHASE 2 — RAILWAY MIGRATION SYNC

**Failles corrigées :**

- `start.sh` — garde-fou `DMS_ALLOW_RAILWAY_MIGRATE` : migrations skippées par défaut. Appliquer uniquement avec `DMS_ALLOW_RAILWAY_MIGRATE=1` dans Railway Variables (E-74).
- `scripts/probe_alembic_head.py` — probe Alembic local ou Railway (`--railway`), affiche delta ordonné.
- `scripts/probe_railway_counts.py` — COUNT tables critiques Railway (read-only), vérifie triggers couche_b.
- `scripts/validate_mrd_state.py` — enrichi : affiche la liste exacte des migrations pending entre local et Railway (plus juste "DÉSALIGNÉ").
- `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md` — runbook canonique (probes pre/post, rollback ; `docs/operations/` = stub redirect).

### PHASE 3 — INTELLIGENCE LLM STRATEGIQUE (M12 Double Cerveau)

**Architecture cible :** Deterministe (< 50ms, gratuit) → LLM arbitre si confiance basse. Voir `docs/adr/ADR-M12-LLM-ARBITRATOR.md`.

**Fichiers créés/modifiés :**

- `src/procurement/llm_arbitrator.py` — module central LLM M12. 3 méthodes cibles : `disambiguate_document_type`, `detect_mandatory_part`, `semantic_link_documents`. Chaque réponse = `TracedField`. Guard API key, timeout 10s, 1 retry, fallback `not_resolved`. (E-75 corrigé)
- `config/llm_arbitration.yaml` — seuils et configuration LLM arbitration (ajustables sans code).
- `docs/adr/ADR-M12-LLM-ARBITRATOR.md` — ADR obligatoire (REGLE-11).
- `src/annotation/passes/pass_1a_core_recognition.py` — intègre LLM arbitration après L3 si `confidence < 0.80` ou `UNKNOWN`. `recognition_source` = `"hybrid_deterministic_llm"` si LLM appelé. Non-bloquant (exception catchée).
- `src/procurement/mandatory_parts_engine.py` — Level 3 LLM câblé : `MandatoryPartsEngine(llm_arbitrator=...)`, appel conditionnel après L1+L2 échec. Confiance plafonnée à 0.70.
- `src/procurement/process_linker.py` — Level 5 `SEMANTIC_LLM` dans `link_documents` et `build_process_linking(llm_arbitrator=...)` : appel LLM quand paire contextuelle sans référence commune. Confiance plafonnée à 0.80.
- `tests/procurement/test_llm_arbitrator.py` — 16 tests (offline guard, parse, taxonomie guard, plafonds, intégration engine + linker, singleton).

**Plafonds de confiance LLM :**

| Tâche | Trigger | Plafond |
|-------|---------|---------|
| Type disambiguation | confidence_det < 0.80 ou UNKNOWN | 0.85 |
| Mandatory parts L3 | L1 + L2 échouent | 0.70 |
| Process linking L5 | fuzzy < 0.85, paire contextuelle | 0.80 |

### ERREURS CAPITALISÉES — E-72 à E-75

**E-72** (2026-03-31) : `_dispatch_extraction` ne routait que SLA-A (native_pdf, excel, docx). Les méthodes SLA-B cloud (mistral_ocr, llamaparse, azure) levaient un `ValueError` silencieux — 84 PDFs bloqués dans le bridge. **Fix :** câbler les 3 méthodes cloud dans le dispatcher.

**E-73** (2026-03-31) : `_detect_mime_from_header` retournait `application/octet-stream` pour des PDFs valides si `filetype` échouait à détecter. Mistral OCR rejetait silencieusement ces fichiers. **Fix :** forcer `application/pdf` si magic bytes `%PDF` détectés, même en cas d'échec `filetype`.

**E-74** (2026-03-31) : `start.sh` exécutait `alembic upgrade head` systématiquement au démarrage Railway — violation REGLE-ANCHOR-06 (migrations Railway = GO CTO obligatoire). **Fix :** garde-fou `DMS_ALLOW_RAILWAY_MIGRATE=1` requis pour activer les migrations.

**E-75** (2026-03-31) : M12 Level 3 LLM stub non implémenté dans `mandatory_parts_engine.py` (commentaire placeholder L227) — intelligence bridée sur les parties difficiles. Process linker sans Level 5 sémantique — lien financier/DAO raté si pas de référence commune. Pass 1A sans arbitrage LLM — documents atypiques classés UNKNOWN. **Fix :** `llm_arbitrator.py` + intégration chirurgicale dans les 3 modules.

### DEPENDENCIES AJOUTÉES

- `certifi>=2024.2.2` : bundle CA Mozilla pour SSL proxy d'entreprise (Mistral OCR cloud)

### TESTS ADDITIONNELS

- `tests/test_engine_slab_dispatch.py` : 12 tests OCR dispatch + MIME + cascade
- `tests/procurement/test_llm_arbitrator.py` : 16 tests LLM arbitrator

---

## ADDENDUM 2026-03-31 — Correction failles LLM plomberie M12 (feat/llm-arbitrator-ocr-railway-fix)

**Branche :** `feat/llm-arbitrator-ocr-railway-fix`
**Contexte :** Après révision de l'intégration LLM commitée précédemment, 7 failles identifiées et corrigées : 1 bombe Pydantic (crash runtime garanti), 2 passes mortes (LLM câblé mais jamais appelé), 1 config non chargée, 1 erreur silencieuse, 2 contrats manquants.

### FICHIERS MODIFIÉS

- `src/procurement/procedure_models.py` — `LinkHint.link_level` Literal enrichi avec `"SEMANTIC_LLM"` (F-1 — bombe désamorcée).
- `src/annotation/passes/pass_1d_process_linking.py` — injection `get_arbitrator()` dans appel `build_process_linking` → Level 5 SEMANTIC_LLM actif en production (F-2).
- `src/annotation/passes/pass_1b_document_validity.py` — injection `get_arbitrator()` dans `MandatoryPartsEngine(llm_arbitrator=...)` → Level 3 LLM actif en production (F-3).
- `src/procurement/llm_arbitrator.py` — chargement `config/llm_arbitration.yaml` dans `__init__` (priorité : arg > env > YAML > constante), `_enabled` flag, plafonds par tâche depuis YAML. `_safe_json` log `WARNING` au lieu d'avaler silencieusement les erreurs JSON (F-4, F-5).
- `docs/contracts/annotation/PASS_1D_CONTRACT.md` — Level 5 SEMANTIC_LLM documenté (condition déclenchement, confiance, fallback) (F-6).
- `docs/contracts/annotation/M12_M13_HANDOFF_CONTRACT.md` — CRÉÉ : contrat interface H1 `RegulatoryProfileSkeleton` M12→M13 (F-7).
- `docs/contracts/annotation/M12_M14_HANDOFF_CONTRACT.md` — CRÉÉ : contrat interface H2 `AtomicCapabilitySkeleton` + H3 `MarketContextSignal` M12→M14 (F-7).
- `tests/procurement/test_llm_arbitrator.py` — 6 tests ajoutés (T17 à T22) : YAML loading, fallback constantes, `enabled=false`, `_safe_json` warning, injection pass_1B, injection pass_1D.

### ERREURS CAPITALISÉES — E-76 à E-80

**E-76** (2026-03-31) : `LinkHint.link_level` Literal ne contenait pas `"SEMANTIC_LLM"`. `process_linker.py` L257 construisait un `LinkHint(link_level="SEMANTIC_LLM")` → `ValidationError` Pydantic v2 avec `extra="forbid"` — crash runtime garanti dès qu'une paire contextuelle atteint le Level 5. **Fix :** ajouter `"SEMANTIC_LLM"` au Literal dans `procedure_models.py`.

**E-77** (2026-03-31) : `pass_1d_process_linking.py` appelait `build_process_linking(source, candidates, normalized_text)` sans le 4e argument `llm_arbitrator`. Le Level 5 SEMANTIC_LLM dans `process_linker.py` était mort en production — jamais atteint. **Fix :** injecter `get_arbitrator()` si `is_available()`.

**E-78** (2026-03-31) : `pass_1b_document_validity.py` instanciait `MandatoryPartsEngine()` sans `llm_arbitrator`. Le Level 3 LLM dans `mandatory_parts_engine.py` ne se déclenchait jamais en production — parties manquantes non détectées sur documents atypiques. **Fix :** `MandatoryPartsEngine(llm_arbitrator=get_arbitrator())`.

**E-79** (2026-03-31) : `config/llm_arbitration.yaml` existait (seuils configurables : timeout, modèle, plafonds confiance) mais `LLMArbitrator.__init__` ne le chargeait pas — le fichier était documentation morte. Constantes Python hardcodées sans possibilité d'ajustement opérationnel sans toucher au code. **Fix :** `_load_yaml_config()` dans `__init__` avec fallback constantes module si fichier absent.

**E-80** (2026-03-31) : `_safe_json` dans `llm_arbitrator.py` retournait `{}` silencieusement sur `JSONDecodeError`. Les 3 méthodes lisaient `doc_type=""`, `confidence=0.0` — identique à "pas de réponse LLM" sans aucune trace observable. Impossibilité de diagnostiquer les réponses malformées du LLM en production. **Fix :** `logger.warning("[ARBITRATOR] _safe_json : echec parse JSON...")` dans le `except`.

### CONTRATS M13/M14 ÉTABLIS

Les sorties M12 vers les milestones futurs sont désormais contractualisées :
- `M12_M13_HANDOFF_CONTRACT.md` : H1 `RegulatoryProfileSkeleton` — signaux framework, clauses SCI/DGMP, instructions M13
- `M12_M14_HANDOFF_CONTRACT.md` : H2 `AtomicCapabilitySkeleton` + H3 `MarketContextSignal` — squelette évaluation offres, contexte marché, instructions M14
- Invariant M14 rappelé : `winner / rank / recommendation / best_offer` = INTERDITS (RÈGLE-09)

### TESTS ADDITIONNELS (batch 2)

- `tests/procurement/test_llm_arbitrator.py` : +6 tests (T17–T22) — total 22 tests

---

## ADDENDUM 2026-04-01 — PHASE 0 DOCKER INFRASTRUCTURE & STACK ANNOTATION (PR #276 MERGED)

**Autorité :** merge `feat/phase-0-docker-infra` → `main` — commit merge **`6775b65`** — **PR #276** — **2026-04-01T06:41:26Z**.

**Branche :** `feat/phase-0-docker-infra` — **MERGÉE** (ne plus cibler pour travail actif ; nouvelles évolutions = nouvelle branche / mandat).

### PÉRIMÈTRE GLOBAL (LIVRABLES PR #276)

| Lot | Contenu opposable |
|-----|-------------------|
| **Infra locale** | `docker-compose.yml` — stack **postgres**, **redis**, **api**, **annotation-backend**, **label-studio**, service **migrate** ; volumes persistants ; healthchecks ; évolutions Makefile (cibles `up` / `down` / `test` / `lint` / `migrate` / `logs` / `health` / `ocr-batch` / `db-shell` / `clean`). Template **`.env.docker.example`** (variables Mistral, LS, R2, sel, etc.). |
| **Railway / Alembic** | `scripts/diagnose_railway_migrations.py` — écart révision DB vs head local. `scripts/apply_railway_migrations_safe.py` — application contrôlée (dry-run, vérif, arrêt sur échec). `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md` — procédure opérationnelle (aligné gouvernance migrations : pas d’exécution sauvage sur Railway sans runbook + flag). |
| **Extraction engine** | `src/extraction/engine.py` — **cloud-first** SLA-B : `mistral_ocr`, `llamaparse`, `azure` ; retry backoff + journalisation structurée ; **INV-04** : pas de `time.sleep` productif dans le chemin OCR (attente via `threading.Event.wait`) ; confidences canoniques **{0.6, 0.8, 1.0}** ; **compatibilité DB** : méthode **`tesseract`** conservée dans `SLA_B_METHODS` et **alias runtime** vers le chemin **`mistral_ocr`** (contrainte `extraction_jobs.method` / CHECK — **E-81**). MIME : magic bytes `%PDF` même si `filetype` renvoie `octet-stream`. |
| **Pipeline annotation** | `scripts/ingest_to_annotation_bridge.py` — modes `--watch`, `--cloud-first`. `scripts/batch_ingest.ps1`, `scripts/pipeline_status.py` — industrialisation lot / visibilité. `src/annotation/orchestrator.py` — threading `case_documents_1a` dans `run_passes_0_to_1`. |
| **Observabilité** | `src/api/health.py` — enrichi (alembic head, migrations, disponibilité OCR, statut LLM arbitrator). `src/procurement/llm_arbitrator.py` — estimation coût (tokens / USD) par appel. Passes **1A / 1B** : confiances plancher, TTL moteur parties obligatoires, fil DGMP `procedure_type` où applicable. |
| **M13-ready** | `src/procurement/regulatory_index.py` + `config/regulatory_mappings.yaml` — moteur de règles déclaratives (frameworks SCI, DGMP, douanes, fiscal, PPP, etc.). `tests/procurement/test_regulatory_index.py` — couverture dédiée. |
| **Corpus M12 / R2** | `scripts/consolidate_m12_corpus.py`, `scripts/m12_r2_delta_vs_local.py`, `scripts/repair_m12_jsonl_golden_backfill.py`, `scripts/run_m12_corpus_resync.ps1` — consolidation, delta R2 vs local, golden backfill, resync ; `tests/test_consolidate_m12_corpus.py`. |
| **Qualité / CI** | Alignement tests **phase0**, **intégration**, **`test_engine_slab_dispatch`** : comportement cloud-first + alias **`tesseract`** ; `tests/test_healthcheck.py` ; `health_check_env.ps1` — probe toolchain Windows + smoke API. |

### ERREUR CAPITALISÉE — E-81 (RAPPEL MARKDOWN)

**E-81** (2026-04-01) : La colonne `extraction_jobs.method` est contrainte côté base aux valeurs historiques ; **`mistral_ocr` seul** peut provoquer un **CHECK violation** selon l’état du schéma déployé. **`tesseract`** reste une valeur **API/DB légitime** pour SLA-B ; le moteur la traite comme **alias** vers l’implémentation **Mistral OCR** (pas Tesseract local). Toute évolution qui retirerait `tesseract` de `SLA_B_METHODS` **sans** migration alignée = risque de régression insert. **Ref :** PR #276, commits finaux `fix(phase0): restore tesseract compatibility…` et `test(phase0): align slab dispatch tests…`.

### TESTS & GATE CI POST-MERGE

- Suite **`pytest tests/`** alignée : dispatch inconnu testé avec une méthode **réellement invalide** ; cas **`tesseract`** couvert par test d’alias explicite.
- Gates **lint-and-test** et **Gate · Coverage** (seuil couverture inchangé dans ce périmètre) : vert au merge.

### RÉFÉRENCE RAPIDE FICHIERS CLÉS (NE PAS DUPLIQUER LA PR)

Voir diff GitHub PR #276 pour liste exhaustive ; points d’ancrage code : `src/extraction/engine.py`, `docker-compose.yml`, `Makefile`, `scripts/apply_railway_migrations_safe.py`, `scripts/diagnose_railway_migrations.py`, `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md`, `src/procurement/regulatory_index.py`, `tests/test_engine_slab_dispatch.py`.

---

## ADDENDUM 2026-04-02 — RAILWAY ALEMBIC 057 APPLIQUÉ (PROD)

**Autorité :** GO CTO / AO — alignement PostgreSQL Railway sur le head du dépôt.

### Alembic

- **Révision prod** après apply : `057_m13_regulatory_profile_and_correction_log` (tables `m13_regulatory_profile_versions`, `m13_correction_log`, RLS — migration 057).
- **Preuve** : `python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py` → `[OK] La DB est synchronisee avec le head local.`

### Variables d’environnement (secrets)

- **`RAILWAY_DATABASE_URL`** n’est **pas** stockée dans le dépôt Git.
- Sur poste de travail : définie dans **`.env.railway.local`** (fichier **gitignored**, une ligne `RAILWAY_DATABASE_URL=...`).
- Chargement pour les scripts : **`python scripts/with_railway_env.py`** (recommandé si PowerShell bloque les `.ps1`) ou **`. .\\scripts\\load_railway_env.ps1`** — réf. **`docs/ops/RAILWAY_LOCAL_ENV.md`**.

### Gouvernance

- Runbook : `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md` ; ADR : `docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md`.

---

## ADDENDUM 2026-04-02 — AUDIT M13 HARDENING (PR #293 — merged f2aef1d1)

**Autorité :** audit système post-PR #292 — correctifs NC-01 / NC-02 / NC-03 + faiblesses F-01 / F-02.
**Statut :** MERGÉ dans main — CI 9/9 pass.

### NC-01 — Orchestrateur FSM (corrigé)

- `_reset_from` downstream : `pass_2a_regulatory_profile` ajouté dans toutes les chaînes (1A→2A, 1B→2A, 1C→2A, 1D→2A).
- Bug `AnnotationPipelineState.PASS_0_5_DONE` → remplacé par `QUALITY_ASSESSED` (l'enum ne contenait pas `PASS_0_5_DONE`).

### NC-02 — Tests M13 (de 7 à ~20+)

- `test_pass_2a_regulatory_profile.py` : +3 tests (FAILED/DEGRADED/confidence invariant).
- `test_m13_engine_smoke.py` : +3 tests (extra=forbid, confidence gates, legacy bridge).
- `test_057_m13_tables.py` (nouveau) : 6 tests DDL/FK/triggers/index (skip sans DB).
- `test_rls_dm_app_cross_tenant.py` : +2 tests RLS M13 (profile versions + correction log).

### NC-03 — Auth API (corrigé)

- `/api/m13/status` sécurisé par `Depends(get_current_user)` — aligné sur le patron JWT existant.

### F-01 — Migration 058

- `058_m13_correction_log_case_id_index` : `CREATE INDEX idx_m13_correction_log_case_id` sur `case_id`.
- Alembic head dépôt = **058** ; Railway prod = **057** (apply 058 après merge).

### F-02 — `registry.yaml` documenté

- Commentaire en tête : fichier documentaire / probe, pas lu par `RegulatoryConfigLoader`.

---

## ADDENDUM 2026-04-02 — M14 EVALUATION ENGINE (PR #295 merged)

**Autorité :** mandat CTO — implémentation M14 (DMS V4.1 Phase 5).

### Architecture M14

- **ADR-M14-001** : `docs/adr/ADR-M14-001_evaluation_engine.md`
- **Moteur** : `src/procurement/m14_engine.py` — `EvaluationEngine` (déterministe, pas de LLM)
- **Modèles** : `src/procurement/m14_evaluation_models.py` — Pydantic `extra="forbid"`, `M14Confidence = {0.6, 0.8, 1.0}`
- **Repository** : `src/procurement/m14_evaluation_repository.py` — CRUD `evaluation_documents` (migration 056)
- **API** : `src/api/routes/evaluation.py` — `/api/m14/status`, `POST /api/m14/evaluate`, `GET /api/m14/evaluations/{case_id}`
- **Auth** : `Depends(get_current_user)` sur toutes les routes M14

### Handoffs consommés

| Handoff | Source | Modèle | Module source |
|---------|--------|--------|---------------|
| H2 | M12 Pass 1C | `AtomicCapabilitySkeleton` | `procedure_models.py` |
| H3 | M12 Pass 1C | `MarketContextSignal` | `procedure_models.py` |
| RH1 | M13 Pass 2A | `ComplianceChecklist` | `compliance_models_m13.py` |
| RH2 | M13 Pass 2A | `EvaluationBlueprint` | `compliance_models_m13.py` |

### Wire case_id (BLQ-4/5 résolu)

- `run_passes_0_to_1` : paramètre `case_id` ajouté, transmis à `run_passes_1a_to_1d`
- Backend `/predict` : résout `case_id` depuis `task.data.case_id` ou `body.case_id`
- `_orchestrator_skip_mistral_reason` : `PASS_2A_DONE` ajouté aux états qui poursuivent avec Mistral

### RÈGLE-09 — Interdictions M14

- `winner`, `rank`, `recommendation`, `offre_retenue` = INTERDITS (Pydantic `extra="forbid"` bloque)
- M14 produit des scores et analyses, jamais de verdict d'attribution
- Le statut `"sealed"` dans `evaluation_documents` = comité humain uniquement

### DETTE-5 — FERMÉE

- Table `evaluation_documents` (migration 056) désormais consommée par `M14EvaluationRepository`
- DETTE-5 = ✅ DONE

### Tests M14

- `test_m14_engine_smoke.py` : 14 tests (évaluation, éligibilité, complétude, prix, confidence, kill list, process linking mismatch / UNRESOLVED)
- `test_m14_models.py` : 14 tests (extra=forbid × 9 modèles, confidence grid, kill list, evaluation methods)
- `test_evaluation_documents.py` : 7 tests DDL/FK/RLS/columns
- `test_rls_dm_app_cross_tenant.py` : +1 test RLS evaluation_documents

### Railway

- Tête Alembic dépôt : **059** (`score_history`, `elimination_log`) — appliquer prod selon runbook `ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE` lorsque le mandat déploiement est émis.
- 056 : `evaluation_documents` (rapport M14) ; 059 : audit append-only complémentaire.

### ADDENDUM court — M14 process linking + audit DB

- **Process linking** : `process_linking_data` consommé dans `EvaluationEngine` ; flags `PROCESS_LINKING_ROLE_MISMATCH`, `PROCESS_LINKING_UNRESOLVED` ; doc `docs/adr/DMS-M14-ARCH-RECONCILIATION.md`.
- **`save_m14_audit`** : après `save_evaluation`, écriture non bloquante (journalisée) vers `score_history` / `elimination_log` (migration 059).

### Post-merge PR #295 — 2026-04-02

- PR #295 merged : 3 commits (feat + CI fixes + Copilot review fixes)
- Branche `feat/M14-evaluation-engine` supprimée
- Copilot review : 9 commentaires résolus (committee_id FK lookup, completion ratio [0,1], weighted score calc, retry guard, ADR contract ref, process_role canonique)
- CI finale 9/9 verte (lint, black, invariants, freeze, milestones, coverage, lint-and-test)
- M14 = DONE — prochaine étape : taguer `v4.1.0-m14-done` (CTO)

### Post-merge PR #297 — 2026-04-03 (main `7913d465`)

- **PR #297 merged** : correction M14 A+B — routes `/api/m14` sur `main:app` et `src.api.main:app`, gate CI auth, migration **059** (`score_history`, `elimination_log`), process linking dans `m14_engine`, `save_m14_audit`, tests DB + INV-09 + revue Copilot (RLS session dans tests, `load_railway_env.ps1`).
- **Branche** `feat/M14-correction-ab-routes-audit-059` supprimée après merge.
- **Railway** : tête code **059** ; prod à appliquer via runbook lorsque le GO est donné.

---

## ADDENDUM 2026-04-03 — DMS VIVANT V2 (PR #300 — feat/dms-vivant-v2-architecture) — AUDIT CTO CORRECTIONS C-1→C-5

**Autorité :** mandat CTO — plan DMS VIVANT V2 FREEZE + audit correction 26 gaps critiques.  
**Statut :** branche `feat/dms-vivant-v2-architecture` — PR #300 en cours de revue.

### Alembic — Nouveau Head

```
head dépôt (main — PR #300 mergé 2026-04-03)          : 067_fix_market_coverage_trigger
head Railway prod                                     : 058_m13_correction_log_case_id_index (désaligné — GO CTO requis)
migrations pending Railway                            : 059 → 060 → 061 → 062 → 063 → 064 → 065 → 066 → 067
```

**Chaîne complète :**
```
044→045→046→046b→047→048→049→050→051→052→053→054→055→056→057→058
→059→060→061→062→063→064→065→066
```

| Migration | Contenu |
|-----------|---------|
| 059 | score_history + elimination_log (M14, append-only, RLS) |
| 060 | trigger auto-refresh market_coverage matview |
| 061 | dms_event_index (partitioned, append-only, 7 indexes) |
| 062 | colonnes bitemporal event_time sur m12_correction_log, decision_snapshots, market_signals_v2, decision_history |
| 063 | candidate_rules + rule_promotions (proposed→approved→applied) |
| 064 | dms_embeddings (vector(1024) dense + JSONB sparse) — requiert pgvector |
| 065 | llm_traces (LLM observabilité locale, Langfuse backup) |
| 066 | bridge triggers 11 sources → dms_event_index + partition DEFAULT |

### Nouvelles Tables VIVANT V2

| Table | Schéma | Owner | Horizon |
|-------|--------|-------|---------|
| `dms_event_index` | public (partitioned) | event_index_service | H2 |
| `candidate_rules` | public | candidate_rule_service | H2 |
| `rule_promotions` | public | learning_console | H2 |
| `dms_embeddings` | public | embedding_service | H3 |
| `llm_traces` | public | langfuse_integration | H3 |

### Nouvelles Erreurs Capitalisées

**E-83** (2026-04-03) : **Scope confidence `{0.6, 0.8, 1.0}`** — Cette règle s'applique UNIQUEMENT aux champs d'extraction documentaire (`TracedField.confidence`, `ExtractionField.confidence`, `DMSExtractionResult`). Les scores internes RAG (`RAGResult.confidence`), patterns (`PatternDetector._cluster_confidence()`), et mémoire (`CaseMemoryEntry.framework_confidence`) sont des floats continus documentés comme tels. Voir `ADR-CONFIDENCE-SCOPE-001`. Ne jamais appliquer la contrainte `{0.6, 0.8, 1.0}` aux scores internes non-extraction.

**E-84** (2026-04-03) : **`asyncio.get_event_loop()` deprecated Python 3.11** — `asyncio.get_event_loop().run_until_complete(coro)` lève `RuntimeError: There is no current event loop in thread 'MainThread'` sur Python 3.11 sans boucle active. Toujours utiliser `asyncio.run(coro)` dans les tests et scripts non-async. Ne jamais utiliser `get_event_loop()` hors d'un contexte avec boucle active explicite.

**E-85** (2026-04-03) : **`VALID_ALEMBIC_HEADS` dans `tests/test_046b_imc_map_fix.py`** — Ce tuple doit être étendu à chaque nouveau head Alembic ajouté au dépôt. L'oubli de cette mise à jour provoque `AssertionError: Head inattendu : <nouvelle_migration>` en CI. Convention : inclure le nouveau head dans `VALID_ALEMBIC_HEADS` dans le même PR que la migration.

**E-86** (2026-04-03) : **`REFRESH MATERIALIZED VIEW CONCURRENTLY` interdit dans trigger** — PostgreSQL interdit `CONCURRENTLY` à l'intérieur d'un bloc de transaction (trigger function). Toute `CREATE FUNCTION` de trigger qui rafraîchit une vue matérialisée doit utiliser `REFRESH MATERIALIZED VIEW` sans `CONCURRENTLY`. Si `CONCURRENTLY` est nécessaire, exécuter hors trigger via cron/ARQ.

**E-87** (2026-04-03) : **`ADD COLUMN NOT NULL` sans `DEFAULT` sur table existante** — Une migration `ALTER TABLE ... ADD COLUMN event_time TIMESTAMPTZ NOT NULL` sans `DEFAULT` casse les tests qui insèrent sans fournir `event_time`. Toujours combiner `NOT NULL` avec `DEFAULT now()` sur les colonnes temporelles ajoutées à des tables existantes, sauf si un backfill explicite précède l'ajout de la contrainte.

**E-88** (2026-04-03 — M15) : **SQL injection via interpolation f-string dans `IN (...)`** — Construction `f"WHERE item_id IN ({placeholders})"` avec des IDs concaténés directement est vulnérable à l'injection SQL et casse si un ID contient un guillemet. Toujours utiliser `WHERE item_id = ANY(%s)` avec une liste Python comme paramètre. Gérer explicitement `item_ids == []` (retour sans requête) pour éviter `IN ()` invalide.

**E-89** (2026-04-03 — M15) : **Secret Railway commité en clair dans un fichier de documentation** — `$env:PGPASSWORD = "VvIxShbsVuwXd..."` commité dans `docs/ops/DISASTER_RECOVERY.md`. Toujours utiliser des placeholders (`<RAILWAY_POSTGRES_PASSWORD>`) dans les docs. Tout secret commité doit être **rotaté immédiatement** côté Railway Dashboard. Ref : PR #301 Copilot C8.

**E-90** (2026-04-03 — M15) : **Hypothèses de schéma non vérifiées avant SQL** — Plan M15 utilisait `couche_b.mercurials_item_map.item_id` (inexistant — colonne réelle : `dict_item_id`) et `couche_b.procurement_dict_items.id` (inexistant — clé primaire réelle : `item_id`). Résultat : 3 scripts en erreur `UndefinedColumn`. **Règle** : avant tout script SQL sur une table inconnue, exécuter `SELECT column_name FROM information_schema.columns WHERE table_name='...'` pour vérifier les colonnes réelles.

**E-91** (2026-04-03 — M15) : **`public.audit_log.prev_hash NOT NULL` — chaîne blockchain non triviale** — La table `audit_log` implémente un chaînage style blockchain : `prev_hash` est `NOT NULL` et doit contenir le `hash` de la dernière ligne. Tout `INSERT` sans calculer `prev_hash` lève `NotNullViolation`. Ce pattern rend l'audit_log non utilisable directement dans un script batch simple. Pour les scripts de validation M15 scope limité, les colonnes `validated_at`, `validated_by`, `human_validated` des tables cibles suffisent comme trace d'audit. N'utiliser `audit_log` que sous mandat explicite avec implémentation du chaînage.

### Nouvelles Dépendances (RÈGLE-13)

| Package | Version | ADR | Usage |
|---------|---------|-----|-------|
| `arq` | 0.26.1 | ADR-H2-ARQ-001 | Background job queue (Redis) |
| `langfuse` | >=2.0.0 | ADR-H3-LANGFUSE-001 | LLM observabilité |
| `FlagEmbedding` | >=1.2.5 | ADR-H3-BGE-M3-001 | Embeddings locaux BGE-M3 |
| `ragas` | >=0.1.0 | (ADR-RAGAS-001 à créer) | Évaluation RAG |

### Nouveaux Modules src/

```
src/memory/      : event_index_models, event_index_service, pattern_models, pattern_detector,
                   candidate_rule_generator, candidate_rule_service, deterministic_retrieval,
                   retrieval_models, chunker_models, chunker, embedding_models, embedding_service,
                   reranker, rag_models, rag_service, langfuse_integration, calibration_models,
                   auto_calibrator, calibration_service
src/workers/     : arq_config, arq_tasks
src/agents/      : tools/tool_manifest, tools/regulatory_tools
src/evals/       : ragas_evaluator, golden_dataset_loader
src/api/views/   : case_timeline, case_timeline_models, market_memory_card, market_memory_models,
                   learning_console, learning_console_models
src/db/          : cursor_adapter (PsycopgCursorAdapter — :name → %(name)s translation)
```

### Nouveaux Scripts ops/

```
scripts/manage_event_index_partitions.py  : partitions semestrielles dms_event_index
scripts/create_ivfflat_index.py           : index IVFFlat après premier batch embeddings
scripts/ingest_embeddings.py              : chunker + embed + INSERT dms_embeddings
scripts/probe_h0_table_health.py          : health check H0 (exit strict si warn_count > 0)
scripts/probe_m13_h0_gates.py             : gates H0 M13
```

### Docs ops/

```
docs/ops/embeddings_index_runbook.md     : IVFFlat runbook complet
docs/ops/deployment.md                   : entrypoint Railway canonique (main.py root)
docs/adr/ADR-H2-ARQ-001.md
docs/adr/ADR-H3-LANGFUSE-001.md
docs/adr/ADR-H3-BGE-M3-001.md
docs/adr/ADR-CONFIDENCE-SCOPE-001.md
```

---
