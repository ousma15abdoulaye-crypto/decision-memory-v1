# CONSTITUTION V2.1 COMPLIANCE CHECKLIST

**Quick reference for Couche B implementation**

---

## ✅ MUST HAVE (Non-Negotiable)

### Database
- [x] PostgreSQL (not SQLite)
- [x] SQLAlchemy 2.0 Core (Table(), not ORM)
- [x] async/await everywhere (no sync fallback)
- [x] Alembic migrations
- [x] Schema: `couche_b` (not public)

### Tables (Exact 10)
1. [x] `couche_b.vendors` - 13 colonnes minimum
2. [x] `couche_b.vendor_aliases` - alias_id, vendor_id, alias_name, source, confidence, created_at
3. [x] `couche_b.vendor_events` - event_id, vendor_id, event_type, event_data, created_at, created_by
4. [x] `couche_b.items` - 7 colonnes minimum
5. [x] `couche_b.item_aliases` - alias_id, item_id, alias_name, source, created_at
6. [x] `couche_b.units` - 7 colonnes minimum
7. [x] `couche_b.unit_aliases` - alias_id, unit_id, alias_text, created_at
8. [x] `couche_b.geo_master` - 8 colonnes minimum
9. [x] `couche_b.geo_aliases` - alias_id, geo_id, alias_name, source, created_at
10. [x] `couche_b.market_signals` - 20 colonnes minimum

### Indexes (Required)

**IMPORTANT:** GIN indexes require `pg_trgm` extension:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

- [x] `idx_vendors_status` ON vendors(status)
- [x] `idx_vendor_aliases_name` ON vendor_aliases USING gin(alias_name gin_trgm_ops)
- [x] `idx_items_category` ON items(category)
- [x] `idx_item_aliases_name` ON item_aliases USING gin(alias_name gin_trgm_ops)
- [x] `idx_units_category` ON units(category)
- [x] `idx_geo_type` ON geo_master(geo_type)
- [x] `idx_geo_aliases_name` ON geo_aliases USING gin(alias_name gin_trgm_ops)
- [x] `idx_signals_item_geo_date` ON market_signals(item_id, geo_id, observation_date)
- [x] `idx_signals_vendor_date` ON market_signals(vendor_id, observation_date)
- [x] `idx_signals_source` ON market_signals(source_type, source_ref)
- [x] `idx_signals_validation` ON market_signals(validation_status)

### Seed Data (Mali)
**Vendors (3 minimum):**
- [x] VND_SOGELEC - Société Générale d'Électricité
- [x] VND_SOMAPEP - Société Malienne de Peinture
- [x] VND_COVEC - China Overseas Engineering Group Mali

**Items (3 minimum):**
- [x] ITM_CIM50 - Ciment Portland CPA 42.5 - Sac 50kg
- [x] ITM_FER12 - Fer à béton haute adhérence Ø12mm
- [x] ITM_RIZ25 - Riz brisé parfumé - Sac 25kg

**Units (9 minimum):**
- [x] UNT_KG - Kilogramme
- [x] UNT_TONNE - Tonne (conversion 1000 kg)
- [x] UNT_L - Litre
- [x] UNT_M3 - Mètre cube (conversion 1000 L)
- [x] UNT_M - Mètre
- [x] UNT_M2 - Mètre carré
- [x] UNT_PIECE - Pièce
- [x] UNT_SAC - Sac
- [x] UNT_CARTON - Carton

**Geo (9 cities minimum):**
- [x] GEO_ML - Mali (country)
- [x] GEO_BAMAKO - Bamako
- [x] GEO_GAO - Gao
- [x] GEO_TOMBOUCTOU - Tombouctou
- [x] GEO_MOPTI - Mopti
- [x] GEO_SIKASSO - Sikasso
- [x] GEO_SEGOU - Ségou
- [x] GEO_KAYES - Kayes
- [x] GEO_KOULIKORO - Koulikoro

### Resolvers (4 functions)
- [x] `async def resolve_vendor(name: str) -> Optional[str]`
- [x] `async def resolve_item(desc: str) -> Optional[str]`
- [x] `async def resolve_unit(text: str) -> Optional[str]`
- [x] `async def resolve_geo(location: str) -> Optional[str]`

**Resolution strategy (exact order):**
1. Exact match canonical name
2. Exact match alias
3. Fuzzy match (Levenshtein distance, threshold 85%)
4. Return None

### Propose-Only Pattern
- [x] `async def propose_new_vendor(name, created_by) -> str` (status='proposed')
- [x] `async def propose_new_item(name, created_by) -> str` (status='proposed')
- [x] `async def propose_new_unit(symbol, created_by) -> str` (status='proposed')
- [x] `async def propose_new_geo(name, created_by) -> str` (status='proposed')

**Rule:** Nouvelles entités créées avec `status='proposed'`. Admin valide manuellement → `status='active'`.

### Signal Ingestion
- [x] `async def record_market_signal()` - Insert market observation
- [x] Non-blocking (async)
- [x] Triggers automatiquement post-décision (source_type='procurement')
- [x] Import manuel mercurials (source_type='mercurial')

---

## ❌ FORBIDDEN (Never Touch)

### Files
- ❌ `main.py` (unless explicit TODO comment exists)
- ❌ `src/db.py` (if exists - create only if doesn't exist)
- ❌ `alembic/env.py` (if exists - create only if doesn't exist)
- ❌ `requirements.txt` (unless explicit TODO comment exists)
- ❌ `pyproject.toml` (unless explicit TODO comment exists)
- ❌ Anything in `src/couche_a/**`
- ❌ Anything in `templates/**`
- ❌ Anything in `static/**`

### Anti-Patterns
- ❌ SQLAlchemy ORM (class MyModel(Base))
- ❌ Sync database code (def instead of async def)
- ❌ Sync fallback patterns
- ❌ Helper scripts to work around issues
- ❌ Global refactoring
- ❌ Modifications beyond Couche B scope
- ❌ Django, Flask, or other frameworks
- ❌ Adding unnecessary dependencies

---

## 📊 EXACT COLUMN SPECIFICATIONS

### vendors (13 columns minimum)

**ID Format Convention:**  
- Format: `PREFIX_IDENTIFIER` (e.g., `VND_SOGELEC`, `VND_01HQRST...`)  
- Prefix: 3-4 chars (VND, ITM, UNT, GEO, SIG)  
- Separator: `_`  
- Identifier: Human-readable OR ULID (sortable timestamp-based)  
- Max length: 20 chars ensures future ULID compatibility

```sql
vendor_id VARCHAR(20) PRIMARY KEY
canonical_name VARCHAR(200) NOT NULL UNIQUE
legal_name VARCHAR(300)
registration_number VARCHAR(50)
tax_id VARCHAR(50)
vendor_type VARCHAR(50)  -- local|national|international|individual
status VARCHAR(20) DEFAULT 'proposed'  -- proposed|active|rejected|inactive
contact_json JSONB
tags TEXT[]
metadata_json JSONB
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()
created_by VARCHAR(100)
```

### items (7 columns minimum)
```sql
item_id VARCHAR(20) PRIMARY KEY
canonical_name VARCHAR(300) NOT NULL UNIQUE
unspsc_code VARCHAR(20)
category VARCHAR(100)  -- fournitures|btp|services|medical
description TEXT
specifications_json JSONB
status VARCHAR(20) DEFAULT 'proposed'
created_at TIMESTAMPTZ DEFAULT NOW()
created_by VARCHAR(100)
```

### units (7 columns minimum)
```sql
unit_id VARCHAR(20) PRIMARY KEY
symbol VARCHAR(20) NOT NULL UNIQUE
name VARCHAR(100)
category VARCHAR(50)  -- weight|volume|length|count|area
conversion_to_base DECIMAL(15,6)
base_unit_id VARCHAR(20) REFERENCES couche_b.units(unit_id)
status VARCHAR(20) DEFAULT 'active'
created_at TIMESTAMPTZ DEFAULT NOW()
```

### geo_master (8 columns minimum)
```sql
geo_id VARCHAR(20) PRIMARY KEY
canonical_name VARCHAR(100) NOT NULL UNIQUE
geo_type VARCHAR(50)  -- country|region|city|district|commune
country_code CHAR(2) DEFAULT 'ML'
parent_geo_id VARCHAR(20) REFERENCES couche_b.geo_master(geo_id)
coordinates JSONB  -- {lat: 12.6392, lng: -8.0029}
population INTEGER
status VARCHAR(20) DEFAULT 'active'
created_at TIMESTAMPTZ DEFAULT NOW()
```

### market_signals (20 columns minimum)
```sql
signal_id VARCHAR(20) PRIMARY KEY
source_type VARCHAR(50) NOT NULL  -- procurement|mercurial|market_survey|meal_survey
source_ref VARCHAR(100) NOT NULL
observation_date DATE NOT NULL
geo_id VARCHAR(20) REFERENCES couche_b.geo_master(geo_id)
item_id VARCHAR(20) REFERENCES couche_b.items(item_id)
unit_id VARCHAR(20) REFERENCES couche_b.units(unit_id)
vendor_id VARCHAR(20) REFERENCES couche_b.vendors(vendor_id)
quantity DECIMAL(15,3)
unit_price DECIMAL(15,2) NOT NULL
total_amount DECIMAL(15,2)
currency CHAR(3) DEFAULT 'XOF'
confidence VARCHAR(20) DEFAULT 'ESTIMATED'  -- EXACT|ESTIMATED|INDICATIVE
validation_status VARCHAR(20) DEFAULT 'pending'  -- pending|confirmed|rejected|archived
quality_flags TEXT[]
notes TEXT
metadata_json JSONB
created_at TIMESTAMPTZ DEFAULT NOW()
created_by VARCHAR(100)
validated_at TIMESTAMPTZ
validated_by VARCHAR(100)
superseded_by VARCHAR(20) REFERENCES couche_b.market_signals(signal_id)
```

---

## 🔧 DEPENDENCIES EXACT VERSIONS

**If requirements.txt has TODO, add:**
```txt
# Database (Constitution V2.1 § 1.2)
sqlalchemy==2.0.27
alembic==1.13.1
psycopg[binary,pool]==3.1.18
asyncpg==0.29.0

# Resolvers (fuzzy matching)
fuzzywuzzy==0.18.0
python-Levenshtein==0.25.0
```

**Otherwise, create `requirements_couche_b.txt` with above.**

---

## 🧪 MINIMUM TESTS

### test_schema.py
- [x] Test all 10 tables created
- [x] Test all 11 indexes created
- [x] Test CHECK constraints valid
- [x] Test FK relationships valid

### test_resolvers.py
- [x] Test resolve_vendor() exact match
- [x] Test resolve_vendor() alias match
- [x] Test resolve_vendor() fuzzy match
- [x] Test propose_new_vendor() creates status='proposed'
- [x] Repeat for item, unit, geo

### test_signals.py
- [x] Test record_market_signal() inserts signal
- [x] Test FK constraints enforced (geo_id, item_id, unit_id, vendor_id)
- [x] Test validation_status defaults to 'pending'
- [x] Test currency defaults to 'XOF'

---

## 🚀 VALIDATION COMMAND

```bash
# Run this before submitting PR
cd /home/runner/work/decision-memory-v1/decision-memory-v1

# 1. Compilation check
python -m compileall src/couche_b -q || exit 1

# 2. Migration check
alembic upgrade head || exit 1
alembic downgrade base || exit 1
alembic upgrade head || exit 1

# 3. Tests check
pytest tests/couche_b/ -v || exit 1

# 4. Existing tests still pass
python3 tests/test_corrections_smoke.py || exit 1
python3 tests/test_partial_offers.py || exit 1

# 5. Protected files check
git diff main.py | wc -l | grep "^0$" || echo "⚠️  main.py modified!"
git diff requirements.txt | wc -l | grep "^0$" || echo "⚠️  requirements.txt modified!"

# 6. No Couche A changes
git diff --name-only | grep "src/couche_a\|templates/\|static/" && echo "❌ Couche A modified!" || echo "✅ Couche A untouched"

echo "✅ VALIDATION PASSED - Ready for PR"
```

---

**END OF COMPLIANCE CHECKLIST**
