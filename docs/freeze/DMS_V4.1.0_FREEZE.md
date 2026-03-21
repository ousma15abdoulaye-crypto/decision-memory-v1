# DMS V4.1.0 — PLAN DIRECTEUR DÉFINITIF

**Auteur :** Abdoulaye Ousmane — Founder & CTO
**Date de freeze :** 2026-02-26
**Statut :** FREEZE DÉFINITIF · OFFICIEL · RÉFÉRENCE UNIQUE
**Supérieur à :** V3.3.2 · V4.0.1 · V4.0.2 · V4.0.3 · V4.1.0-rc1
**Exécution :** Cursor + Claude Sonnet 4.6 · Mopti, Mali · Deepwork solo

---

# PARTIE I — FONDATIONS

## Principe directeur

> L'outil n'est jamais vide après M3.
> La donnée réelle entre tôt.
> Le moteur se calibre sur le réel.
> La décision reste humaine.
> L'agent exécute. L'humain valide.

## Jalons stratégiques

M0  → dette visible, mesurée, enregistrée dans TECHNICAL_DEBT.md
M3  → base cesse d'être vide — géographie + fournisseurs réels
M9  → Couche B = moat vivant — mercuriale + survey + signal actifs
M11 → stubs morts — corpus réel annoté — precision ≥ 0.70
M15 → preuve terrain 100 dossiers avec métriques opposables
M21 → déployé sans fiction — Claude activé automatiquement

## Contexte d'exécution

Opérateur : Abdoulaye Ousmane (unique)
Lieu       : Mopti, Mali
Outil      : Cursor + Claude Sonnet 4.6 — orchestration agent
Modèle     : Deepwork solo — zéro dev externe
Langue     : Français uniquement (beta)
Post-beta  : Bambara / Peul / Anglais — hors scope V1

## Actifs réels disponibles

| Actif | Volume | Milestone |
|---|---|---|
| Mercuriales officielles Mali | 2023 / 2024 / 2025 / 2026 | M5 |
| Articles mercuriels | ~2 000 | M6 |
| Fournisseurs SCI Excel | 200+ vendors multi-zones | M4 |
| Géographie Mali | régions / cercles / zones humanitaires | M3 |
| DAO réels anonymisables | 3 | M10B + M11 |
| RFQ réels anonymisables | 3 | M10B + M11 |
| Offres techniques réelles | 3 | M11 |
| Offres financières réelles | 3 | M11 |
| Dossiers DAO clôturés janvier 2026 | 100 | M15 |
| Règles SCI + DGMP Mali | procédures / seuils / critères | M13 |

---

# PARTIE II — STACK TECHNIQUE

## Infrastructure

Python 3.11 · FastAPI · Pydantic v2
PostgreSQL 16 · Redis 7 · Railway · Alembic
psycopg v3 (row_factory=dict_row)
pytest · ruff · black

## Extraction documents

python-magic>=0.4.27              détection MIME réelle
filetype>=1.2.0                   validation type fichier
pdfminer.six>=20221105            test PDF natif extractible
llama-parse>=0.4.0                PDF natif → Markdown + tables
azure-ai-formrecognizer>=3.3.0    scan → structuré + confidence
mistralai>=1.0.0                  OCR fallback + LLM extraction
instructor>=1.3.0                 structured output garanti typé
python-docx>=1.1.0                Word natif
openpyxl>=3.1.0                   Excel natif
pdf2image>=1.17.0                 PDF → images 300 DPI
Pillow>=10.4.0                    manipulation image
opencv-python-headless>=4.9.0     deskew + binarisation
pytesseract>=0.3.10               fallback offline Mali
numpy>=1.26.0                     calculs signal + outliers
rapidfuzz>=3.6.0                  fuzzy matching

## LLM chain — fallback ordonné

TIER 1  mistral-small-latest          primaire — disponible Mali
TIER 2  claude-3-5-haiku-20241022     branché — activé auto quand Mali dispo
TIER 3  gpt-4o-mini                   fallback universel
TIER 4  mistral-7b local/ollama       offline — résilience coupures Mali

## Principes invariants stack

Zéro ORM — SQL paramétré uniquement
DB-level triggers + REVOKE sur tables append-only
Extraction async — scoring jamais bloqué par extraction
ERP agnostique — zéro couplage ProSave / SAP / Oracle
Mocks complets tous providers en CI — zéro appel API réel dans tests

---

# PARTIE III — RÈGLES SYSTÈME

## Règles techniques

RÈGLE-01  1 milestone = 1 branche = 1 PR = 1 merge = 1 tag Git
RÈGLE-02  Séquence interne : DB → tests DB → services → endpoints → CI verte
RÈGLE-03  CI rouge = STOP TOTAL
RÈGLE-04  PostgreSQL = source de vérité. Redis = cache reconstructible.
RÈGLE-05  Append-only sur toute table décisionnelle / audit / traçabilité
RÈGLE-06  DONE ou ABSENT. Rien entre les deux.
RÈGLE-07  Zéro "..." dans les tests. Assertions explicites.
RÈGLE-08  PROBE-SQL-01 avant toute migration touchant une table existante
RÈGLE-09  winner / rank / recommendation / best_offer = INTERDITS hors comité humain
RÈGLE-10  status=complete = réservé M15 exclusivement
RÈGLE-11  LLM extraction = API externe — ADR obligatoire avant premier commit
RÈGLE-12  Migrations = SQL brut via op.execute() — ZÉRO autogenerate
RÈGLE-13  Toute dépendance nouvelle = ADR avant premier commit
RÈGLE-14  Chaque DoD validé sur données réelles
RÈGLE-15  Documents réels anonymisés avant commit. État raw_received = jamais committé, jamais exposé.
RÈGLE-16  Extraction primaire = stack API externe contractuelle. Fallback local (Tesseract + mistral-7b) = résilience d'exception uniquement. Jamais chemin nominal en beta. Justification : coupures réseau Mali = réalité terrain, pas excuse pour faire du local en nominal.
RÈGLE-17  Toute migration DB = 1 test minimum prouvant l'invariant visé
RÈGLE-18  ERP agnostique — zéro couplage ProSave / SAP / Oracle
RÈGLE-19  Tout champ extrait = value + confidence + evidence JAMAIS valeur nue
RÈGLE-20  Fuzzy match sous seuil = UNRESOLVED explicite. Jamais silencieux.
RÈGLE-21  Mocks complets pour tous services API externes en CI. Zéro appel API réel dans les tests automatisés.
RÈGLE-22  Formule Market Signal = documentée, versionnée, reproductible. Version 1.0 gravée dans market_signals.formula_version
RÈGLE-23  Extraction / reconnaissance = corpus annoté obligatoire. Seul l'état annotated_validated compte. Minimum 15 annotated_validated avant M12. Minimum 50 annotated_validated avant M15.
RÈGLE-24  Extraction toujours asynchrone. Pipeline scoring ne démarre jamais en attendant l'extraction.
RÈGLE-25  Annotation ground_truth = travail humain uniquement. L'agent ne crée jamais de ground_truth.
RÈGLE-26  Fusion dict auto = 3 conditions simultanées obligatoires : score ≥ 85 ET même category_id ET même unit_id. Si une condition manque → proposal obligatoire.
RÈGLE-27  Toute fusion auto dict = entrée dans dict_collision_log.
RÈGLE-28  SLA définis et non négociables :
          UPLOAD   ≤ 500ms  (202 Accepted immédiat)
          EXTRACT  ≤ 30s    (async — best effort — non bloquant)
          PIPELINE ≤ 60s    (scoring + signal HORS extraction)
          SIGNAL   ≤ 200ms  (market_signal seul)
          EXPORT   ≤ 10s    (CBA + PV)
RÈGLE-29  Séquence dictionnaire non inversible :
          M5 = ingestion brute sources (mercuriale_sources + mercurials)
          M6 = construction canonique depuis libellés réels M5
          M7 = enrichissement contrôlé (collisions + proposals)
          M6 bloqué si M5 DoD non vert. M7 bloqué si M6 DoD non vert.

## Règles orchestration

RÈGLE-ORG-01  1 mandat agent = 1 milestone = 1 branche Git
RÈGLE-ORG-02  L'agent lit le mandat en entier avant de commencer
RÈGLE-ORG-03  SIGNAL STOP = arrêt immédiat + post humain + attente
              L'agent n'improvise jamais sur un signal stop
RÈGLE-ORG-04  DoD = checklist binaire validée par l'humain avant merge
              Jamais validée par l'agent seul
RÈGLE-ORG-05  Annotation = travail humain uniquement (RÈGLE-25)
RÈGLE-ORG-06  Après chaque merge :
              → Deploy staging automatique (Railway)
              → Smoke test : healthcheck + alembic heads + pytest smoke
              → Smoke vert ET DoD validé : deploy production
              → Smoke rouge : rollback staging — production intacte
              Milestones pure-docs : merge main suffit, pas de deploy
RÈGLE-ORG-07  Fichier hors périmètre modifié = revert immédiat
RÈGLE-ORG-08  Chaque mandat commence par PROBE (état réel du système avant toute modification)
RÈGLE-ORG-09  Mandats versionnés dans .mandats/
              Jamais modifiés après exécution
              Correctif → .mandats/M{N}fix{issue}.md
RÈGLE-ORG-10  L'agent ne merge jamais
              L'humain seul merge après DoD vert
RÈGLE-ORG-11  Chemin ADR = docs/adr/ (singulier, invariant)
              Jamais docs/adrs/

## Invariants métier

INV-R1  1 comité = 1 registre dépôts (UNIQUE committee_id)
INV-R2  recorded_at = système. Jamais saisi par utilisateur.
INV-R3  submission_registry_events = append-only (trigger DB)
INV-R4  Aucun dépôt après fermeture registre (trigger DB)
INV-R5  Registre sans comité = impossible (FK NOT NULL)
INV-R6  Registre n'écrit jamais en Couche B
INV-R7  Pipeline lit le registre — jamais le modifie
INV-R8  Dépôt = supplier_name_raw + (email OU téléphone)
INV-R9  Chaque dépôt = recorded_by + recorded_at

---

# PARTIE IV — ARCHITECTURE

## Couches système

```
┌──────────────────────────────────────────────────────────────────────┐
│                      COUCHE A — PROCUREMENT                          │
│                                                                      │
│  Case Management      Document Upload      Extraction Engine         │
│  ─────────────────    ───────────────     ──────────────────────     │
│  create / status      sha256 + audit      Classifier                │
│  procedure_type       queue async         TextNormalizer            │
│  procurement_file     202 immédiat        LlamaParse (PDF natif)    │
│                                           Azure Doc Intel (scan)    │
│  Scoring Engine       Committee           Mistral OCR (fallback)    │
│  ─────────────────    ──────────────      python-docx (Word)        │
│  criteria weights     members + seal      openpyxl (Excel)          │
│  eliminatory          ACO + PV export     Tesseract (offline)       │
│  SCI §5.2 rules       Submission          StructuredExtractor       │
│                       Registry            (instructor + LLM chain)  │
│                                           ConfidenceRouter          │
│                                           Review Queue              │
├──────────────────────────────────────────────────────────────────────┤
│                      COUCHE B — MÉMOIRE MARCHÉ                       │
│                                                                      │
│  Dictionary + Fuzzy   Mercuriale Ingest   Market Signal             │
│  ──────────────────   ─────────────────   ─────────────             │
│  canonical + aliases  2023/24/25/26       agrégation 3 sources      │
│  collision_log        sha256 idempotent   formule v1.0              │
│  dict_proposals       zone × année        readonly → Couche A       │
│                                                                      │
│  Decision Feedback Pipeline                                          │
│  ──────────────────────────                                          │
│  seal() → decision_history → dict enrichment auto                   │
├──────────────────────────────────────────────────────────────────────┤
│                         INFRASTRUCTURE                               │
│         PostgreSQL 16 · Redis 7 · Railway · FastAPI · Alembic       │
└──────────────────────────────────────────────────────────────────────┘
```

## SLA

| Opération | SLA | Nature |
|---|---|---|
| UPLOAD | ≤ 500ms | 202 Accepted immédiat |
| EXTRACT | ≤ 30s | async best effort non bloquant |
| PIPELINE | ≤ 60s | scoring + signal HORS extraction |
| SIGNAL | ≤ 200ms | market_signal seul |
| EXPORT | ≤ 10s | CBA + PV |

## Seuils procédure SCI §4.2

| Montant | Procédure | Comité |
|---|---|---|
| < 100 $ | hors scope | — |
| 101 – 1 000 $ | devis_unique (1 offre) | non |
| 1 001 – 10 000 $ | devis_simple (3 offres) | non |
| 10 001 – 100 000 $ | devis_formel (3 offres) | oui |
| > 100 001 $ | appel_offres_ouvert (21j) | oui |
| Humanitaire | seuils × 2 | min 2 membres |

## Critères évaluation SCI §5.2

Essentiels éliminatoires : NIF · RCCM · conditions SCI · sanctions · RIB
Commerciaux : pondération ≥ 40% obligatoire
Durabilité : pondération ≥ 10% obligatoire
Total : = 100% (tolérance ±1%)

## Composition comité SCI §5.4

Standard (3 votants)     : supply_chain + finance + budget_holder
Humanitaire (2 votants)  : budget_holder + supply_chain
SOD                      : sourcing lead ≠ membre votant

---

# PARTIE V — SCHÉMA DB COMPLET

```sql
-- ═══════════════════════════════════════════════════════════════
-- DMS V4.1.0 — SCHÉMA COMPLET ÉTAT CIBLE
-- Migrations via Alembic op.execute() uniquement — ZÉRO autogenerate
-- ═══════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────
-- INFRASTRUCTURE
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email        TEXT NOT NULL UNIQUE,
  full_name    TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (
    role IN ('admin','manager','buyer','viewer','auditor')
  ),
  organization TEXT,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS token_blacklist (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token_jti  TEXT NOT NULL UNIQUE,
  revoked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity     TEXT NOT NULL,
  entity_id  TEXT NOT NULL,
  action     TEXT NOT NULL,
  actor_id   UUID REFERENCES users(id),
  payload    JSONB,
  prev_hash  TEXT,
  event_hash TEXT NOT NULL,
  ip_address INET,
  timestamp  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- APPEND-ONLY : REVOKE DELETE, UPDATE FROM app_user

-- ─────────────────────────────────────────
-- GÉO + CATÉGORIES
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS geo_master (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code      TEXT NOT NULL UNIQUE,
  name      TEXT NOT NULL,
  level     INTEGER NOT NULL,
  -- 0=pays 1=région 2=cercle 3=zone_humanitaire
  parent_id UUID REFERENCES geo_master(id)
);

CREATE TABLE IF NOT EXISTS procurement_categories (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code                  TEXT NOT NULL UNIQUE,
  label                 TEXT NOT NULL,
  parent_id             UUID REFERENCES procurement_categories(id),
  sci_category_specific BOOLEAN DEFAULT FALSE
);

-- ─────────────────────────────────────────
-- DICTIONNAIRE — COUCHE B FONDATION
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS units (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical TEXT NOT NULL UNIQUE,
  aliases   TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS procurement_references (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical   TEXT NOT NULL UNIQUE,
  category_id UUID REFERENCES procurement_categories(id),
  unit_id     UUID REFERENCES units(id),
  aliases     TEXT[] NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by  UUID REFERENCES users(id),
  source      TEXT NOT NULL DEFAULT 'manual' CHECK (
    source IN ('manual','mercuriale','offer_feedback','enrichment')
  )
);

CREATE TABLE IF NOT EXISTS dict_proposals (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_text       TEXT NOT NULL,
  suggested_id   UUID REFERENCES procurement_references(id),
  confidence     FLOAT NOT NULL,
  source_case_id UUID REFERENCES cases(id),
  status         TEXT NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending','approved','rejected')
  ),
  reviewed_by    UUID REFERENCES users(id),
  reviewed_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dict_collision_log (
  -- RÈGLE-27 : toute fusion auto = entrée ici
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_text_1     TEXT NOT NULL,
  raw_text_2     TEXT NOT NULL,
  canonical_id   UUID REFERENCES procurement_references(id),
  fuzzy_score    FLOAT NOT NULL CHECK (fuzzy_score BETWEEN 0.0 AND 1.0),
  category_match BOOLEAN NOT NULL,
  unit_match     BOOLEAN NOT NULL,
  resolution     TEXT NOT NULL CHECK (
    resolution IN ('auto_merged','proposal_created','unresolved')
  ),
  resolved_by    TEXT NOT NULL DEFAULT 'auto',
  source_year_1  INTEGER,
  source_year_2  INTEGER,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- APPEND-ONLY : REVOKE DELETE, UPDATE FROM app_user

-- ─────────────────────────────────────────
-- FOURNISSEURS
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS vendors (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                   TEXT NOT NULL,
  canonical_name         TEXT NOT NULL UNIQUE,
  aliases                TEXT[] NOT NULL DEFAULT '{}',
  nif                    TEXT,
  rccm                   TEXT,
  rib                    TEXT,
  verification_status    TEXT NOT NULL DEFAULT 'registered' CHECK (
    verification_status IN (
      'registered','qualified','approved','suspended'
    )
  ),
  vcrn                   TEXT UNIQUE,
  verified_at            TIMESTAMPTZ,
  verified_by            TEXT,
  key_personnel_verified BOOLEAN DEFAULT FALSE,
  suspension_reason      TEXT,
  suspended_at           TIMESTAMPTZ,
  zones_covered          UUID[] DEFAULT '{}',
  category_ids           UUID[] DEFAULT '{}',
  has_sanctions_cert     BOOLEAN DEFAULT FALSE,
  has_sci_conditions     BOOLEAN DEFAULT FALSE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────
-- CASES
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cases (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reference            TEXT NOT NULL UNIQUE,
  title                TEXT NOT NULL,
  procedure_type       TEXT NOT NULL CHECK (
    procedure_type IN (
      'devis_unique','devis_simple',
      'devis_formel','appel_offres_ouvert'
    )
  ),
  estimated_value      NUMERIC(15,2),
  currency             TEXT NOT NULL DEFAULT 'XOF',
  humanitarian_context TEXT NOT NULL DEFAULT 'none' CHECK (
    humanitarian_context IN ('none','cat1','cat2','cat3','cat4')
  ),
  min_offers_required  INTEGER NOT NULL DEFAULT 1,
  response_period_days INTEGER,
  sealed_bids_required BOOLEAN NOT NULL DEFAULT FALSE,
  committee_required   BOOLEAN NOT NULL DEFAULT FALSE,
  zone_id              UUID REFERENCES geo_master(id),
  category_id          UUID REFERENCES procurement_categories(id),
  status               TEXT NOT NULL DEFAULT 'draft' CHECK (
    status IN (
      'draft','open','evaluation','committee',
      'sealed','awarded','cancelled'
    )
  ),
  procurement_file     JSONB NOT NULL DEFAULT '{
    "pr": "absent",
    "rfq": "absent",
    "sealed_bids_opened": false,
    "offers_received": 0,
    "aco": "absent",
    "vcrn_all_verified": false,
    "contract": "absent",
    "po": "absent",
    "grn": "absent"
  }',
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by           UUID REFERENCES users(id),
  submission_deadline  TIMESTAMPTZ,
  profile_applied      TEXT
);

-- ─────────────────────────────────────────
-- CRITÈRES D'ÉVALUATION
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS evaluation_criteria (
  id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id                    UUID NOT NULL REFERENCES cases(id),
  label                      TEXT NOT NULL,
  type                       TEXT NOT NULL CHECK (
    type IN ('essential','commercial','capacity','sustainability')
  ),
  weight                     NUMERIC(5,2) NOT NULL,
  method                     TEXT NOT NULL CHECK (
    method IN ('formula','paliers','judgment','boolean')
  ),
  max_score                  NUMERIC(5,2),
  paliers                    JSONB,
  formula                    TEXT,
  is_eliminatory             BOOLEAN NOT NULL DEFAULT FALSE,
  required_document          TEXT,
  extracted_from_document_id UUID REFERENCES documents(id),
  extraction_confidence      FLOAT,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────
-- DOCUMENTS + EXTRACTION
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id           UUID NOT NULL REFERENCES cases(id),
  filename          TEXT NOT NULL,
  sha256            TEXT NOT NULL,
  doc_type          TEXT NOT NULL CHECK (
    doc_type IN (
      'tdr','rfq','dao','offer_technical','offer_financial',
      'offer_combined','admin_doc','contract','grn','other'
    )
  ),
  file_type         TEXT NOT NULL CHECK (
    file_type IN ('native_pdf','scan','word','excel','unknown')
  ),
  storage_path      TEXT NOT NULL,
  page_count        INTEGER,
  extraction_status TEXT NOT NULL DEFAULT 'pending' CHECK (
    extraction_status IN (
      'pending','queued','processing','done',
      'failed','review_required'
    )
  ),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by        UUID REFERENCES users(id),
  UNIQUE (case_id, sha256)
);

CREATE TABLE IF NOT EXISTS extraction_jobs (
  -- RÈGLE-24 : extraction toujours async
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID NOT NULL REFERENCES documents(id),
  engine_used     TEXT NOT NULL CHECK (
    engine_used IN (
      'llamaparse','azure_doc_intel','mistral_ocr',
      'python_docx','openpyxl','tesseract','failed'
    )
  ),
  llm_model       TEXT,
  llm_provider    TEXT CHECK (
    llm_provider IN ('mistral','claude','openai','local','none')
  ),
  raw_output      TEXT,
  structured_json JSONB,
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at    TIMESTAMPTZ,
  error_message   TEXT,
  page_count      INTEGER,
  cost_usd        NUMERIC(8,6),
  retry_count     INTEGER NOT NULL DEFAULT 0,
  max_retries     INTEGER NOT NULL DEFAULT 3,
  next_retry_at   TIMESTAMPTZ,
  queued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  fallback_used   BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS offer_extractions (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id              UUID NOT NULL REFERENCES documents(id),
  case_id                  UUID NOT NULL REFERENCES cases(id),
  vendor_id                UUID REFERENCES vendors(id),
  total_price              NUMERIC(15,2),
  total_price_conf         FLOAT,
  total_price_evid         TEXT,
  unit_price               NUMERIC(15,4),
  unit_price_conf          FLOAT,
  currency                 TEXT DEFAULT 'XOF',
  delivery_delay_days      INTEGER,
  delay_conf               FLOAT,
  has_nif                  BOOLEAN,
  has_nif_conf             FLOAT,
  has_rccm                 BOOLEAN,
  has_rccm_conf            FLOAT,
  has_rib                  BOOLEAN,
  has_rib_conf             FLOAT,
  has_sci_conditions       BOOLEAN,
  has_sci_cond_conf        FLOAT,
  has_sanctions_cert       BOOLEAN,
  has_sanctions_conf       FLOAT,
  chief_researcher_years   INTEGER,
  cabinet_studies_count    INTEGER,
  team_studies_count       INTEGER,
  has_sustainability_proof BOOLEAN,
  line_items               JSONB DEFAULT '[]',
  extraction_corrections   JSONB DEFAULT '[]',
  extraction_job_id        UUID REFERENCES extraction_jobs(id),
  overall_confidence       FLOAT,
  review_required          BOOLEAN NOT NULL DEFAULT FALSE,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS extraction_review_queue (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID NOT NULL REFERENCES documents(id),
  case_id         UUID NOT NULL REFERENCES cases(id),
  field_name      TEXT NOT NULL,
  extracted_value TEXT,
  confidence      FLOAT NOT NULL,
  evidence        TEXT,
  evidence_page   INTEGER,
  status          TEXT NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending','validated','corrected','dismissed')
  ),
  validated_value TEXT,
  validated_by    UUID REFERENCES users(id),
  validated_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────
-- SCORING
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS score_history (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id            UUID NOT NULL REFERENCES cases(id),
  vendor_id          UUID NOT NULL REFERENCES vendors(id),
  criteria_id        UUID NOT NULL REFERENCES evaluation_criteria(id),
  raw_value          TEXT,
  score              NUMERIC(8,4) NOT NULL,
  max_score          NUMERIC(8,4) NOT NULL,
  is_eliminated      BOOLEAN NOT NULL DEFAULT FALSE,
  elimination_reason TEXT,
  scored_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  scored_by          TEXT NOT NULL
);
-- APPEND-ONLY : REVOKE DELETE, UPDATE FROM app_user

CREATE TABLE IF NOT EXISTS elimination_log (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id       UUID NOT NULL REFERENCES cases(id),
  vendor_id     UUID NOT NULL REFERENCES vendors(id),
  criteria_id   UUID REFERENCES evaluation_criteria(id),
  reason        TEXT NOT NULL,
  eliminated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  eliminated_by TEXT NOT NULL
);
-- APPEND-ONLY : REVOKE DELETE, UPDATE FROM app_user

-- ─────────────────────────────────────────
-- COMITÉ + REGISTRE DÉPÔTS
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS committees (
  committee_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id        UUID NOT NULL REFERENCES cases(id) UNIQUE,
  status         TEXT NOT NULL DEFAULT 'draft' CHECK (
    status IN ('draft','active','locked')
  ),
  committee_type TEXT NOT NULL DEFAULT 'standard' CHECK (
    committee_type IN ('standard','humanitarian','simplified')
  ),
  min_members    INTEGER NOT NULL DEFAULT 3,
  locked_at      TIMESTAMPTZ,
  locked_by      UUID REFERENCES users(id),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS committee_members (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  committee_id      UUID NOT NULL REFERENCES committees(committee_id),
  user_id           UUID NOT NULL REFERENCES users(id),
  role              TEXT NOT NULL CHECK (
    role IN (
      'supply_chain','finance','budget_holder',
      'technical','security','pharma','observer'
    )
  ),
  is_voting         BOOLEAN NOT NULL DEFAULT TRUE,
  conflict_declared BOOLEAN NOT NULL DEFAULT FALSE,
  conflict_detail   TEXT,
  joined_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS committee_delegations (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  committee_id            UUID NOT NULL REFERENCES committees(committee_id),
  member_id               UUID NOT NULL REFERENCES committee_members(id),
  delegate_last_name      TEXT NOT NULL,
  delegate_first_name     TEXT NOT NULL,
  delegate_function_title TEXT NOT NULL,
  reason                  TEXT NOT NULL,
  starts_at               TIMESTAMPTZ,
  ends_at                 TIMESTAMPTZ,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS submission_registries (
  registry_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  committee_id UUID NOT NULL
    REFERENCES committees(committee_id) ON DELETE RESTRICT,
  case_id      UUID NOT NULL REFERENCES cases(id),
  tender_id    TEXT NOT NULL,
  process_type TEXT NOT NULL CHECK (
    process_type IN ('DAO','RFQ','RFP','OTHER')
  ),
  zone_primary TEXT,
  opened_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at    TIMESTAMPTZ,
  status       TEXT NOT NULL DEFAULT 'open' CHECK (
    status IN ('open','closed')
  ),
  created_by   UUID NOT NULL REFERENCES users(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_one_registry_per_committee UNIQUE (committee_id)
);

CREATE TABLE IF NOT EXISTS submission_registry_events (
  -- INV-R3 : APPEND-ONLY
  event_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  registry_id        UUID NOT NULL
    REFERENCES submission_registries(registry_id) ON DELETE RESTRICT,
  committee_id       UUID NOT NULL
    REFERENCES committees(committee_id) ON DELETE RESTRICT,
  case_id            UUID NOT NULL REFERENCES cases(id),
  tender_id          TEXT NOT NULL,
  event_type         TEXT NOT NULL CHECK (event_type IN (
    'registry_initialized',
    'submission_recorded',
    'submission_corrected_before_lock',
    'registry_closed',
    'registry_reopened_exception'
  )),
  supplier_name_raw  TEXT,
  supplier_email_raw TEXT,
  supplier_phone_raw TEXT,
  zone_raw           TEXT,
  lot_id_raw         TEXT,
  lot_count_declared INTEGER CHECK (lot_count_declared >= 1),
  submission_channel TEXT CHECK (
    submission_channel IN ('physical','email','courier','other')
  ),
  deposit_reference  TEXT,
  recorded_by        UUID NOT NULL REFERENCES users(id),
  recorded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata_json      JSONB NOT NULL DEFAULT '{}',
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- APPEND-ONLY : trigger + REVOKE

-- ─────────────────────────────────────────
-- ÉVALUATION ACO
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS evaluation_documents (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id                 UUID NOT NULL REFERENCES cases(id),
  committee_id            UUID NOT NULL REFERENCES committees(committee_id),
  version                 INTEGER NOT NULL DEFAULT 1,
  scores_matrix           JSONB NOT NULL DEFAULT '{}',
  justifications          JSONB NOT NULL DEFAULT '{}',
  qualification_threshold FLOAT,
  vendors_qualified       UUID[],
  vendors_eliminated      UUID[],
  pre_negotiation_scores  JSONB,
  status                  TEXT NOT NULL DEFAULT 'draft' CHECK (
    status IN ('draft','committee_review','sealed','exported')
  ),
  profile_applied         TEXT,
  aco_excel_path          TEXT,
  pv_word_path            TEXT,
  sealed_at               TIMESTAMPTZ,
  sealed_by               UUID REFERENCES users(id),
  seal_hash               TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────
-- COUCHE B — MÉMOIRE MARCHÉ
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS mercuriale_sources (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename     TEXT NOT NULL,
  sha256       TEXT NOT NULL UNIQUE,
  year         INTEGER NOT NULL,
  zone_id      UUID REFERENCES geo_master(id),
  source_type  TEXT NOT NULL CHECK (
    source_type IN ('official','dgmp','anpe','custom')
  ),
  imported_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  row_count    INTEGER,
  parse_status TEXT NOT NULL DEFAULT 'pending' CHECK (
    parse_status IN ('pending','processing','done','failed')
  )
);

CREATE TABLE IF NOT EXISTS mercurials (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id      UUID NOT NULL REFERENCES mercuriale_sources(id),
  item_code      TEXT,
  item_canonical TEXT NOT NULL,
  item_id        UUID REFERENCES procurement_references(id),
  unit_price     NUMERIC(15,4) NOT NULL,
  currency       TEXT NOT NULL DEFAULT 'XOF',
  unit_id        UUID REFERENCES units(id),
  zone_id        UUID REFERENCES geo_master(id),
  year           INTEGER NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS market_surveys (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id       UUID REFERENCES cases(id),
  item_id       UUID REFERENCES procurement_references(id),
  supplier_name TEXT NOT NULL,
  price_quoted  NUMERIC(15,4) NOT NULL,
  currency      TEXT NOT NULL DEFAULT 'XOF',
  date_surveyed DATE NOT NULL,
  zone_id       UUID REFERENCES geo_master(id),
  surveyor      TEXT NOT NULL,
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS market_signals (
  -- RÈGLE-22 : formule versionnée 1.0
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id         UUID NOT NULL REFERENCES procurement_references(id),
  zone_id         UUID REFERENCES geo_master(id),
  price_avg       NUMERIC(15,4),
  price_min       NUMERIC(15,4),
  price_max       NUMERIC(15,4),
  price_median    NUMERIC(15,4),
  data_points     INTEGER NOT NULL DEFAULT 0,
  signal_quality  TEXT NOT NULL DEFAULT 'empty' CHECK (
    signal_quality IN ('empty','low','medium','high','not_applicable')
  ),
  formula_version TEXT NOT NULL DEFAULT '1.0',
  sources         JSONB DEFAULT '[]',
  computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS decision_history (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id        UUID NOT NULL REFERENCES cases(id),
  item_id        UUID REFERENCES procurement_references(id),
  vendor_id      UUID REFERENCES vendors(id),
  price_paid     NUMERIC(15,4),
  quantity       NUMERIC(15,4),
  unit_id        UUID REFERENCES units(id),
  decision_date  DATE NOT NULL,
  zone_id        UUID REFERENCES geo_master(id),
  currency       TEXT DEFAULT 'XOF',
  total_score    NUMERIC(8,4),
  case_reference TEXT,
  procedure_type TEXT,
  source         TEXT NOT NULL DEFAULT 'committee_decision',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- APPEND-ONLY : REVOKE DELETE, UPDATE FROM app_user

-- ─────────────────────────────────────────
-- ANNOTATION REGISTRY
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS annotation_registry (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID REFERENCES documents(id),
  annotation_file TEXT NOT NULL,
  sha256          TEXT NOT NULL UNIQUE,
  document_type   TEXT NOT NULL,
  annotated_by    TEXT NOT NULL,
  annotated_at    TIMESTAMPTZ NOT NULL,
  duration_min    INTEGER,
  field_count     INTEGER,
  criteria_count  INTEGER,
  is_validated    BOOLEAN NOT NULL DEFAULT FALSE,
  validated_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────
-- TRIGGERS APPEND-ONLY
-- ─────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_reject_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION
    'Table % est append-only. DELETE/UPDATE interdits.',
    TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER trg_audit_log_append_only
  BEFORE DELETE OR UPDATE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();

CREATE TRIGGER trg_score_history_append_only
  BEFORE DELETE OR UPDATE ON score_history
  FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();

CREATE TRIGGER trg_elimination_log_append_only
  BEFORE DELETE OR UPDATE ON elimination_log
  FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();

CREATE TRIGGER trg_dict_collision_log_append_only
  BEFORE DELETE OR UPDATE ON dict_collision_log
  FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();

CREATE TRIGGER trg_decision_history_append_only
  BEFORE DELETE OR UPDATE ON decision_history
  FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();

CREATE OR REPLACE FUNCTION fn_sre_append_only()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION
    'submission_registry_events est append-only (INV-R3).';
END;
$$;

CREATE TRIGGER trg_sre_append_only
  BEFORE DELETE OR UPDATE ON submission_registry_events
  FOR EACH ROW EXECUTE FUNCTION fn_sre_append_only();

CREATE OR REPLACE FUNCTION fn_sre_reject_after_close()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_status TEXT;
BEGIN
  SELECT status INTO v_status
  FROM submission_registries
  WHERE registry_id = NEW.registry_id;
  IF v_status = 'closed' THEN
    RAISE EXCEPTION
      'Registre % est fermé. Aucun dépôt possible (INV-R4).',
      NEW.registry_id;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sre_reject_after_close
  BEFORE INSERT ON submission_registry_events
  FOR EACH ROW EXECUTE FUNCTION fn_sre_reject_after_close();

CREATE OR REPLACE FUNCTION fn_sync_registry_on_committee_lock()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status = 'locked' AND OLD.status != 'locked' THEN
    UPDATE submission_registries
    SET status = 'closed', closed_at = now()
    WHERE committee_id = NEW.committee_id
      AND status = 'open';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sync_registry_on_lock
  AFTER UPDATE ON committees
  FOR EACH ROW EXECUTE FUNCTION fn_sync_registry_on_committee_lock();

-- ─────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_documents_case_id
  ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity
  ON audit_log(entity, entity_id);
CREATE INDEX IF NOT EXISTS idx_offer_extractions_case_id
  ON offer_extractions(case_id);
CREATE INDEX IF NOT EXISTS idx_market_signals_item_zone
  ON market_signals(item_id, zone_id);
CREATE INDEX IF NOT EXISTS idx_score_history_case_vendor
  ON score_history(case_id, vendor_id);
CREATE INDEX IF NOT EXISTS idx_mercurials_item_zone_year
  ON mercurials(item_id, zone_id, year);
CREATE INDEX IF NOT EXISTS idx_sre_registry_id
  ON submission_registry_events(registry_id);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_document_id
  ON extraction_jobs(document_id);
```

---

# PARTIE VI — MODÈLES DE DONNÉES

```python
# src/couche_a/models/extraction.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from decimal import Decimal


class ExtractionField(BaseModel):
    """
    RÈGLE-19 : Jamais de valeur nue.
    Tout champ extrait = value + confidence + evidence.
    """
    value: str | int | float | Decimal | bool | None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str | None = None
    evidence_page: int | None = None
    method: str = "llm"


class EvaluationCriterionExtracted(BaseModel):
    label:               ExtractionField
    weight:              ExtractionField
    method:              ExtractionField
    max_score:           ExtractionField
    is_eliminatory:      ExtractionField
    required_document:   ExtractionField
    paliers:             list[dict] | None = None
    formula_description: str | None = None


class TDRExtractionResult(BaseModel):
    project_name:            ExtractionField
    deadline:                ExtractionField
    mission_duration_days:   ExtractionField | None = None
    qualification_threshold: ExtractionField | None = None
    zones:                   list[str]
    evaluation_criteria:     list[EvaluationCriterionExtracted]
    payment_schedule:        list[dict] | None = None
    procedure_type_hint:     ExtractionField
    overall_confidence:      float


class LineItemExtracted(BaseModel):
    description_raw: str
    item_id:         str | None = None
    item_canonical:  str | None = None
    unit_price:      ExtractionField
    quantity:        ExtractionField
    total_price:     ExtractionField
    unit_raw:        str | None = None
    unit_id:         str | None = None


class OfferExtractionResult(BaseModel):
    supplier_name_raw:        ExtractionField
    vendor_id:                str | None = None
    has_nif:                  ExtractionField
    has_rccm:                 ExtractionField
    has_rib:                  ExtractionField
    has_sci_conditions:       ExtractionField
    has_sanctions_cert:       ExtractionField
    total_price:              ExtractionField
    currency:                 ExtractionField
    delivery_delay_days:      ExtractionField | None = None
    validity_days:            ExtractionField | None = None
    chief_researcher_years:   ExtractionField | None = None
    cabinet_studies_count:    ExtractionField | None = None
    team_studies_count:       ExtractionField | None = None
    has_sustainability_proof: ExtractionField | None = None
    line_items:               list[LineItemExtracted]
    overall_confidence:       float
    review_required:          bool
    doc_type_detected:        Literal[
        'offer_technical', 'offer_financial',
        'offer_combined', 'unknown'
    ]


class DocumentClassification(BaseModel):
    file_type:          Literal[
        'native_pdf', 'scan', 'word', 'excel', 'unknown'
    ]
    mime_type:          str
    page_count:         int | None
    has_text:           bool
    language_hint:      str | None
    engine_recommended: Literal[
        'llamaparse', 'azure_doc_intel', 'mistral_ocr',
        'python_docx', 'openpyxl'
    ]


class NormalizationResult(BaseModel):
    raw_text:   str
    item_id:    str | None
    canonical:  str | None
    confidence: float
    method:     Literal[
        'exact', 'fuzzy_auto', 'fuzzy_review', 'unresolved'
    ]


class ProcedureRecognitionResult(BaseModel):
    procedure_type:        Literal[
        'dao', 'rfq', 'rfp_consultance',
        'market_survey', 'unknown'
    ]
    confidence:            float
    signals_detected:      list[str]
    financial_hint_xof:    Decimal | None
    humanitarian_context:  str | None
    requires_human_review: bool


class ProcedureConfig(BaseModel):
    type:                    str
    min_offers_required:     int
    response_period_days:    int
    sealed_bids_required:    bool
    committee_required:      bool
    committee_min_members:   int
    humanitarian_multiplier: float


class MarketSignalResult(BaseModel):
    item_id:         str
    zone_id:         str | None
    price_avg:       Decimal | None
    price_min:       Decimal | None
    price_max:       Decimal | None
    price_median:    Decimal | None
    data_points:     int
    signal_quality:  Literal[
        'empty', 'low', 'medium', 'high', 'not_applicable'
    ]
    formula_version: str
    sources:         list[dict]
    computed_at:     str
    # JAMAIS : recommendation, best_price, suggested_vendor
```

---

# PARTIE VII — LLM ROUTER

```python
# src/couche_a/extraction/llm_router.py
from __future__ import annotations
import httpx
import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    MISTRAL = "mistral"
    CLAUDE  = "claude"
    OPENAI  = "openai"
    LOCAL   = "local"


GEO_CHECK_CACHE: dict[str, tuple[bool, float]] = {}
GEO_CACHE_TTL = 300  # 5 minutes


def _is_claude_available_mali() -> bool:
    """
    Test disponibilité géographique Claude depuis Mali.
    Cache 5 minutes — activation automatique sans redéploiement.
    """
    cache_key = "claude_mali"
    if cache_key in GEO_CHECK_CACHE:
        available, ts = GEO_CHECK_CACHE[cache_key]
        if time.time() - ts < GEO_CACHE_TTL:
            return available
    try:
        r = httpx.get(
            "https://api.anthropic.com/v1/models",
            timeout=5.0,
            headers={"x-api-key": "test"}
        )
        # 401 = endpoint accessible, clé invalide = normal
        # 403 = geo restriction
        available = r.status_code in (200, 401)
    except Exception:
        available = False
    GEO_CHECK_CACHE[cache_key] = (available, time.time())
    logger.info("Claude Mali disponible : %s", available)
    return available


def get_provider_chain() -> list[LLMProvider]:
    """
    Retourne la chaîne de fallback dans l'ordre.
    TIER 1 : Mistral (toujours en premier — disponible Mali)
    TIER 2 : Claude (si disponible géographiquement)
    TIER 3 : OpenAI (fallback universel)
    TIER 4 : Local (résilience offline)
    """
    chain = [LLMProvider.MISTRAL]
    if _is_claude_available_mali():
        chain.append(LLMProvider.CLAUDE)
    chain.append(LLMProvider.OPENAI)
    chain.append(LLMProvider.LOCAL)
    return chain


def get_primary_provider() -> LLMProvider:
    return get_provider_chain()[0]
```

---

# PARTIE VIII — PROTOCOL ANNOTATION

## États documentaires

```
raw_received        Document original terrain.
                    Jamais committé. Jamais exposé. Local uniquement.

anonymized          Données identifiantes remplacées.
                    Script : scripts/anonymize_document.py (créé M10B)
                    Chemin : docs/extraction/fixtures/
                    SHA256 dans annotation_registry (DB)

annotated_validated Fichier JSONL ground_truth créé ET validé
                    par scripts/validate_annotation.py (script livré — voir docs/m12/M12_EXPORT.md)
                    SHA256 du JSONL dans annotation_registry
                    Seul état comptant pour RÈGLE-23
```

## Format JSONL — TDR / DAO / RFQ

```json
{
  "document_file": "anonymised_tdr_001.pdf",
  "document_type": "tdr",
  "annotated_by": "AO",
  "annotated_at": "2026-02-26T10:00:00Z",
  "annotation_duration_minutes": 45,
  "sha256": "À_REMPLIR_APRÈS_validate_annotation.py",
  "ground_truth": {
    "project_name": {
      "value": "Étude de Base PADEM",
      "confidence_expected": 0.98,
      "evidence_hint": "titre page 1"
    },
    "deadline": {
      "value": "2025-04-14",
      "confidence_expected": 0.99,
      "evidence_hint": "14 avril 2025 à 16h00 GMT"
    },
    "qualification_threshold": {
      "value": 60,
      "confidence_expected": 0.97,
      "evidence_hint": "minimum de 60%"
    },
    "procedure_type": {
      "value": "rfp_consultance",
      "confidence_expected": 0.95
    },
    "evaluation_criteria": [
      {
        "label": "Compréhension de la mission",
        "weight": 5,
        "method": "judgment",
        "max_score": 5,
        "is_eliminatory": false
      },
      {
        "label": "Méthodologie et organisation",
        "weight": 30,
        "method": "judgment",
        "max_score": 30,
        "is_eliminatory": false
      },
      {
        "label": "Expérience chef de mission",
        "weight": 10,
        "method": "paliers",
        "max_score": 10,
        "is_eliminatory": false,
        "paliers": [
          {"min_years": 5, "score": 10},
          {"min_years": 3, "score": 7},
          {"min_years": 1, "score": 4}
        ]
      },
      {
        "label": "Expérience cabinet",
        "weight": 5,
        "method": "paliers",
        "max_score": 5,
        "is_eliminatory": false
      },
      {
        "label": "Expérience équipe",
        "weight": 10,
        "method": "paliers",
        "max_score": 10,
        "is_eliminatory": false
      },
      {
        "label": "Durabilité",
        "weight": 10,
        "method": "judgment",
        "max_score": 10,
        "is_eliminatory": false
      },
      {
        "label": "Proposition financière",
        "weight": 30,
        "method": "formula",
        "max_score": 30,
        "is_eliminatory": false,
        "formula_description": "Moins-disant / Prix offre × 30"
      }
    ],
    "payment_schedule": [
      {"tranche": 1, "pct": 40, "condition": "signature contrat"},
      {"tranche": 2, "pct": 40, "condition": "validation draft"},
      {"tranche": 3, "pct": 20, "condition": "validation final"}
    ],
    "zones": ["Bamako", "Mopti", "Tombouctou"]
  }
}
```

## Format JSONL — Offre technique

```json
{
  "document_file": "anonymised_offer_tech_001.pdf",
  "document_type": "offer_technical",
  "annotated_by": "AO",
  "annotated_at": "2026-02-26T11:00:00Z",
  "annotation_duration_minutes": 30,
  "sha256": "À_REMPLIR",
  "ground_truth": {
    "supplier_name_raw":      {"value": "Cabinet Études Mali SARL", "confidence_expected": 0.97},
    "has_nif":                {"value": true,  "confidence_expected": 0.95},
    "has_rccm":               {"value": true,  "confidence_expected": 0.95},
    "has_rib":                {"value": true,  "confidence_expected": 0.90},
    "has_sci_conditions":     {"value": true,  "confidence_expected": 0.85},
    "has_sanctions_cert":     {"value": false, "confidence_expected": 0.80},
    "chief_researcher_years": {"value": 7,     "confidence_expected": 0.85},
    "cabinet_studies_count":  {"value": 5,     "confidence_expected": 0.80},
    "has_sustainability_proof": {"value": true, "confidence_expected": 0.70}
  }
}
```

## Format JSONL — Offre financière

```json
{
  "document_file": "anonymised_offer_fin_001.pdf",
  "document_type": "offer_financial",
  "annotated_by": "AO",
  "annotated_at": "2026-02-26T12:00:00Z",
  "annotation_duration_minutes": 35,
  "sha256": "À_REMPLIR",
  "ground_truth": {
    "total_price":         {"value": 7850000, "currency": "XOF", "confidence_expected": 0.98, "evidence_hint": "montant total TTC"},
    "delivery_delay_days": {"value": 45, "confidence_expected": 0.85},
    "validity_days":       {"value": 90, "confidence_expected": 0.80},
    "line_items": [
      {"description_raw": "Honoraires chef de mission",  "quantity": 1, "unit_price": 4500000, "total_price": 4500000},
      {"description_raw": "Honoraires équipe terrain",   "quantity": 3, "unit_price": 800000,  "total_price": 2400000},
      {"description_raw": "Frais déplacement",           "quantity": 1, "unit_price": 950000,  "total_price": 950000}
    ]
  }
}
```

## Procédure annotation étape par étape

```
1. Ouvrir le document en entier avant d'annoter
   (les infos critiques sont souvent en page 8)

2. Créer le fichier JSONL :
   docs/extraction/annotations/{type}_{ref}_{YYYYMMDD}.jsonl

3. Remplir ground_truth champ par champ

4. Niveaux confidence :
   0.95+      information claire et explicite
   0.80-0.94  présente mais formulée indirectement
   0.65-0.79  inférable avec effort
   < 0.65     null obligatoire dans value

5. Si hésitation sur valeur → null
   Si hésitation sur confidence → prendre la plus basse
   Jamais annoter de mémoire — document ouvert obligatoire

6. Valider :
   python scripts/validate_annotation.py fichier.jsonl

7. Copier le SHA256 retourné dans le champ sha256

8. Enregistrer dans annotation_registry (DB)

TEMPS ESTIMÉS :
   TDR simple (5-10 critères)    30-45 min
   DAO complexe (lots multiples) 60-90 min
   Offre technique               20-30 min
   Offre financière              25-40 min

SEUILS QUALITÉ (RÈGLE-23) :
   Avant M12 : ≥ 15 annotated_validated
   Avant M15 : ≥ 50 annotated_validated
   Precision recall ≥ 0.70 sur critères avant valider M12
```

---

# PARTIE IX — FORMULE MARKET SIGNAL V1.0

```
PONDÉRATION SOURCES
  mercuriale_official  0.50
  market_survey        0.35
  decision_history     0.15

FRAÎCHEUR — COEFFICIENT MULTIPLICATEUR
  Même année   1.00
  1 an         0.90
  2 ans        0.75
  3 ans        0.55
  > 3 ans      0.30

QUALITÉ SIGNAL
  high    data_points ≥ 10 ET sources ≥ 2
  medium  data_points ≥ 4
  low     data_points ≥ 1
  empty   data_points = 0

OUTLIERS
  IQR multiplier 2.5
  Prix hors [Q1 - 2.5×IQR, Q3 + 2.5×IQR] → exclus avant calcul

SOURCE UNIQUE (ex : zone isolée)
  1 seule source → signal_quality = 'low'
  Calcul identique — flag quality seulement

RÈGLES ABSOLUES
  Zéro recommendation
  Zéro best_price
  Zéro suggested_vendor
  Résultat identique pour mêmes données (reproductible)
  Modification → version 2.0 + nouvel ADR

formula_version = "1.0" gravé dans market_signals.formula_version
```

---

# PARTIE X — DATA READINESS

## Actifs et état de propreté

```
MERCURIALES OFFICIELLES
  État      : brutes — Excel multi-onglets non normalisé
  Risques   : libellés non uniformes entre années
              unités hétérogènes (L vs litre vs litres)
              prix aberrants possibles (erreurs saisie terrain)
  Action M5 : identifier colonnes manuellement
              documenter dans docs/data/MERCURIALE_COLUMN_MAP.md
              ingérer brut — normalisation = M6

FOURNISSEURS SCI EXCEL
  État      : semi-structuré — nom + zone + catégorie + contacts
  Risques   : doublons noms légèrement différents
              NIF/RCCM absents sur certaines lignes
              zones codées de façon hétérogène
  Action M4 : mapping colonnes → schéma vendors DB
              doublons flaggés pour review humaine — jamais auto-fusionnés

DOCUMENTS RÉELS DAO/RFQ/OFFRES
  État      : bruts terrain — noms fournisseurs et prix visibles
  Risques   : données identifiantes présentes
              qualité scan variable
              formats mixtes (Word / PDF natif / scan)
  Action M10B : anonymisation OBLIGATOIRE avant tout commit
                vérification manuelle post-anonymisation

100 DOSSIERS DAO M15
  État      : bruts terrain
  Action M15 : anonymisation batch
               sample 20 traités ET métriques validés avant les 80 restants
```

## Risques de contamination

```
RISQUE-D1  Scan illisible < 150 DPI
           → confidence très basse → review_required → géré

RISQUE-D2  Prix aberrant mercuriale (erreur saisie terrain)
           → outlier IQR ×2.5 → exclu avant calcul → géré

RISQUE-D3  Deux fournisseurs noms très proches
           → RÈGLE-26 (3 conditions) + dict_collision_log → géré

RISQUE-D4  Contamination données réelles dans repo
           → RÈGLE-15 + anonymize_document.py obligatoire → géré

DOCTRINE
  La data entre dans l'état où elle est.
  Le système s'adapte au réel — il ne corrige pas la source.
  Les imperfections sont tracées, pas cachées.
  Les doublons sont flaggués, pas inventés.
  Les prix aberrants sont exclus, pas modifiés.
```

---

# PARTIE XI — MILESTONES COMPLETS

## Table de vérité Alembic

| Milestone | Head après merge |
|---|---|
| M0 | 035 inchangé — confirmer par PROBE |
| M0B | 036_db_hardening |
| M1B | 037_audit_hash_chain |
| M3 | 038_seed_geo_master_mali |
| M4 | 039_seed_vendors_mali |
| M5 | 040_mercuriale_ingest |
| M6 | 041_procurement_dictionary |
| M8 | 042_market_surveys |
| M10A | 043_extraction_jobs_async |
| M11 | 044_ingestion_real_schema |
| M14 | 045_evaluation_documents |
| M16A | 046_submission_registry |
| M16B | 047_committee_seal_complete |

Invariant : alembic heads → exactement 1 ligne après chaque merge.

## Séquence et charge

```
PHASE 0 — STABILISATION
  M0    FIX-CI & REPO TRUTH SYNC      2-3j
  M0B   DB HARDENING                  2j

PHASE 1 — SÉCURITÉ
  M1    SECURITY BASELINE             3j
  M1B   AUDIT HASH CHAIN              2j

PHASE 2 — UNIFICATION
  M2    UNIFY SYSTEM                  3j

PHASE 3 — DONNÉES RÉELLES
  M3    GEO MASTER MALI               0.5j   ← base cesse d'être vide
  M4    VENDOR IMPORTER               1j
  M5    MERCURIALE INGEST             1.5j
  M6    DICTIONARY BUILD              1.5j
  M7    DICT ENRICHMENT               1j
  M8    MARKET SURVEY                 2j
  M9    MARKET SIGNAL                 2j     ← Couche B vivante

PHASE 4 — EXTRACTION
  M10A  GATEWAY STACK + MOCKS         2j
  M10B  GATEWAY CALIBRATION           1j     ★ 3 docs annotés (2-3h AO)
  M11   INGESTION RÉELLE STC          3j     ★ 15 annotated_validated (8-12h AO)
  M12   PROCEDURE RECOGNIZER          2j
  M13   PROFILES SCI + DGMP           2j

PHASE 5 — ÉVALUATION
  M14   EVALUATION ENGINE             3j
  M15   PIPELINE E2E 100 DOSSIERS     3j     ★ sample 20 + métriques

PHASE 6 — COMITÉ + REGISTRE
  M16A  SUBMISSION REGISTRY           2j
  M16B  COMMITTEE + SEAL              2j

PHASE 7 — GÉNÉRATION DOCUMENTS
  M17   CBA GEN                       2j
  M18   PV GEN                        2j

PHASE 8 — PRODUCTION
  M19   OBSERVABILITÉ                 2j
  M20   PERFORMANCE GATES CI          1j
  M21   DÉPLOIEMENT MALI              3j

CHARGE CODE (agent)      : 51 jours ouvrés
CHARGE ANNOTATION (AO)  : ~25 heures sur M10B + M11 + M15
DURÉE RÉELLE ESTIMÉE    : ~70 jours (facteur terrain Mali ×1.4)
```

## M15 — Métriques de validation obligatoires

```
Les 100 dossiers ne sont pas un test de charge.
Ils sont une validation stratégique opposable.

MÉTRIQUES CALCULÉES :
  coverage_extraction   % documents overall_confidence > 0
  unresolved_rate       % line_items non matchés au dictionnaire
  vendor_match_rate     % supplier_name_raw matchés à vendors
  review_queue_rate     % documents en review_required
  signal_quality_cov    % items avec signal ≠ 'empty'
  drift_by_category     variance prix extrait vs signal marché

SEUILS DE VALIDATION :
  coverage_extraction  ≥ 80%
  unresolved_rate      ≤ 25%
  vendor_match_rate    ≥ 60%
  review_queue_rate    ≤ 30%

Si seuils non atteints → M15 = NOT DONE
Ajuster → relancer batch → remesurer
Rapport : docs/reports/M15_validation_report.md
```

---

# PARTIE XII — MANDAT M0

```
# MANDAT AGENT — M0 FIX-CI & REPO TRUTH SYNC
Version    : 1.1
Milestone  : M0
Prérequis  : aucun
Migration  : AUCUNE
Head début : à confirmer par PROBE
Head fin   : 035 inchangé
Branche    : feat/m0-fix-ci

## CONTEXTE AGENT
Lire avant de commencer :
  docs/freeze/DMS_V4.1.0_FREEZE.md (ce document)
  TECHNICAL_DEBT.md (créer si absent)
  alembic/versions/ (lister tous les fichiers présents)

## PÉRIMÈTRE FERMÉ

CRÉÉS :
  docs/ci/ci_diagnosis.txt
  TECHNICAL_DEBT.md (si absent)

MODIFIÉS (corrections uniquement) :
  src/**/*.py   erreurs CI existantes uniquement
  tests/**/*.py assertions cassées uniquement

INTERDITS :
  alembic/versions/*              aucune migration
  src/couche_a/extraction/*       stubs restent stubs — M10A les tue
  src/couche_b/*                  hors scope M0
  Tout fichier non listé ci-dessus

## HORS SCOPE EXPLICITE
  Nouvelles fonctionnalités
  Modifications schéma DB
  Nouveaux tests
  Suppression stubs et time.sleep (réservé M10A)
  Fichiers extraction / scoring / comité / annotation

## SÉQUENCE

ÉTAPE 0 — PROBE OBLIGATOIRE
  mkdir -p docs/ci
  alembic heads 2>&1 | tee docs/ci/ci_diagnosis.txt
  echo "---PYTEST---" >> docs/ci/ci_diagnosis.txt
  pytest --tb=long -v 2>&1 | tee -a docs/ci/ci_diagnosis.txt
  → Poster résultat. Attendre validation humaine.

ÉTAPE 1 — CLASSIFIER
  import_error    : [fichier:ligne]
  schema_mismatch : [table.colonne]
  logic_error     : [assertion:attendu vs reçu]
  fixture_residue : [table:données parasites]
  → Écrire dans TECHNICAL_DEBT.md "Erreurs M0 identifiées"

ÉTAPE 2 — CORRIGER DANS L'ORDRE
  1. import_errors
  2. schema_mismatches (vérifier nom réel avant tout SQL)
  3. logic_errors
  4. fixture_residue → SQL purge

ÉTAPE 3 — SCAN STATIQUE (INVENTAIRE UNIQUEMENT)
  grep -rn "time\.sleep" src/ | grep -v "test_"
  grep -rn "return {}" src/couche_a/
  grep -rn "winner\|rank\|recommendation" src/
  → TECHNICAL_DEBT.md section "Stubs actifs"
  → NE PAS supprimer. Inventorier uniquement.

ÉTAPE 4 — VÉRIFICATION
  pytest --tb=short -v 2>&1 | tail -30
  alembic heads
  alembic upgrade head

## SIGNAUX STOP
  STOP-1 : alembic heads > 1 ligne → poster + attendre
  STOP-2 : correction nécessite modifier migration → interdit + attendre
  STOP-3 : > 5 fichiers tests à modifier → poster liste + attendre
  STOP-4 : table DB absente → ne pas créer + attendre
  STOP-5 : logique métier ambiguë → ne pas interpréter + attendre

## LIVRABLES
  L1 : docs/ci/ci_diagnosis.txt
       alembic heads + pytest complet
  L2 : TECHNICAL_DEBT.md
       Stubs actifs · FK manquantes · Tables ambiguës
       Erreurs M0 corrigées · Tests absents · Hors scope beta

## CONDITION DONE — BINAIRE
  [ ] pytest → 0 failed / 0 errors
  [ ] alembic heads → exactement 1 résultat = 035
  [ ] alembic upgrade head DB vierge → 0 erreur
  [ ] TECHNICAL_DEBT.md committé toutes sections remplies
  [ ] docs/ci/ci_diagnosis.txt committé
  [ ] grep "time\.sleep" src/ → inventorié TECHNICAL_DEBT.md (pas supprimé)
  [ ] grep "winner\|rank\|recommendation" src/ → 0
  [ ] AUCUNE migration créée
  [ ] AUCUN fichier hors périmètre modifié
  [ ] CI verte
  [ ] Tag : v4.1.0-m0-done

## DEPLOY
  git tag v4.1.0-m0-done
  git push origin feat/m0-fix-ci --tags
  PR → merge main
  Railway deploy staging automatique
  Smoke test : healthcheck + alembic heads + pytest smoke
  Smoke vert → deploy production
  30min staging minimum avant production
```

---

# PARTIE XIII — HASHES DE VÉRIFICATION

```
SHA256 fichier : [GÉNÉRÉ PAR AGENT APRÈS COMMIT]
SHA256 commit  : [GÉNÉRÉ PAR AGENT APRÈS COMMIT]
Date hash      : [GÉNÉRÉE PAR AGENT APRÈS COMMIT]

Commande de vérification :
  sha256sum docs/freeze/DMS_V4.1.0_FREEZE.md

Instruction à l'agent pour générer les hashes :
  sha256sum docs/freeze/DMS_V4.1.0_FREEZE.md
  git rev-parse v4.1.0-freeze

Ce document est gelé après hash.
Tout amendement → docs/freeze/DMS_V4.1.1_PATCH.md
Ce fichier n'est plus jamais modifié.
```
