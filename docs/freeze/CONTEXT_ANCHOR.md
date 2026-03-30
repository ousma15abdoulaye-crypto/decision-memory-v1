# CONTEXT ANCHOR OFFICIEL — VERSION OPPOSABLE ET INVIOLABLE

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  CONTEXT ANCHOR — DMS v4.1                                          ║
║  Dernière mise à jour : 2026-03-29 (ADDENDUM export M12 v2 / LS local) ║
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
║  GIT — 2026-03-19                                                    ║
║  ──────────────────────────────────────────────────────────────     ║
║  main              : a8aec01 (Merge M-FIX-EXTRACT-02 feat/fix-extract-02)║
║  feat/fix-extract-02 : MERGÉ dans main (M-FIX-EXTRACT-02)            ║
║  feat/pre-m12-extraction-reelle : MERGÉ dans main (Mandat 4)        ║
║  feat/fix-backend-production : backend v3.0.1d (en attente merge)   ║
║  alembic head local : 050_documents_sha256_not_null                  ║
║  alembic head Railway : 044_decision_history (DÉSYNCHRONISÉ)         ║
║  migrations pending Railway : 045 046 046b 047 048 049 050          ║
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
║  head actuel     : 050_documents_sha256_not_null                     ║
║  historique      : 001 → 045 — FREEZE TOTAL 001-045                ║
║  chaîne          : 044 → 045 → 046 → 046b → 047 → 048 → 049 → 050   ║
║  FREEZE          : 001 → 045 FREEZE TOTAL                          ║
║                    046 + 046b = DETTE-7 DONE                        ║
║                    047 = PHASE 1B DONE (ORM→psycopg Couche A)       ║
║  RÈGLE           : zéro autogenerate — SQL brut uniquement         ║
║  RÈGLE           : zéro modification fichiers existants 001-045    ║
║  RÈGLE           : toute nouvelle migration = 046+ séquentiel       ║
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
║  EXTRACTION — ÉTAT RÉEL POST-MERGE M-FIX-EXTRACT-02                   ║
║  ──────────────────────────────────────────────────────────────     ║
║  extract_text_any :                                                    ║
║    pypdf principal                                                      ║
║    pdfminer.six fallback si text_len < 100                              ║
║    log WARNING text_len=0 → PDF_SCAN_SANS_OCR ou PDF_CORROMPU          ║
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
║            auth_router.py, logging_config.py, ratelimit.py          ║
║  alembic/: versions/ 001–045, env.py                                ║
║  services/: annotation-backend/ (ML Backend Label Studio)            ║
║  docs/   : adr/, freeze/, mandates/, milestones/                   ║
║  scripts/: probes, seeds, migrations, import/export                ║
║  tests/  : auth/, contracts/, invariants/, mercuriale/              ║
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
║    ASAP-03 : Railway sync 045→048       ⏳ GO CTO requis              ║
║    ASAP-04 : M-TESTS.done              ⏳ (Mandat 2)                 ║
║    ASAP-05 : migration 049 FK validate  ⏳ (Mandat 2)                 ║
║    ASAP-06 : migration 050 sha256       ⏳ (Mandat 2)                 ║
║    ASAP-07/08 : Redis rate limit       ✓ DONE (Mandat 3)            ║
║    ASAP-09 : sqlalchemy → psycopg      ✓ DONE (Mandat 3)            ║
║    ASAP-10 : CI gates vivants         ⏳ (Mandat 2)                  ║
║    ASAP-11 : llm_router.py            ✓ DONE (Mandat 4)             ║
║    ASAP-12 : pont extraction          ✓ DONE (Mandat 4)             ║
║                                                                      ║
║  M12     BLOQUÉ — 7 ASAP non résolus                                 ║
║          BLOQUANT : 15 annotated_validated (0/15)                    ║
║          DETTE-8  : signaux IMC (après backend stable)               ║
║          DETTE-7  DONE — imc_category_item_map + 046 + 046b        ║
║          DETTE-8  NEXT — signaux IMC → market_signals_v2            ║
║                    dépend DETTE-7 ✓                                  ║
║          BLOQUANT AO — 15 docs annotated_validated                  ║
║                    XML + backend opérationnels ✓                    ║
║                    AO peut annoter maintenant                        ║
║  M13     PLAN  046_evaluation_documents + extraction pipeline       ║
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
║  BLOQUANT   : 15 docs annotated_validated (AO, non déléguable)     ║
║  DETTE-1    : API GET /signals (market_signals_v2)                  ║
║  DETTE-2    : listener pg_notify CRITICAL → webhook/email          ║
║  DETTE-3    : workflow validation decision_history                 ║
║  DETTE-4    : Tests Railway CI/CD (GitHub Actions)                 ║
║  DETTE-5    : 046_evaluation_documents (M13/M14)                   ║
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
