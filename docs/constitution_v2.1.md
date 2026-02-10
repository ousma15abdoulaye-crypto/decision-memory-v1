# 🚀 CONSTITUTION DMS V2.1 — PRODUCTION-READY SPECIFICATION

**Date:** 10 février 2026  
**Statut:** FROZEN FOR EXECUTION  
**Auteur:** Abdoulaye Ousmane (Founder & Tech Lead)  
**Mode:** Online-only | Excel-killer | Production-first  
**Cible:** ONGs internationales | États africains | Grandes entreprises  

***

## § 0 — MANIFESTE FONDATEUR

### Vision produit

Decision Memory System (DMS) existe pour **éliminer le chaos documentaire dans les processus décisionnels compétitifs** (procurement, appels d'offres, due diligence) en Afrique de l'Ouest et au-delà.

**Ce que DMS fait:**
- Centralise dossiers, preuves, décisions, artefacts (Couche A)
- Crée une mémoire organisationnelle exploitable sans effort (append-only, traçable, auditable)
- Construit la **première base de données market intelligence structurée d'Afrique de l'Ouest** (Couche B) comme avantage compétitif durable

**Ce que DMS remplace:**
- Tableaux Excel artisanaux dispersés sur 50 laptops
- Folders partagés où personne ne retrouve rien
- Mémoire tribale perdue à chaque rotation RH
- Benchmarks prix inexistants ou obsolètes

### Règle d'or non négociable

**Si DMS n'est pas plus rapide, plus fluide et plus puissant qu'Excel, il ne vaut rien.**

Chaque feature doit passer le test:
- ⏱️ **Vitesse:** < 2 secondes du clic à l'action
- 🎯 **Clarté:** Zéro confusion sur ce que fait le bouton
- 💪 **Puissance:** Fait quelque chose qu'Excel ne peut pas faire (ou fait en 10x moins de temps)

### Positionnement stratégique

**DMS n'est pas un ERP.**  
DMS n'est pas un contract management system.  
DMS n'est pas un outil de suivi d'exécution.

**DMS est une plateforme décisionnelle:**
- Avant l'attribution: structuration, extraction, mémoire
- Pendant la décision: contexte marché, alertes factuelles
- Après la décision: capitalisation automatique, zero effort

***

## § 1 — STACK TECHNIQUE (Février 2026)

### 1.1 Philosophie tech

**Online-only. Point final.**

Pas de "mode dégradé offline" en V1. Pas de "on verra après". Les organisations cibles (Save the Children, UNICEF, gouvernements, mines) ont:
- Connexion internet stable (bureaux capitales)
- Backup 4G/Starlink si coupures
- Budgets IT pour infrastructure moderne

**Si un client n'a pas Internet stable, DMS n'est pas pour lui en 2026.**  
(Peut-être en 2027 avec un cache local read-only, mais pas maintenant.)

### 1.2 Backend: FastAPI + PostgreSQL

**Stack Python:**
```toml
# pyproject.toml
[project]
name = "dms-api"
version = "2.1.0"
requires-python = ">=3.11"

dependencies = [
    # Core
    "fastapi==0.110.0",
    "uvicorn[standard]==0.27.1",
    "pydantic==2.6.1",
    "pydantic-settings==2.1.0",
    
    # Database
    "sqlalchemy==2.0.27",
    "alembic==1.13.1",
    "psycopg[binary,pool]==3.1.18",
    "asyncpg==0.29.0",  # Async PostgreSQL
    
    # Document processing
    "pypdf==4.0.1",
    "python-docx==1.1.0",
    "openpyxl==3.1.2",
    "python-multipart==0.0.9",
    
    # Security & Auth
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "python-multipart==0.0.9",
    
    # Performance
    "redis[hiredis]==5.0.1",
    "orjson==3.9.15",  # JSON ultra-rapide
    
    # Monitoring
    "sentry-sdk[fastapi]==1.40.6",
    "structlog==24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest==8.0.0",
    "pytest-cov==4.1.0",
    "pytest-asyncio==0.23.5",
    "httpx==0.26.0",
    "faker==23.1.0",
]
```

**Pourquoi FastAPI vs alternatives:**

| Critère | FastAPI | Django | Flask | Node.js |
|---------|---------|--------|-------|---------|
| **Vitesse** | 🟢 Async natif | 🔴 Sync | 🟡 Sync | 🟢 Async |
| **Type safety** | 🟢 Pydantic | 🟡 Django ORM | 🔴 Aucun | 🟡 TypeScript |
| **Auto-docs** | 🟢 Swagger UI | 🔴 Manuel | 🔴 Manuel | 🟡 Swagger manuel |
| **Time to market** | 🟢 Rapide | 🟡 Lourd | 🟢 Rapide | 🟡 Setup complexe |
| **Écosystème AI** | 🟢 Python | 🟢 Python | 🟢 Python | 🔴 Limité |

**Décision:** FastAPI est le seul choix rationnel pour un founder solo avec agents AI en février 2026.

***

### 1.3 Frontend: React + TypeScript + Vite

**Stack moderne:**
```json
{
  "name": "dms-frontend",
  "version": "2.1.0",
  "type": "module",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    
    "//": "Data fetching & state",
    "@tanstack/react-query": "^5.20.5",
    "@tanstack/react-table": "^8.12.0",
    "zustand": "^4.5.0",
    
    "//": "Forms & validation",
    "react-hook-form": "^7.50.1",
    "zod": "^3.22.4",
    "@hookform/resolvers": "^3.3.4",
    
    "//": "UI Components (shadcn/ui base)",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-select": "^2.0.0",
    "@radix-ui/react-toast": "^1.1.5",
    "@radix-ui/react-tooltip": "^1.0.7",
    "cmdk": "^0.2.1",
    
    "//": "Styling",
    "tailwindcss": "^3.4.1",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.1",
    
    "//": "Icons & assets",
    "lucide-react": "^0.323.0",
    
    "//": "Utilities",
    "axios": "^1.6.7",
    "date-fns": "^3.3.1",
    "react-dropzone": "^14.2.3"
  },
  "devDependencies": {
    "@vitejs/plugin-react-swc": "^3.5.0",
    "vite": "^5.1.0",
    "typescript": "^5.3.3",
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35",
    "eslint": "^8.56.0",
    "prettier": "^3.2.5"
  }
}
```

**Pourquoi React vs alternatives:**

| Critère | React | Vue | Svelte | Angular |
|---------|-------|-----|--------|---------|
| **Talent pool** | 🟢 Énorme | 🟡 Moyen | 🔴 Petit | 🟡 Moyen |
| **Écosystème** | 🟢 Mature | 🟡 OK | 🔴 Jeune | 🟢 Mature |
| **Performance** | 🟢 Virtual DOM | 🟢 Réactif | 🟢 Compilé | 🟡 Lourd |
| **Type safety** | 🟢 TypeScript | 🟢 TypeScript | 🟢 TypeScript | 🟢 TypeScript |
| **Learning curve** | 🟡 Moyenne | 🟢 Facile | 🟢 Facile | 🔴 Difficile |
| **Agent AI familiarity** | 🟢 Claude/GPT excellent | 🟡 OK | 🔴 Limité | 🟡 OK |

**Décision:** React + TypeScript + shadcn/ui = standard industrie 2026, agents AI ultra-performants dessus.

***

### 1.4 Database: PostgreSQL 16

**Architecture schemas:**
```sql
CREATE DATABASE dms_production;

-- Schema separation (logical isolation)
CREATE SCHEMA couche_a;  -- Operational (cases, artifacts, decisions)
CREATE SCHEMA couche_b;  -- Market Intelligence (vendors, items, signals)
CREATE SCHEMA system;    -- Auth, users, audit logs

-- Extensions critiques
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Fuzzy search
CREATE EXTENSION IF NOT EXISTS "btree_gin";    -- Index performance
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";  -- Query monitoring
```

**Pourquoi PostgreSQL vs alternatives:**

| Critère | PostgreSQL | MySQL | MongoDB | SQLite |
|---------|-----------|-------|---------|--------|
| **JSONB natif** | 🟢 Performant | 🟡 JSON basique | 🟢 Natif | 🔴 Aucun |
| **Full-text search** | 🟢 Excellent | 🟡 Limité | 🟡 Limité | 🔴 Basique |
| **Transactions** | 🟢 ACID complet | 🟢 ACID | 🔴 Limité | 🟢 ACID |
| **Scalabilité** | 🟢 100M+ rows | 🟢 100M+ rows | 🟢 Illimité | 🔴 Single file |
| **GIS (geo queries)** | 🟢 PostGIS | 🔴 Aucun | 🟡 OK | 🔴 Aucun |
| **Managed services** | 🟢 Partout | 🟢 Partout | 🟢 Atlas | 🔴 N/A |

**Décision:** PostgreSQL est le standard pour applications data-intensive modernes.

***

### 1.5 Déploiement: Railway (MVP) → AWS (Scale)

**Phase MVP (Semaines 1-8):**

**Railway.app:**
- Deploy from GitHub en 1 clic
- PostgreSQL managed inclus
- Auto-scaling 0-10 instances
- $20/mois → $100/mois selon usage
- Perfect pour founder solo

**Architecture Railway:**
```yaml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[services]]
name = "dms-api"
source = "backend/"

[[services]]
name = "dms-frontend"
source = "frontend/"
```

**Phase Production (Post-MVP, Mois 3+):**

**AWS Architecture:**
```
┌─────────────────────────────────────────────────┐
│              CloudFront (CDN)                   │
│              + Route53 (DNS)                    │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────────┐        ┌───────▼────────┐
│   S3       │        │  ALB           │
│  (Static)  │        │  (Load Balancer)│
└────────────┘        └───────┬────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼──────┐    ┌───────▼──────┐
            │  ECS Fargate │    │  ECS Fargate │
            │  (API x2)    │    │  (API x2)    │
            └───────┬──────┘    └───────┬──────┘
                    └─────────┬─────────┘
                              │
                    ┌─────────▼──────────┐
                    │  RDS PostgreSQL    │
                    │  (Multi-AZ)        │
                    └────────────────────┘
```

**Coûts estimés:**
- MVP Railway: $50-100/mois
- Production AWS: $300-500/mois (jusqu'à 10K users)

***

## § 2 — PRINCIPES DE PERFORMANCE

### 2.1 SLA Produit (Contraintes non négociables)

| Métrique | Objectif | Test |
|----------|----------|------|
| **Page load (Registre)** | < 1.5s | Lighthouse score > 90 |
| **API response (liste)** | < 200ms P95 | Load test 100 req/s |
| **Recherche** | < 100ms "instant feel" | Index DB + cache Redis |
| **Upload document** | < 5s pour 10MB PDF | Streaming upload |
| **Export Excel** | < 3s pour 500 rows | Génération async si > 1000 rows |

### 2.2 Règles techniques obligatoires

**Backend:**
- ✅ Pagination serveur (jamais "load all")
- ✅ Index DB sur toutes colonnes filtrées/triées
- ✅ Cache Redis pour Couche B (TTL 1h)
- ✅ Async I/O (FastAPI async endpoints)
- ✅ Connection pooling PostgreSQL (max 20)

**Frontend:**
- ✅ Virtualized lists (TanStack Table)
- ✅ Code splitting (React.lazy)
- ✅ Optimistic UI updates (TanStack Query)
- ✅ Debounced search (300ms)
- ✅ Image lazy loading

**Database:**
- ✅ Index composites sur requêtes fréquentes
- ✅ EXPLAIN ANALYZE sur toutes queries lentes
- ✅ Partitioning si > 10M rows (post-MVP)
- ✅ Vacuum automatique configuré

### 2.3 Excel-killer checklist

Pour chaque feature, valider:

- [ ] **Plus rapide qu'Excel?** (chronométré)
- [ ] **Plus clair qu'Excel?** (test utilisateur 5 min)
- [ ] **Fait quelque chose qu'Excel ne peut pas?** (AI, collaboration, mémoire)

Si 3/3 ✅ → Ship  
Si 2/3 → Améliorer  
Si 1/3 → Rejeter

***

## § 3 — COUCHE B: MARKET INTELLIGENCE

### 3.1 Vision stratégique

**Couche B n'est pas une feature. C'est l'avantage compétitif durable de DMS.**

En 2026, **aucune base de données structurée de prix marché n'existe en Afrique de l'Ouest** pour le procurement humanitaire/gouvernemental.

**DMS va créer cette base. Et la protéger.**

**Valeur pour les clients:**
- ONGs: "Combien coûte vraiment un sac de ciment à Bamako en février?"
- États: "Quel fournisseur livre vraiment en 15 jours à Gao?"
- Mines: "Mes prix sont-ils compétitifs vs marché régional?"

**Valeur pour DMS:**
- Lock-in: Plus tu utilises DMS, plus ta mémoire marché est riche
- Network effects: Plus d'orgs = plus de signals = meilleure intelligence
- Monetization: Market Intelligence Premium (rapports, benchmarks) = $$$

### 3.2 Architecture cognitive

```
┌──────────────────────────────────────────────────────────┐
│                      COUCHE B                            │
│              "Le collègue expérimenté"                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  FONCTION: Créer la base de données marché unique       │
│            d'Afrique de l'Ouest                          │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  SOURCE 1: INGESTION AUTO (post-décision)          │ │
│  ├────────────────────────────────────────────────────┤ │
│  │                                                    │ │
│  │  Trigger: POST /api/cases/{id}/decide             │ │
│  │           ↓                                        │ │
│  │  Extract: Awarded offer → items + prices          │ │
│  │           ↓                                        │ │
│  │  Resolve: vendor_name → vendor_id (canonical)     │ │
│  │           item_desc → item_id                     │ │
│  │           unit_text → unit_id                     │ │
│  │           location → geo_id                       │ │
│  │           ↓                                        │ │
│  │  Insert: market_signals (1 signal/item)           │ │
│  │                                                    │ │
│  │  🔹 100% automatique                              │ │
│  │  🔹 Zero effort utilisateur                       │ │
│  │  🔹 Non-bloquant (async task)                     │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  SOURCE 2: IMPORT MERCURIALS (manuel mensuel)      │ │
│  ├────────────────────────────────────────────────────┤ │
│  │                                                    │ │
│  │  Interface: POST /api/mercurials/import           │ │
│  │  Format: CSV structuré                            │ │
│  │                                                    │ │
│  │  Colonnes:                                         │ │
│  │  - category (Fournitures, BTP, etc.)              │ │
│  │  - item (Ciment Portland 50kg)                    │ │
│  │  - zone (Bamako, Kayes, etc.)                     │ │
│  │  - price (6500)                                    │ │
│  │  - unit (FCFA/sac)                                │ │
│  │  - date (2026-02-01)                              │ │
│  │  - source (Mercurial BTP Mali)                    │ │
│  │                                                    │ │
│  │  🔹 Rôle: Procurement manager                     │ │
│  │  🔹 Fréquence: Mensuelle/trimestrielle            │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  SOURCE 3: MARKET SURVEY (interface web MVP)       │ │
│  ├────────────────────────────────────────────────────┤ │
│  │                                                    │ │
│  │  Interface: DMS web app (écran dédié)             │ │
│  │  Workflow: Propose-only pattern                   │ │
│  │                                                    │ │
│  │  Utilisateur saisit:                               │ │
│  │  ├─ Date observation                              │ │
│  │  ├─ Lieu (autocomplete geo)                       │ │
│  │  ├─ Items + prix (autocomplete catalog)           │ │
│  │  └─ Vendor (autocomplete ou "proposer nouveau")   │ │
│  │                                                    │ │
│  │  Nouvelles entités → status='proposed'            │ │
│  │  Admin valide → status='active'                   │ │
│  │  Market signals → status='pending'                │ │
│  │                                                    │ │
│  │  🔹 Accès: Procurement officers + MEAL teams      │ │
│  │  🔹 Mobile-responsive obligatoire                 │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  SOURCE 4: MEAL APP (Android, POST-MVP V1.1)       │ │
│  ├────────────────────────────────────────────────────┤ │
│  │                                                    │ │
│  │  App ultra-légère (Flutter)                        │ │
│  │  Écran unique: Item + Prix + Lieu + Photo         │ │
│  │  Offline-first → sync background                   │ │
│  │                                                    │ │
│  │  🔹 Utilisateurs: MEAL teams terrain              │ │
│  │  🔹 Aucun accès autres fonctions DMS              │ │
│  │  🔹 Anonymisation: "source MEAL" uniquement       │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

***

## § 4 — CATALOGS MAÎTRES (Référentiels canoniques)

### 4.1 Philosophie: Propose-only pattern

**Problème résolu:**  
Dans procurement, les noms varient infiniment:
- "SARL BTP Constructions" = "Sarl Btp Construction" = "BTP Construct" = même entreprise
- "Ciment Portland 50kg" = "Ciment 50kg Portland" = "Ciment CPA 50kg" = même produit

**Solution DMS:**  
1. **1 entité canonique** par vendor/item/unit/geo
2. **N aliases** possibles (variantes orthographiques)
3. **Matching automatique** (exact → fuzzy → propose new)
4. **Validation humaine** pour nouvelles propositions (prevent chaos)

**Workflow:**
```
User saisit "SARL BTP Bamako"
         ↓
Resolver cherche:
  1. Canonical exact match → TROUVÉ: vendor_id=VND_ABC123
  2. Alias match → TROUVÉ: alias "Sarl Btp Bamako" → vendor_id=VND_ABC123
  3. Fuzzy match (>85%) → SUGGESTIONS: "SARL BTP Constructions" (92%)
  4. Aucun match → PROPOSE NEW: status='proposed', attente validation admin
```

***

### 4.2 Vendors (Fournisseurs)

```sql
CREATE TABLE couche_b.vendors (
    vendor_id VARCHAR(20) PRIMARY KEY,  -- VND_01HQRST...
    canonical_name VARCHAR(200) NOT NULL UNIQUE,
    legal_name VARCHAR(300),
    registration_number VARCHAR(50),  -- RCCM, NINEA, etc.
    tax_id VARCHAR(50),  -- NIF, TIN
    vendor_type VARCHAR(50),  -- local|national|international|individual
    status VARCHAR(20) DEFAULT 'proposed',  -- proposed|active|rejected|inactive
    contact_json JSONB,  -- {email, phone, address, city, country}
    tags TEXT[],  -- ['btp', 'fournitures', 'transport']
    metadata_json JSONB,  -- Champs custom extensibles
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE TABLE couche_b.vendor_aliases (
    alias_id VARCHAR(20) PRIMARY KEY,
    vendor_id VARCHAR(20) REFERENCES couche_b.vendors(vendor_id),
    alias_name VARCHAR(200) NOT NULL,
    source VARCHAR(50) NOT NULL,  -- dao_submission|manual_entry|import
    confidence VARCHAR(20) DEFAULT 'LIKELY',  -- EXACT|LIKELY|POSSIBLE
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE couche_b.vendor_events (
    event_id VARCHAR(20) PRIMARY KEY,
    vendor_id VARCHAR(20) REFERENCES couche_b.vendors(vendor_id),
    event_type VARCHAR(50) NOT NULL,  -- proposed|activated|merged|status_change
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE INDEX idx_vendors_status ON couche_b.vendors(status);
CREATE INDEX idx_vendor_aliases_name ON couche_b.vendor_aliases USING gin(alias_name gin_trgm_ops);
```

**Seed data (Mali top vendors):**
```sql
INSERT INTO couche_b.vendors (vendor_id, canonical_name, vendor_type, status) VALUES
('VND_SOGELEC', 'Société Générale d''Électricité (SOGELEC)', 'national', 'active'),
('VND_SOMAPEP', 'Société Malienne de Peinture et d''Entretien (SOMAPEP)', 'national', 'active'),
('VND_COVEC', 'China Overseas Engineering Group (COVEC Mali)', 'international', 'active');
```

***

### 4.3 Items (Produits/Services)

```sql
CREATE TABLE couche_b.items (
    item_id VARCHAR(20) PRIMARY KEY,  -- ITM_01HQRST...
    canonical_name VARCHAR(300) NOT NULL UNIQUE,
    unspsc_code VARCHAR(20),  -- Standard classification
    category VARCHAR(100),  -- fournitures|btp|services|medical
    description TEXT,
    specifications_json JSONB,  -- Specs techniques standards
    status VARCHAR(20) DEFAULT 'proposed',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE TABLE couche_b.item_aliases (
    alias_id VARCHAR(20) PRIMARY KEY,
    item_id VARCHAR(20) REFERENCES couche_b.items(item_id),
    alias_name VARCHAR(300) NOT NULL,
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_items_category ON couche_b.items(category);
CREATE INDEX idx_item_aliases_name ON couche_b.item_aliases USING gin(alias_name gin_trgm_ops);
```

**Seed data (items communs Mali):**
```sql
INSERT INTO couche_b.items (item_id, canonical_name, category, status) VALUES
('ITM_CIM50', 'Ciment Portland CPA 42.5 - Sac 50kg', 'btp', 'active'),
('ITM_FER12', 'Fer à béton haute adhérence Ø12mm', 'btp', 'active'),
('ITM_RIZ25', 'Riz brisé parfumé - Sac 25kg', 'fournitures', 'active');
```

***

### 4.4 Units (Unités de mesure)

```sql
CREATE TABLE couche_b.units (
    unit_id VARCHAR(20) PRIMARY KEY,  -- UNT_KG, UNT_SAC...
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100),
    category VARCHAR(50),  -- weight|volume|length|count|area
    conversion_to_base DECIMAL(15,6),  -- Pour conversions (ex: 1 tonne = 1000 kg)
    base_unit_id VARCHAR(20) REFERENCES couche_b.units(unit_id),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE couche_b.unit_aliases (
    alias_id VARCHAR(20) PRIMARY KEY,
    unit_id VARCHAR(20) REFERENCES couche_b.units(unit_id),
    alias_text VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_units_category ON couche_b.units(category);
```

**Seed data (unités standard):**
```sql
INSERT INTO couche_b.units (unit_id, symbol, name, category, conversion_to_base, base_unit_id) VALUES
('UNT_KG', 'kg', 'Kilogramme', 'weight', 1.0, NULL),
('UNT_TONNE', 'tonne', 'Tonne', 'weight', 1000.0, 'UNT_KG'),
('UNT_L', 'L', 'Litre', 'volume', 1.0, NULL),
('UNT_M3', 'm³', 'Mètre cube', 'volume', 1000.0, 'UNT_L'),
('UNT_M', 'm', 'Mètre', 'length', 1.0, NULL'),
('UNT_M2', 'm²', 'Mètre carré', 'area', 1.0, NULL'),
('UNT_PIECE', 'pièce', 'Pièce', 'count', 1.0, NULL'),
('UNT_SAC', 'sac', 'Sac', 'count', 1.0, NULL'),
('UNT_CARTON', 'carton', 'Carton', 'count', 1.0, NULL');

INSERT INTO couche_b.unit_aliases (alias_id, unit_id, alias_text) VALUES
('UAL_KG1', 'UNT_KG', 'kilogramme'),
('UAL_KG2', 'UNT_KG', 'Kg'),
('UAL_SAC1', 'UNT_SAC', 'sacs'),
('UAL_SAC2', 'UNT_SAC', 'Sac 50kg');
```

***

### 4.5 Geo Master (Zones géographiques)

```sql
CREATE TABLE couche_b.geo_master (
    geo_id VARCHAR(20) PRIMARY KEY,  -- GEO_BAMAKO, GEO_ML_R01...
    canonical_name VARCHAR(100) NOT NULL UNIQUE,
    geo_type VARCHAR(50),  -- country|region|city|district|commune
    country_code CHAR(2) DEFAULT 'ML',
    parent_geo_id VARCHAR(20) REFERENCES couche_b.geo_master(geo_id),
    coordinates JSONB,  -- {lat: 12.6392, lng: -8.0029}
    population INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE couche_b.geo_aliases (
    alias_id VARCHAR(20) PRIMARY KEY,
    geo_id VARCHAR(20) REFERENCES couche_b.geo_master(geo_id),
    alias_name VARCHAR(100) NOT NULL,
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_geo_type ON couche_b.geo_master(geo_type);
CREATE INDEX idx_geo_aliases_name ON couche_b.geo_aliases USING gin(alias_name gin_trgm_ops);
```

**Seed data (Mali):**
```sql
INSERT INTO couche_b.geo_master (geo_id, canonical_name, geo_type, country_code, coordinates, population) VALUES
('GEO_ML', 'Mali', 'country', 'ML', '{"lat": 17.5707, "lng": -3.9962}', 20250000),
('GEO_BAMAKO', 'Bamako', 'city', 'ML', '{"lat": 12.6392, "lng": -8.0029}', 2500000),
('GEO_GAO', 'Gao', 'city', 'ML', '{"lat": 16.2719, "lng": -0.0451}', 86000),
('GEO_TOMBOUCTOU', 'Tombouctou', 'city', 'ML', '{"lat": 16.7731, "lng": -3.0074}', 54000),
('GEO_MOPTI', 'Mopti', 'city', 'ML', '{"lat": 14.4843, "lng": -4.1830}', 120000),
('GEO_SIKASSO', 'Sikasso', 'city', 'ML', '{"lat": 11.3177, "lng": -5.6655}', 225000),
('GEO_SEGOU', 'Ségou', 'city', 'ML', '{"lat": 13.4311, "lng": -6.2364}', 130000),
('GEO_KAYES', 'Kayes', 'city', 'ML', '{"lat": 14.4478, "lng": -11.4448}', 127000),
('GEO_KOULIKORO', 'Koulikoro', 'city', 'ML', '{"lat": 12.8627, "lng": -7.5598}', 60000);

INSERT INTO couche_b.geo_aliases (alias_id, geo_id, alias_name, source) VALUES
('GAL_BKO1', 'GEO_BAMAKO', 'Bko', 'colloquial'),
('GAL_BKO2', 'GEO_BAMAKO', 'Bamako District', 'official'),
('GAL_SEG1', 'GEO_SEGOU', 'Ségou', 'official'),
('GAL_SEG2', 'GEO_SEGOU', 'Segou', 'variant');
```

***

## § 5 — MARKET SIGNALS (Observations prix)

### 5.1 Schema

```sql
CREATE TABLE couche_b.market_signals (
    signal_id VARCHAR(20) PRIMARY KEY,  -- SIG_01HQRST...
    
    -- Source
    source_type VARCHAR(50) NOT NULL,  -- procurement|mercurial|market_survey|meal_survey
    source_ref VARCHAR(100) NOT NULL,  -- case_id ou référence externe
    observation_date DATE NOT NULL,
    
    -- Entities (canonical IDs)
    geo_id VARCHAR(20) REFERENCES couche_b.geo_master(geo_id),
    item_id VARCHAR(20) REFERENCES couche_b.items(item_id),
    unit_id VARCHAR(20) REFERENCES couche_b.units(unit_id),
    vendor_id VARCHAR(20) REFERENCES couche_b.vendors(vendor_id),
    
    -- Prices
    quantity DECIMAL(15,3),
    unit_price DECIMAL(15,2) NOT NULL,
    total_amount DECIMAL(15,2),
    currency CHAR(3) DEFAULT 'XOF',
    
    -- Metadata
    confidence VARCHAR(20) DEFAULT 'ESTIMATED',  -- EXACT|ESTIMATED|INDICATIVE
    validation_status VARCHAR(20) DEFAULT 'pending',  -- pending|confirmed|rejected|archived
    quality_flags TEXT[],  -- ['outlier', 'incomplete', 'verified']
    notes TEXT,
    metadata_json JSONB,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    validated_at TIMESTAMPTZ,
    validated_by VARCHAR(100),
    
    -- Versioning (si correction nécessaire)
    superseded_by VARCHAR(20) REFERENCES couche_b.market_signals(signal_id)
);

CREATE INDEX idx_signals_item_geo_date ON couche_b.market_signals(item_id, geo_id, observation_date);
CREATE INDEX idx_signals_vendor_date ON couche_b.market_signals(vendor_id, observation_date);
CREATE INDEX idx_signals_source ON couche_b.market_signals(source_type, source_ref);
CREATE INDEX idx_signals_validation ON couche_b.market_signals(validation_status);
```

### 5.2 Resolvers (Entity matching logic)

```python
# backend/couche_b/resolvers.py

import re
from typing import Optional
from datetime import datetime
from sqlalchemy import text
from fuzzywuzzy import fuzz  # pip install fuzzywuzzy python-Levenshtein

def generate_ulid() -> str:
    """Generate sortable unique ID (simple implementation)"""
    from uuid import uuid4
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random = uuid4().hex[:8].upper()
    return f"{timestamp}_{random}"

def normalize_text(text: str) -> str:
    """Normalize text for matching (lowercase, trim, remove accents)"""
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return ' '.join(text.split())

def resolve_vendor(conn, vendor_name: str, threshold: int = 85) -> str:
    """
    Resolve vendor: canonical → alias → fuzzy → propose new
    Returns: vendor_id
    """
    normalized = normalize_text(vendor_name)
    
    # 1. Exact canonical match
    result = conn.execute(text("""
        SELECT vendor_id FROM couche_b.vendors
        WHERE LOWER(canonical_name) = :name
          AND status IN ('active', 'proposed')
        LIMIT 1
    """), {"name": normalized}).fetchone()
    
    if result:
        return result[0]
    
    # 2. Exact alias match
    result = conn.execute(text("""
        SELECT vendor_id FROM couche_b.vendor_aliases
        WHERE LOWER(alias_name) = :name
        LIMIT 1
    """), {"name": normalized}).fetchone()
    
    if result:
        return result[0]
    
    # 3. Fuzzy matching (expensive, use sparingly)
    candidates = conn.execute(text("""
        SELECT vendor_id, canonical_name FROM couche_b.vendors
        WHERE status IN ('active', 'proposed')
        LIMIT 50
    """)).fetchall()
    
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        score = fuzz.ratio(normalized, normalize_text(candidate[1]))
        if score > best_score:
            best_score = score
            best_match = candidate[0]
    
    if best_score >= threshold:
        # Create alias for future fast lookup
        conn.execute(text("""
            INSERT INTO couche_b.vendor_aliases (alias_id, vendor_id, alias_name, source, confidence)
            VALUES (:aid, :vid, :name, 'fuzzy_match', 'LIKELY')
        """), {
            "aid": f"VAL_{generate_ulid()}",
            "vid": best_match,
            "name": vendor_name
        })
        return best_match
    
    # 4. No match → Create proposed vendor
    vendor_id = f"VND_{generate_ulid()}"
    conn.execute(text("""
        INSERT INTO couche_b.vendors (vendor_id, canonical_name, status, created_by)
        VALUES (:id, :name, 'proposed', 'system_auto')
    """), {"id": vendor_id, "name": vendor_name.title()})
    
    conn.execute(text("""
        INSERT INTO couche_b.vendor_aliases (alias_id, vendor_id, alias_name, source)
        VALUES (:aid, :vid, :name, 'auto_import')
    """), {
        "aid": f"VAL_{generate_ulid()}",
        "vid": vendor_id,
        "name": vendor_name
    })
    
    conn.execute(text("""
        INSERT INTO couche_b.vendor_events (event_id, vendor_id, event_type, event_data, created_by)
        VALUES (:eid, :vid, 'proposed', :data, 'system_auto')
    """), {
        "eid": f"VEV_{generate_ulid()}",
        "vid": vendor_id,
        "data": json.dumps({"source": "procurement", "original_name": vendor_name})
    })
    
    return vendor_id


def resolve_item(conn, item_description: str, threshold: int = 85) -> str:
    """Resolve item: canonical → alias → fuzzy → propose new"""
    # Similar implementation to resolve_vendor
    # ... (code similaire, adaptéaux items)
    pass


def resolve_unit(conn, unit_text: str) -> str:
    """Resolve unit: symbol → alias → exact match only"""
    normalized = normalize_text(unit_text)
    
    # 1. Symbol match
    result = conn.execute(text("""
        SELECT unit_id FROM couche_b.units
        WHERE LOWER(symbol) = :symbol
        LIMIT 1
    """), {"symbol": normalized}).fetchone()
    
    if result:
        return result[0]
    
    # 2. Alias match
    result = conn.execute(text("""
        SELECT unit_id FROM couche_b.unit_aliases
        WHERE LOWER(alias_text) = :text
        LIMIT 1
    """), {"text": normalized}).fetchone()
    
    if result:
        return result[0]
    
    # 3. No fuzzy for units → propose new
    unit_id = f"UNT_{generate_ulid()}"
    conn.execute(text("""
        INSERT INTO couche_b.units (unit_id, symbol, status, created_by)
        VALUES (:id, :symbol, 'proposed', 'system_auto')
    """), {"id": unit_id, "symbol": unit_text})
    
    return unit_id


def resolve_geo(conn, location_name: str, threshold: int = 90) -> str:
    """Resolve geo: canonical → alias → fuzzy (strict threshold)"""
    # Similar to resolve_vendor but stricter threshold (90%)
    # ... (code similaire avec threshold=90)
    pass
```

***

## § 6 — API ENDPOINTS

### 6.1 Market Survey (Capture terrain)

```python
# backend/api/market_survey.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

router = APIRouter(prefix="/api/market-survey", tags=["Market Survey"])

class NewProposal(BaseModel):
    entity_type: str = Field(..., pattern="^(vendor|item|unit|geo)$")
    proposed_name: str
    metadata: Optional[dict] = None

class MarketObservation(BaseModel):
    item_id: str
    unit_id: str
    quantity: Optional[float] = None
    unit_price: float
    vendor_id: Optional[str] = None

class MarketSurveyInput(BaseModel):
    observation_date: date
    geo_id: str
    notes: Optional[str] = None
    new_proposals: List[NewProposal] = []
    observations: List[MarketObservation]

@router.post("/")
async def create_market_survey(
    survey: MarketSurveyInput,
    current_user: User = Depends(get_current_user)
):
    """
    Create market survey with propose-only pattern
    
    Workflow:
    1. Validate input data
    2. Create proposed entities (vendors/items/units if new)
    3. Create market_signals with status='pending'
    4. Notify admins for validation
    """
    with engine.begin() as conn:
        survey_id = f"SURVEY_{datetime.now().strftime('%Y%m%d')}_{generate_ulid()}"
        
        # Process new proposals
        proposed_entities = {}
        for proposal in survey.new_proposals:
            if proposal.entity_type == 'vendor':
                vendor_id = f"VND_{generate_ulid()}"
                conn.execute(text("""
                    INSERT INTO couche_b.vendors (vendor_id, canonical_name, status, created_by)
                    VALUES (:id, :name, 'proposed', :user)
                """), {
                    "id": vendor_id,
                    "name": proposal.proposed_name,
                    "user": current_user.user_id
                })
                proposed_entities[f"vendor:{proposal.proposed_name}"] = vendor_id
            
            elif proposal.entity_type == 'item':
                item_id = f"ITM_{generate_ulid()}"
                conn.execute(text("""
                    INSERT INTO couche_b.items (item_id, canonical_name, status, created_by)
                    VALUES (:id, :name, 'proposed', :user)
                """), {
                    "id": item_id,
                    "name": proposal.proposed_name,
                    "user": current_user.user_id
                })
                proposed_entities[f"item:{proposal.proposed_name}"] = item_id
            
            # Similar for units and geo...
        
        # Create market signals
        signals_created = []
        for obs in survey.observations:
            signal_id = f"SIG_{generate_ulid()}"
            conn.execute(text("""
                INSERT INTO couche_b.market_signals (
                    signal_id, source_type, source_ref, observation_date,
                    geo_id, item_id, unit_id, unit_price, currency,
                    vendor_id, quantity, confidence, validation_status,
                    notes, created_by
                ) VALUES (
                    :sid, 'market_survey', :sref, :date,
                    :geo, :item, :unit, :price, 'XOF',
                    :vendor, :qty, 'ESTIMATED', 'pending',
                    :notes, :user
                )
            """), {
                "sid": signal_id,
                "sref": survey_id,
                "date": survey.observation_date,
                "geo": survey.geo_id,
                "item": obs.item_id,
                "unit": obs.unit_id,
                "price": obs.unit_price,
                "vendor": obs.vendor_id,
                "qty": obs.quantity,
                "notes": survey.notes,
                "user": current_user.user_id
            })
            signals_created.append(signal_id)
        
        # Notify validation queue (async task)
        notify_validation_queue.delay(survey_id, len(survey.new_proposals), len(signals_created))
        
        return {
            "survey_id": survey_id,
            "status": "pending_validation",
            "proposed_entities": len(survey.new_proposals),
            "signals_created": len(signals_created),
            "message": "Survey soumis pour validation. Admins notifiés."
        }


@router.get("/validation-queue")
async def get_validation_queue(
    current_user: User = Depends(require_admin)
):
    """Get pending market surveys + proposed entities for validation"""
    with engine.connect() as conn:
        # Proposed vendors
        proposed_vendors = conn.execute(text("""
            SELECT vendor_id, canonical_name, created_at, created_by
            FROM couche_b.vendors
            WHERE status = 'proposed'
            ORDER BY created_at DESC
            LIMIT 50
        """)).fetchall()
        
        # Proposed items
        proposed_items = conn.execute(text("""
            SELECT item_id, canonical_name, created_at, created_by
            FROM couche_b.items
            WHERE status = 'proposed'
            ORDER BY created_at DESC
            LIMIT 50
        """)).fetchall()
        
        # Pending signals
        pending_signals = conn.execute(text("""
            SELECT 
                ms.signal_id,
                ms.source_ref,
                ms.observation_date,
                i.canonical_name as item_name,
                g.canonical_name as geo_name,
                ms.unit_price,
                ms.created_at,
                ms.created_by
            FROM couche_b.market_signals ms
            JOIN couche_b.items i ON i.item_id = ms.item_id
            JOIN couche_b.geo_master g ON g.geo_id = ms.geo_id
            WHERE ms.validation_status = 'pending'
            ORDER BY ms.created_at DESC
            LIMIT 100
        """)).fetchall()
        
        return {
            "proposed_vendors": [dict(row._mapping) for row in proposed_vendors],
            "proposed_items": [dict(row._mapping) for row in proposed_items],
            "pending_signals": [dict(row._mapping) for row in pending_signals]
        }


@router.patch("/{signal_id}/validate")
async def validate_signal(
    signal_id: str,
    action: str = Query(..., pattern="^(confirm|reject|archive)$"),
    current_user: User = Depends(require_admin)
):
    """Validate or reject a pending market signal"""
    with engine.begin() as conn:
        status_map = {
            "confirm": "confirmed",
            "reject": "rejected",
            "archive": "archived"
        }
        
        conn.execute(text("""
            UPDATE couche_b.market_signals
            SET validation_status = :status,
                validated_at = NOW(),
                validated_by = :user
            WHERE signal_id = :sid
        """), {
            "status": status_map[action],
            "user": current_user.user_id,
            "sid": signal_id
        })
        
        return {"signal_id": signal_id, "new_status": status_map[action]}
```

### 6.2 Market Intelligence (Consultation)

```python
# backend/api/market_intelligence.py

@router.get("/search")
async def search_market_intelligence(
    item: Optional[str] = None,
    geo: Optional[str] = None,
    vendor: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    validated_only: bool = True,
    limit: int = Query(100, le=1000)
):
    """
    Search market signals with filters
    Returns: List of signals with statistics
    """
    with engine.connect() as conn:
        where_clauses = ["ms.validation_status != 'rejected'"]
        params = {}
        
        if validated_only:
            where_clauses.append("ms.validation_status = 'confirmed'")
        
        if item:
            where_clauses.append("i.canonical_name ILIKE :item")
            params["item"] = f"%{item}%"
        
        if geo:
            where_clauses.append("g.canonical_name ILIKE :geo")
            params["geo"] = f"%{geo}%"
        
        if vendor:
            where_clauses.append("v.canonical_name ILIKE :vendor")
            params["vendor"] = f"%{vendor}%"
        
        if date_from:
            where_clauses.append("ms.observation_date >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            where_clauses.append("ms.observation_date <= :date_to")
            params["date_to"] = date_to
        
        where_sql = " AND ".join(where_clauses)
        params["limit"] = limit
        
        query = text(f"""
            SELECT 
                ms.signal_id,
                ms.observation_date,
                i.canonical_name AS item_name,
                g.canonical_name AS geo_name,
                u.symbol AS unit,
                ms.quantity,
                ms.unit_price,
                ms.currency,
                v.canonical_name AS vendor_name,
                ms.source_type,
                ms.confidence,
                ms.validation_status
            FROM couche_b.market_signals ms
            JOIN couche_b.items i ON i.item_id = ms.item_id
            JOIN couche_b.geo_master g ON g.geo_id = ms.geo_id
            JOIN couche_b.units u ON u.unit_id = ms.unit_id
            LEFT JOIN couche_b.vendors v ON v.vendor_id = ms.vendor_id
            WHERE {where_sql}
            ORDER BY ms.observation_date DESC
            LIMIT :limit
        """)
        
        results = conn.execute(query, params).fetchall()
        
        return {
            "count": len(results),
            "signals": [dict(row._mapping) for row in results]
        }


@router.get("/stats")
async def get_market_stats(
    item_id: str,
    geo_id: Optional[str] = None,
    months_back: int = Query(6, ge=1, le=24)
):
    """
    Get price statistics for an item
    Returns: avg, min, max, stddev, signal count
    """
    with engine.connect() as conn:
        where_clauses = [
            "ms.item_id = :item",
            "ms.validation_status = 'confirmed'",
            "ms.observation_date >= NOW() - INTERVAL ':months months'"
        ]
        params = {"item": item_id, "months": months_back}
        
        if geo_id:
            where_clauses.append("ms.geo_id = :geo")
            params["geo"] = geo_id
        
        where_sql = " AND ".join(where_clauses)
        
        query = text(f"""
            SELECT 
                COUNT(*) AS nb_signals,
                AVG(ms.unit_price) AS avg_price,
                MIN(ms.unit_price) AS min_price,
                MAX(ms.unit_price) AS max_price,
                STDDEV(ms.unit_price) AS std_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.unit_price) AS median_price,
                u.symbol AS unit
            FROM couche_b.market_signals ms
            JOIN couche_b.units u ON u.unit_id = ms.unit_id
            WHERE {where_sql}
            GROUP BY u.symbol
        """)
        
        result = conn.execute(query, params).fetchone()
        
        if not result or result[0] == 0:
            raise HTTPException(404, "No market data found for this item/geo/period")
        
        return dict(result._mapping)
```

***

## § 7 — UI DESIGN (Modern 2026 Standards)

### 7.1 Design System

**Base: shadcn/ui + Tailwind CSS**

Pourquoi shadcn/ui:
- ✅ Composants Radix UI (accessibilité A+)
- ✅ Copy-paste code (pas de dépendance NPM lourde)
- ✅ Customisable 100% via Tailwind
- ✅ Moderne (2025-2026 standard)

**Color palette:**
```css
/* tailwind.config.js */
module.exports = {
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        // DMS custom colors
        "dms-blue": "#0066CC",
        "dms-green": "#00A86B",
        "dms-orange": "#FF6B35",
        "dms-red": "#E63946",
      },
    },
  },
}
```

### 7.2 Market Survey UI (Écran principal)

**Wireframe:**
```
┌──────────────────────────────────────────────────────────────┐
│  🏠 DMS — Market Survey                           @user ⚙️   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📍 OBSERVER PRIX MARCHÉ                                     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Date observation *                                     │ │
│  │ [2026-02-10] 📅                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Lieu *                                                 │ │
│  │ [🔍 Bamako ▼]  ou  [+ Proposer nouveau lieu]          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Notes contexte (optionnel)                             │ │
│  │ [______________________________________________]       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ───────────────────────────────────────────────────────────│
│                                                              │
│  📦 ITEMS + PRIX                                             │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Item *        │ Unité * │ Qté │ Prix Unit. * │ Vendor  ││
│  ├───────────────┼─────────┼─────┼──────────────┼─────────┤│
│  │ [🔍 Ciment]   │ [sac▼]  │ 50  │ 6500 XOF     │ [🔍]    ││➕│
│  │ [🔍 Fer 12mm] │ [kg▼]   │ 100 │ 850 XOF      │ [🔍]    ││➖│
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  🔍 = Autocomplete catalog + "Proposer nouveau" option      │
│                                                              │
│  ───────────────────────────────────────────────────────────│
│                                                              │
│  ⚠️  PROPOSITIONS NOUVELLES (2)                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • Vendor: "Quincaillerie Nouvelle"                     │ │
│  │   [✏️ Modifier] [🗑️ Supprimer]                         │ │
│  │                                                        │ │
│  │ • Item: "Fer à béton 12mm haute adhérence"            │ │
│  │   [✏️ Modifier] [🗑️ Supprimer]                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [Annuler]  [💾 Brouillon]  [✅ Soumettre validation] │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**React component structure:**
```tsx
// frontend/src/pages/MarketSurvey/MarketSurveyForm.tsx

import { useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DatePicker } from '@/components/ui/date-picker'
import { Combobox } from '@/components/ui/combobox'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Plus, Trash2, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'

const observationSchema = z.object({
  item_id: z.string().min(1, "Item requis"),
  unit_id: z.string().min(1, "Unité requise"),
  quantity: z.number().optional(),
  unit_price: z.number().min(0, "Prix doit être positif"),
  vendor_id: z.string().optional(),
})

const surveySchema = z.object({
  observation_date: z.date(),
  geo_id: z.string().min(1, "Lieu requis"),
  notes: z.string().optional(),
  observations: z.array(observationSchema).min(1, "Au moins 1 observation requise"),
  new_proposals: z.array(z.object({
    entity_type: z.enum(['vendor', 'item', 'unit', 'geo']),
    proposed_name: z.string(),
    metadata: z.record(z.any()).optional(),
  })),
})

type SurveyForm = z.infer<typeof surveySchema>

export function MarketSurveyForm() {
  const { register, control, handleSubmit, watch, formState: { errors } } = useForm<SurveyForm>({
    resolver: zodResolver(surveySchema),
    defaultValues: {
      observation_date: new Date(),
      observations: [{ item_id: '', unit_id: '', unit_price: 0 }],
      new_proposals: [],
    },
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: "observations",
  })

  const submitMutation = useMutation({
    mutationFn: (data: SurveyForm) => api.post('/market-survey', data),
    onSuccess: () => {
      toast.success("Survey soumis pour validation ✅")
      // Reset form
    },
  })

  const onSubmit = (data: SurveyForm) => {
    submitMutation.mutate(data)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 max-w-4xl mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📍 Observer prix marché
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Date */}
          <div>
            <label className="block text-sm font-medium mb-1">Date observation *</label>
            <DatePicker 
              value={watch('observation_date')}
              onChange={(date) => setValue('observation_date', date)}
            />
            {errors.observation_date && (
              <p className="text-sm text-red-600 mt-1">{errors.observation_date.message}</p>
            )}
          </div>

          {/* Geo */}
          <div>
            <label className="block text-sm font-medium mb-1">Lieu *</label>
            <Combobox
              placeholder="Rechercher lieu..."
              searchEndpoint="/api/catalog/geo/search"
              onSelect={(geo) => setValue('geo_id', geo.geo_id)}
              allowNew={{
                label: "+ Proposer nouveau lieu",
                onCreate: (name) => handleNewProposal('geo', name),
              }}
            />
            {errors.geo_id && (
              <p className="text-sm text-red-600 mt-1">{errors.geo_id.message}</p>
            )}
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium mb-1">Notes contexte (optionnel)</label>
            <textarea 
              {...register('notes')}
              className="w-full px-3 py-2 border rounded-md"
              rows={2}
              placeholder="Marché de Médine, prix en hausse..."
            />
          </div>
        </CardContent>
      </Card>

      {/* Observations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📦 Items + Prix
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {fields.map((field, index) => (
              <div key={field.id} className="flex items-start gap-2 p-3 border rounded-md">
                {/* Item */}
                <div className="flex-1">
                  <Combobox
                    placeholder="Item..."
                    searchEndpoint="/api/catalog/items/search"
                    onSelect={(item) => setValue(`observations.${index}.item_id`, item.item_id)}
                    allowNew={{
                      label: "+ Proposer nouveau",
                      onCreate: (name) => handleNewProposal('item', name),
                    }}
                  />
                </div>

                {/* Unit */}
                <div className="w-32">
                  <Combobox
                    placeholder="Unité..."
                    searchEndpoint="/api/catalog/units/search"
                    onSelect={(unit) => setValue(`observations.${index}.unit_id`, unit.unit_id)}
                  />
                </div>

                {/* Quantity */}
                <div className="w-24">
                  <Input
                    type="number"
                    placeholder="Qté"
                    {...register(`observations.${index}.quantity`, { valueAsNumber: true })}
                  />
                </div>

                {/* Price */}
                <div className="w-32">
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="Prix..."
                    {...register(`observations.${index}.unit_price`, { valueAsNumber: true })}
                    className={errors.observations?.[index]?.unit_price ? 'border-red-500' : ''}
                  />
                </div>

                {/* Vendor */}
                <div className="flex-1">
                  <Combobox
                    placeholder="Vendor..."
                    searchEndpoint="/api/catalog/vendors/search"
                    onSelect={(vendor) => setValue(`observations.${index}.vendor_id`, vendor.vendor_id)}
                    allowNew={{
                      label: "+ Proposer nouveau",
                      onCreate: (name) => handleNewProposal('vendor', name),
                    }}
                  />
                </div>

                {/* Remove */}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => remove(index)}
                  disabled={fields.length === 1}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              onClick={() => append({ item_id: '', unit_id: '', unit_price: 0 })}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" /> Ajouter item
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* New Proposals Summary */}
      {watch('new_proposals').length > 0 && (
        <Card className="border-orange-300 bg-orange-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-700">
              <AlertCircle className="h-5 w-5" />
              Propositions nouvelles ({watch('new_proposals').length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {watch('new_proposals').map((proposal, idx) => (
                <li key={idx} className="flex items-center justify-between">
                  <span>
                    <strong>{proposal.entity_type}:</strong> "{proposal.proposed_name}"
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeProposal(idx)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Submit */}
      <div className="flex justify-end gap-3">
        <Button type="button" variant="outline">
          Annuler
        </Button>
        <Button type="button" variant="secondary">
          💾 Brouillon
        </Button>
        <Button type="submit" disabled={submitMutation.isPending}>
          {submitMutation.isPending ? "Envoi..." : "✅ Soumettre validation"}
        </Button>
      </div>
    </form>
  )
}
```

***

## § 8 — ROADMAP EXÉCUTION (4 semaines)

### Semaine 1: Fondations (Jour 1-7)

**Backend:**
- [ ] Setup FastAPI + PostgreSQL + Alembic
- [ ] Schemas Couche B (vendors, items, units, geo, market_signals)
- [ ] Seed data Mali (geo + units standards)
- [ ] Resolvers (resolve_vendor, resolve_item, resolve_unit, resolve_geo)
- [ ] Tests resolvers (>80% coverage)

**Frontend:**
- [ ] Setup React + Vite + TypeScript + Tailwind + shadcn/ui
- [ ] Components base (Button, Input, Card, Combobox, DatePicker)
- [ ] Layout principal + routing
- [ ] Auth flow (login/logout/session)

**DevOps:**
- [ ] Railway.app setup
- [ ] CI/CD GitHub Actions (tests + deploy preview)
- [ ] Environment variables (.env.example)

***

### Semaine 2: Market Survey MVP (Jour 8-14)

**Backend:**
- [ ] API `/market-survey` (POST create avec propose-only)
- [ ] API `/market-survey/validation-queue` (GET pending proposals)
- [ ] API `/market-survey/{signal_id}/validate` (PATCH confirm/reject)
- [ ] API `/catalog/*` (search vendors/items/units/geo pour autocomplete)
- [ ] Notification admin (email ou Slack webhook)

**Frontend:**
- [ ] Page Market Survey Form (écran complet)
- [ ] Combobox avec autocomplete + "Proposer nouveau"
- [ ] Dynamic observations array (add/remove items)
- [ ] New proposals summary card
- [ ] Submit + loading states + error handling

**Tests:**
- [ ] E2E Playwright: User crée survey → Admin valide

***

### Semaine 3: Market Intelligence + Admin (Jour 15-21)

**Backend:**
- [ ] API `/market-intelligence/search` (filtres item/geo/vendor/date)
- [ ] API `/market-intelligence/stats` (avg/min/max/median prices)
- [ ] Cache Redis pour queries stats (TTL 1h)
- [ ] Admin validation UI backend support

**Frontend:**
- [ ] Page Market Intelligence Search (filtres + results table)
- [ ] Modal Market Stats (chart simple avec Recharts)
- [ ] Admin Validation Queue page (table propositions + signals)
- [ ] Bulk actions (validate multiple signals)

**Tests:**
- [ ] API load test (100 req/s search endpoint)
- [ ] E2E: Search market intelligence → voir stats

***

### Semaine 4: Polish + Production (Jour 22-28)

**Backend:**
- [ ] Ingestion automatique post-décision (Couche A → B)
- [ ] Import mercurials CSV (endpoint + validation)
- [ ] Monitoring Sentry + metrics Prometheus
- [ ] Documentation OpenAPI complète

**Frontend:**
- [ ] Responsive mobile (test iPhone/Android)
- [ ] Loading skeletons
- [ ] Toast notifications (success/error)
- [ ] Dark mode (optionnel nice-to-have)

**DevOps:**
- [ ] Production deployment Railway
- [ ] Database backups automated
- [ ] SSL certificate + custom domain
- [ ] Monitoring dashboard (Sentry)

**User Testing:**
- [ ] 3 DAOs réels Save the Children Mali
- [ ] 5 market surveys test
- [ ] Feedback log + corrections

***

## § 9 — CLAUSE ANTI-DÉRIVE (Immuable)

### 9.1 Online-only = non négociable

**DMS est online-only en V1. Point final.**

Toute discussion "offline-first" ou "mode dégradé offline" est **hors Constitution** et sera rejetée.

**Pourquoi:**
1. Les clients cibles (ONGs, États, mines) ont Internet stable
2. Offline complexifie architecture (sync conflicts, data corruption, bugs)
3. Time-to-market > versatilité théorique
4. En 2026, "offline" est un faux problème pour ce marché

**Post-MVP (6+ mois):**  
Si demande client réelle + budget, on peut ajouter **cache read-only** pour consultation registre/market intelligence, mais jamais saisie offline.

### 9.2 Excel-killer ou rien

**Chaque feature doit être:**
- ⏱️ **Plus rapide qu'Excel** (< 2 secondes)
- 🎯 **Plus claire qu'Excel** (zéro confusion UX)
- 💪 **Fait quelque chose qu'Excel ne peut pas** (collaboration, mémoire, AI)

Si une feature rate 2/3 critères → **rejeter ou refaire**.

### 9.3 Décisions techniques = impact mesurable

Toute décision technique doit améliorer **au moins 1 axe:**

| Axe | Métrique |
|-----|----------|
| **Performance** | Temps réponse API, page load, bundle size |
| **Fiabilité** | Uptime %, error rate, test coverage |
| **Esthétique** | Lighthouse score, user feedback, design consistency |
| **Déployabilité** | Time to deploy, rollback speed, CI/CD success rate |

Si aucun axe n'est amélioré → **rejeter**.

### 9.4 Constitution = référence ultime

**Ce document est FROZEN pour exécution.**

Modifications acceptables:
- ✅ Ajout features alignées avec vision
- ✅ Optimisations techniques (performance, sécurité)
- ✅ Corrections bugs

Modifications interdites:
- ❌ Changement philosophie online-only
- ❌ Dilution Couche B (avantage compétitif)
- ❌ Complexification architecture sans ROI clair

**Version actuelle:** V2.1  
**Date freeze:** 10 février 2026  
**Prochaine review:** Post-MVP (Semaine 5)

***

## § 10 — CONCLUSION EXÉCUTIVE

**DMS n'est pas un projet. C'est une catégorie de produit.**

En février 2026, **aucun système équivalent n'existe** pour:
- Centraliser décisions procurement structurées
- Créer mémoire market intelligence exploitable
- Servir organisations africaines avec standards internationaux

**Cette Constitution V2.1 fige:**
- Architecture technique production-ready
- Stack moderne (FastAPI + React + PostgreSQL + Railway)
- Couche B comme avantage compétitif durable
- Roadmap 4 semaines → production

**Prochaine étape:**  
Activer agents (Backend + Frontend + QA) demain matin 9h GMT selon plan d'activation fourni.

**Règle finale:**  
Si une décision ne rend pas DMS plus rapide, plus fiable, plus beau ou plus déployable → **elle n'existe pas**.

***

**FIN CONSTITUTION DMS V2.1**

© 2026 Decision Memory System  
"This system protects organizations from forgetting, not from their people."
