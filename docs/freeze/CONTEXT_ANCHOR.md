# CONTEXT_ANCHOR
# ============================================================
# POSER EN PREMIER DANS TOUTE NOUVELLE SESSION CLAUDE/CURSOR
# Regenerer apres chaque milestone DONE
# Genere : 2026-03-10 — post M8 DONE (market intelligence foundation)
# ============================================================

---

## 1. IDENTITE PROJET

  Nom         : DMS — Digital Market Signal
  Operateur   : AO — Abdoulaye Ousmane
  Lieu        : Mopti, Mali
  Domaine     : Transparence marches publics et approvisionnement
  Objectif    : Systeme nerveux central des achats — du devis au contrat
  Outil agent : Cursor + Claude Sonnet 4.6 (local)
  Role CTO    : CTO senior + systems engineer + decideur final

---

## 2. DOCUMENTS GELES — NE PAS REEXPLIQUER

  Ces documents sont loi. Ne pas les resumer. Ne pas les reformuler.
  Les lire directement si besoin.

  SYSTEM_CONTRACT.md         : docs/freeze/SYSTEM_CONTRACT.md
  DMS_V4.1.0_FREEZE.md       : docs/freeze/DMS_V4.1.0_FREEZE.md
  ORCHESTRATION_FRAMEWORK    : docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
  ETA_V1                     : docs/freeze/DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md
  DMS_MRD_PLAN_V1.md         : docs/freeze/DMS_MRD_PLAN_V1.md
  BASELINE_MRD_PRE_REBUILD   : docs/freeze/BASELINE_MRD_PRE_REBUILD.md
  ADR_META                   : docs/freeze/ADR-META-001-AMENDMENT-PROCESS.md
  FREEZE_HASHES.md           : docs/freeze/FREEZE_HASHES.md

  ETA_V1    : gelé 2026-03-10
              classification GLOBAL_CORE/TENANT_SCOPED/OVERLAY
              CB-01→CB-08 avec statuts et milestones
              table décision Section 15 par milestone
              génome canonique règles figées

  ADR_META  : gelé 2026-03-10
              processus unique d'amendement documents gelés
              emergency track 24h inclus

  Ordre de lecture obligatoire pour tout agent :
    0. SYSTEM_CONTRACT.md              <- couche zéro
    1. DMS_V4.1.0_FREEZE.md
    2. DMS_ORCHESTRATION_FRAMEWORK_V1.md
    3. DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md
    4. DMS_MRD_PLAN_V1.md
    5. MRD_CURRENT_STATE.md     <- etat courant
    6. BASELINE_MRD_PRE_REBUILD.md
    7. mandat du milestone en cours

---

## 3. ETAT COURANT — LIRE MRD_CURRENT_STATE.md

  docs/freeze/MRD_CURRENT_STATE.md

  En resume post-M8 :
    last_completed  : M8
    last_tag        : m8-done
    last_commit     : 641e108 (merge PR #178)
    next_milestone  : M9 (market_signals + formule V1.1 + price_series)
    alembic_local   : 042_market_surveys (head)
    alembic_railway : m7_4b (3 migrations en retard — m7_5/m7_6/m7_7)
    blocked_on      : aucun

  M8 DONE : 2026-03-10
    13 tables GLOBAL_CORE + TENANT_SCOPED + matview market_coverage
    6 triggers idempotents (DROP IF EXISTS + CREATE TRIGGER)
     migration 042 idempotente (IF NOT EXISTS partout)
    seeds: 6 contextes FEWS Mali, 45 items, 6 zones, 3 baskets
    CB-01 SEMANTIC_GUARD V1 PASS
    CB-08 TRIAGE: 610 unresolved t1=179 t2=431 t3=0
    ADR-M8-FORMULA-V1.1-INTENTION: formule reportee M9

---

## 3b. ÉTAT RÉEL POST PRE-M10A — 2026-03-11

  RAILWAY :
    alembic              : 043_market_signals_v11 ✓
    procurement_dict     : 1 490 items ✓
    mercurials           : 27 396 lignes
                           item_id UUID = artefact legacy
                           jointure via item_map UNIQUEMENT
    mercurials_item_map  : 1 629 mappings ✓
    tracked_market_items : 1 004 items ✓
    tracked_market_zones : 19 zones (DANS_M8 après seeds)
    zone_context_registry: 6 contextes FEWS Mali ✓
    geo_price_corridors  : 6 corridors ✓
    seasonal_patterns    : 0 lignes (vide Railway)
    market_signals_v2    : 247 signaux formula=1.1
                           residual_pct>0 sur CONTEXT/SEASONAL/WATCH/CRITICAL

  DETTES IDENTIFIÉES POUR M10A :
    DETTE-1 [RÉSOLUE] zone_context_registry vide Railway
      seed_zone_context_mali.py exécuté (ALLOW_RAILWAY_SEED=1)

    DETTE-2 [PARTIEL] residual_pct = 0 sur NORMAL
      seasonal_patterns vide Railway
      zone_context_registry consommé ✓ (CONTEXT_NORMAL, CRITICAL)

    DETTE-3 dict_collision_log 610 unresolved
      179 TIER-1 à résoudre

    DETTE-4 market_surveys 0 lignes
      poids 0.35 inactif

    DETTE-5 decision_history absente
      poids 0.15 inactif

  CONTRACT-02 REFORMULÉ :
    INTERDIT Railway sans GO CTO :
      migrations Alembic
      ALTER TABLE / DROP TABLE
      DELETE sans WHERE
    AUTORISÉ Railway avec DATABASE_URL :
      compute_market_signals.py
      seed scripts (ALLOW_RAILWAY_SEED=1)
      probe/lecture

  JOINTURE MERCURIALS — GRAVÉE :
    mercurials.item_id UUID = JAMAIS UTILISÉ
    Chemin unique :
      mercurials.item_canonical
      → mercurials_item_map.item_canonical
      → mercurials_item_map.dict_item_id
      → procurement_dict_items.item_id TEXT

---

## 4. STACK TECHNIQUE

  ### Local (poste Windows 10 Mopti)
    OS              : Windows 10 10.0.22000 (64-bit)
    Shell           : PowerShell (pas bash — adapter les commandes)
    Python          : 3.11.0 (installation systeme, pas de venv actif)
    pip             : 22.3
    git             : 2.53.0.windows.1
    node/npm        : ABSENTS (Railway CLI non installable)
    psql CLI        : ABSENT (utiliser psycopg3 Python pour probes)

  ### Base de donnees locale
    url_sqlalchemy  : postgresql+psycopg://dms:dms123@localhost:5432/dms
    url_psycopg3    : postgresql://dms:dms123@localhost:5432/dms
    postgres        : 15.16 (Visual C++ build 1944, 64-bit)
    Attention       : DATABASE_URL dans .env, pas exportee dans shell

  ### Base de donnees Railway
    url_var         : RAILWAY_DATABASE_URL dans .env
    host            : maglev.proxy.rlwy.net:35451
    postgres        : 17.7 (Debian)
    acces           : connexion directe psycopg3 (CLI absent)
    usage           : lecture uniquement sauf migration explicite CTO

  ### Packages Python critiques
    psycopg         : 3.2.5
    sqlalchemy      : 2.0.25
    alembic         : 1.13.1
    fastapi         : 0.115.0
    uvicorn         : 0.30.0
    pydantic        : 2.9.0
    httpx           : 0.27.0
    redis           : 5.2.1
    pytest          : 9.0.2
    rapidfuzz       : installe (MRD-6)
    pytest-asyncio  : NON INSTALLE
    anthropic       : NON INSTALLE
    openai          : NON INSTALLE

  ### Charger .env en Python (DATABASE_URL non exportee)
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
    # Normaliser pour psycopg3 direct :
    db_url = os.environ['DATABASE_URL'].replace(
        'postgresql+psycopg://', 'postgresql://', 1)

---

## 5. SCHEMA BASE DE DONNEES — VERITES IMPORTANTES

  ### Pieges frequents pour les agents

  PIEGE-1 : item_id vs item_uid
    REEL    : item_id (TEXT) = cle primaire de procurement_dict_items
    FAUX    : item_uid n'est PAS la cle a utiliser en FK (erreur agent M8)
    Impact  : toute FK sur item_uid produit DatatypeMismatch en CI
    Fix M8  : toutes FK M8 pointent sur item_id TEXT

  PIEGE-2 : label vs label_fr
    REEL    : label_fr (TEXT) = colonne label du dictionnaire
    FAUX    : colonne label n'existe PAS
    Impact  : fingerprint = sha256(normalize(label_fr)|source_type)

  PIEGE-3 : fuzzy_score echelle
    REEL    : public.dict_collision_log.fuzzy_score = 0.0 a 1.0
    FAUX    : ce n'est pas 0-100 comme rapidfuzz retourne nativement
    Impact  : diviser par 100 avant INSERT

  PIEGE-4 : resolution dans dict_collision_log
    REEL    : CHECK ('unresolved', 'auto_merged', 'proposal_created')
    FAUX    : 'pending' n'est pas une valeur valide
    Impact  : erreur CHECK violation au INSERT

  PIEGE-5 : aliases sans colonne active
    REEL    : procurement_dict_aliases n'a PAS de colonne active
    Impact  : ne pas filtrer WHERE active=TRUE sur cette table

  PIEGE-6 : autocommit requis pour probes longs
    Raison  : InFailedSqlTransaction si erreur dans un bloc
    Fix     : psycopg.connect(db_url, autocommit=True)

  PIEGE-7 : category_match et unit_match NOT NULL
    Table   : public.dict_collision_log
    Fix     : fournir FALSE si inconnu

  ### Schema couche_b.procurement_dict_items (colonnes cles)
    item_id           TEXT PK
    label_fr          TEXT
    label_en          TEXT
    active            BOOLEAN DEFAULT TRUE
    fingerprint       TEXT    UNIQUE sur actifs
    item_code         TEXT    UNIQUE sur actifs
    birth_source      TEXT CHECK (mercuriale|imc|seed|manual|legacy|unknown)
    birth_run_id      UUID
    birth_timestamp   TIMESTAMPTZ
    label_status      TEXT NOT NULL DEFAULT 'draft'
                      CHECK (draft|validated|deprecated)
    taxo_l1           TEXT
    taxo_l2           TEXT
    taxo_l3           TEXT
    taxo_version      TEXT (pre-existante M7 — ne pas recrer)
    quality_score     SMALLINT
    human_validated   BOOLEAN
    domain_id         TEXT
    family_l2_id      TEXT
    subfamily_id      TEXT
    item_type         TEXT
    default_unit      TEXT FK RESTRICT -> procurement_dict_units

  ### Triggers sur couche_b.procurement_dict_items
    trg_protect_item_identity      BEFORE UPDATE
      -> item_id immuable
      -> fingerprint immuable apres init
      -> item_code immuable apres init
      -> label_fr immuable si label_status='validated'
      -> label_status='deprecated' irreversible

    trg_protect_item_with_aliases  BEFORE DELETE
      -> interdit si aliases actifs existent

    trg_block_legacy_family_*      BEFORE INSERT/UPDATE
    trg_compute_quality_score      BEFORE INSERT/UPDATE
    trg_dict_compute_hash          BEFORE UPDATE
    trg_dict_write_audit           AFTER UPDATE

---

## 6. DECISIONS ARCHITECTURALES FIGEES

  fingerprint_formula  : sha256(normalize(label_fr) + '|' + source_type)
  normalize()          : strip + lower + re.sub(r'\s+', ' ', s)
  source_id_exclu      : identifiant pas identite — INV-04
  item_code_format     : {PREFIX}-{YYYYMM}-{SEQ6}
  item_code_prefixes   : MC=mercuriale IC=imc SD=seed/manual LG=legacy/unknown
  taxo_version_actuelle: 1.0 (coverage 86.38%, 1287/1490 items)
  collision_seuil      : 85 (REGLE-26 V4 — resolution humaine uniquement)
  sequence_milestones  : PRE0->MRD-0->MRD-1->MRD-2->MRD-4->MRD-5->MRD-6->M8->...

---

## 7. REGLES CI — OBLIGATOIRES AVANT TOUT COMMIT

  Toute migration Alembic et tout script Python :
    python -m ruff check [fichier] --fix
    python -m black [fichier]
    python -m ruff check [fichier]       # confirmer 0 erreur
    python -m black --check [fichier]    # confirmer unchanged

  Causes d'echec CI frequentes :
    - import dans une fonction (doit etre au top du module)
    - timezone.utc -> utiliser datetime.UTC (UP017)
    - f-string avec backslash (Python 3.11)
    - heredoc bash (PowerShell ne supporte pas <<'EOF')
    - operateur && (PowerShell utilise ; a la place)

---

## 8. REGLES CONTRACTUELLES CRITIQUES

  CONTRACT-01 : validate_mrd_state.py en premier — toujours
  CONTRACT-02 : DATABASE_URL jamais Railway pendant migration locale
  CONTRACT-03 : docs/freeze/ immuable sauf BLOC 3 du mandat
  CONTRACT-04 : next_milestone doit = milestone du mandat recu
  CONTRACT-05 : tag mrd-{N-1}-done present avant demarrer MRD-N
  CONTRACT-06 : commit = exactement les fichiers du BLOC 9
  CONTRACT-07 : downgrade() fail-loud presente et testee
  CONTRACT-08 : lire avant ecrire — probe avant toute migration

  INV-05 : rebuild = UPSERT fingerprint — jamais DELETE+INSERT
  INV-08 : alembic heads = 1 seule ligne — jamais de multi-head
  INV-11 : DATABASE_URL ne contient pas 'railway'

  ETA_V1 Q1-Q9 : checklist conformité architecturale
                 obligatoire tout milestone
  CB-05         : CONSTRAINT_HEADER actif dès M8
                 tout mandat commence par BLOC 0

---

## 9. MILESTONES MRD — TABLEAU COMPLET

  | Jalon    | Statut | Tag          | Commit  | Date       |
  |----------|--------|--------------|---------|------------|
  | PRE0     | DONE   | absent       | d56dd32 | 2026-03-09 |
  | MRD-0    | DONE   | mrd-0-done   | 4b2fab8 | 2026-03-09 |
  | MRD-1    | DONE   | mrd-1-done   | b939e3b | 2026-03-08 |
  | MRD-2    | DONE   | mrd-2-done   | a3067fb | 2026-03-09 |
  | MRD-3    | DONE   | legacy       | b905ad4 | 2026-03-08 |
  | MRD-4    | DONE   | mrd-4-done   | 831117b | 2026-03-09 |
  | MRD-5    | DONE   | mrd-5-done   | 29efbc6 | 2026-03-09 |
  | MRD-6    | DONE   | mrd-6-done   | 226b4dd | 2026-03-09 |
  | ETA-GEL  | DONE   | eta-v1-done  | e51b339 | 2026-03-10 |
  | M8       | DONE   | m8-done      | 641e108 | 2026-03-10 |
  | M9       | NEXT   | -            | -       | -          |

  Hash chain ETA-GEL (FREEZE_HASHES.md) :
    DMS_V4.1.0_FREEZE.md              = e892d783...
    DMS_ORCHESTRATION_FRAMEWORK_V1.md = 66a6961d...
    SYSTEM_CONTRACT.md                 = 92acb422...
    BASELINE_MRD_PRE_REBUILD.md        = d1093db6...
    DMS_MRD_PLAN_V1.md                 = 5c025e4a...
    DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md = c0369ca1...
    ADR-META-001-AMENDMENT-PROCESS.md  = 0e43674a...

  Alembic head par milestone :
    MRD-1 : m7_4a_item_identity_doctrine (restaure sur origin/main)
    MRD-3 : m7_4b (neutralise CASCADE FK)
    MRD-4 : m7_5_fingerprint_triggers
    MRD-5 : m7_6_item_code
    MRD-6 : m7_7_genome_stable
    M8    : 042_market_surveys  <- HEAD ACTUEL

---

## 10. PROCHAINE ETAPE — M9

  Milestone suivant : M9 — Market Signals + Formule V1.1
  Prerequis         : tag m8-done present (OUI)
  Alembic cible     : 043_market_signals (a creer)
  Hors scope M8     : market_signals, compute_signal, price_series,
                      vendor_price_positioning, basket_cost_by_zone,
                      formule V1.1, tenant_market_baskets
  Railway           : appliquer m7_5 + m7_6 + m7_7 + 042 avant M9 prod
  ADR requis M9     : ADR-M9-FORMULA-V1.1 avant toute implementation

---

## 11. PROTOCOLE NOUVELLE SESSION

  Sequence obligatoire :
  1. Lire ce fichier (CONTEXT_ANCHOR.md)
  2. Lire docs/freeze/MRD_CURRENT_STATE.md
  3. Executer : python scripts/validate_mrd_state.py
  4. Si exit(0) et next_milestone = milestone du mandat -> GO
  5. Si exit(1) -> identifier le STOP -> poster au CTO -> attendre GO

  Tu es un agent d'execution. Le CTO decide.
  Tu ne demandes PAS de reexpliquer V4, Framework, ou MRD_PLAN.
  Tu lis ces documents directement si une info te manque.
  Si ambiguite -> STOP -> poser UNE question precise au CTO.
  Output brut uniquement aux checkpoints — zero reformulation.

---

## 12. INSTRUCTION POUR CLAUDE (nouvelle session)

  Contexte : tu reprends le travail sur DMS. M8 est DONE.
  Prochain chapitre : M9 (market_signals + formule V1.1).

  Ce que tu sais sans qu'on te le repete :
  - item_id (TEXT) = cle FK vers procurement_dict_items — PAS item_uid
  - users.id=INTEGER, units.id=INTEGER, cases.id=TEXT, geo_master.id=VARCHAR
  - migrations doivent etre idempotentes : IF NOT EXISTS + DROP TRIGGER IF EXISTS
  - conftest integration + db_integrity appellent alembic upgrade head
  - DATABASE_URL est dans .env, pas exportee dans PowerShell
  - PowerShell ne supporte pas bash heredoc ni operateur &&
  - ruff + black obligatoires avant tout commit
  - autocommit=True pour les probes longs psycopg3
  - Railway : 4 migrations en retard (m7_5 + m7_6 + m7_7 + 042)

  Ce que tu dois faire en debut de session :
    python scripts/validate_mrd_state.py
    Lire le mandat recu
    Verifier CONTRACT-04 (next_milestone = mandat recu)
    Si tout vert -> executer le mandat

  Ce que tu fais en fin de milestone :
    1. Mettre a jour MRD_CURRENT_STATE.md (counts reels, new head)
    2. Mettre a jour CONTEXT_ANCHOR.md (milestones tableau)
    3. Committer les deux
    4. Merger la branche sur main
    5. Poser le tag mrd-N-done
    6. Pousser main + tag
    7. Supprimer la branche feature
