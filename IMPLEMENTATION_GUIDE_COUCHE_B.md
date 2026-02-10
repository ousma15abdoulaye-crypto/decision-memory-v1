# IMPLEMENTATION GUIDE — COUCHE B MINIMAL

**Date:** 10 février 2026  
**Status:** Implementation roadmap  
**Target:** Resolve 12 blockers from AUDIT_COUCHE_B_V2.1.md  

---

## OVERVIEW

Cette implémentation doit être effectuée par un **agent Couche B dédié**, PAS par l'agent AUDIT.

L'agent AUDIT a terminé son travail. Les prochaines étapes sont:
1. Créer une nouvelle PR "Implement Couche B Minimal" 
2. Assigner à un agent Couche B avec accès à cette documentation
3. Suivre strictement les phases ci-dessous

---

## ARCHITECTURE DECISIONS

### Database Strategy
- **PostgreSQL obligatoire** en production (Constitution § 1.2)
- **SQLAlchemy 2.0 Core** (Table(), pas ORM) avec async/await
- **Alembic** pour migrations
- **Drivers:** psycopg (sync admin) + asyncpg (async runtime)

### Module Structure
```
src/
├── __init__.py                    # NEW: Empty file for package
├── mapping/                       # EXISTING: Couche A
│   └── ...
└── couche_b/                      # NEW: Market Intelligence
    ├── __init__.py
    ├── models.py                  # Table() definitions
    ├── resolvers.py               # Entity matching logic
    ├── signals.py                 # Market signal ingestion
    └── seed_data.py               # Mali initial data

alembic/                           # NEW: Database migrations
├── alembic.ini
├── env.py
├── script.py.mako
└── versions/
    ├── 001_create_couche_b_schema.py
    └── 002_seed_couche_b_data.py

tests/
└── couche_b/                      # NEW: Couche B tests
    ├── __init__.py
    ├── test_schema.py
    ├── test_resolvers.py
    └── test_signals.py
```

---

## PHASE 1: DATABASE FOUNDATION

### 1.1 Create src/__init__.py
**Purpose:** Fix ModuleNotFoundError  
**File:** `src/__init__.py`  
**Content:**
```python
# Empty file to make src a package
```

### 1.2 Create src/db.py
**Purpose:** PostgreSQL async connection  
**File:** `src/db.py`  
**Content:** See snippet below

<details>
<summary>src/db.py minimal implementation</summary>

```python
"""
Couche B Database Connection
SQLAlchemy 2.0 Core + Async
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import MetaData, Table, Column, String, Integer, DECIMAL, DateTime, JSON, ARRAY, TEXT
from sqlalchemy import Index, CheckConstraint, ForeignKey
from datetime import datetime
import os

# PostgreSQL connection URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://dms_user:dms_password@localhost:5432/dms_production"
)

# Async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Metadata for Couche B schema
metadata = MetaData(schema="couche_b")

async def get_async_session():
    """Dependency for FastAPI async sessions"""
    async with AsyncSessionLocal() as session:
        yield session
```
</details>

### 1.3 Initialize Alembic
**Commands:**
```bash
pip install alembic sqlalchemy asyncpg psycopg[binary,pool]
alembic init alembic
```

**File:** `alembic/env.py`  
**Modifications:**
- Import `from src.db import metadata`
- Set `target_metadata = metadata`
- Configure async engine

<details>
<summary>alembic/env.py minimal changes</summary>

```python
from src.db import metadata, DATABASE_URL
target_metadata = metadata

# In run_migrations_online():
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
# ... rest of Alembic async config
```
</details>

### 1.4 Create Migration 001: Schema
**File:** `alembic/versions/001_create_couche_b_schema.py`  
**Content:** 10 tables + indexes + constraints

**Tables to create:**
1. `couche_b.vendors` (20 colonnes)
2. `couche_b.vendor_aliases` (5 colonnes)
3. `couche_b.vendor_events` (5 colonnes)
4. `couche_b.items` (7 colonnes)
5. `couche_b.item_aliases` (4 colonnes)
6. `couche_b.units` (7 colonnes)
7. `couche_b.unit_aliases` (3 colonnes)
8. `couche_b.geo_master` (8 colonnes)
9. `couche_b.geo_aliases` (4 colonnes)
10. `couche_b.market_signals` (20 colonnes)

**Indexes requis:**
- `idx_signals_item_geo_date` ON market_signals(item_id, geo_id, observation_date)
- `idx_signals_vendor_date` ON market_signals(vendor_id, observation_date)
- `idx_signals_source` ON market_signals(source_type, source_ref)
- GIN indexes pour fuzzy search (vendor_aliases.alias_name, etc.)

See Constitution § 3.3 - § 5.1 for exact DDL.

---

## PHASE 2: COUCHE B CORE LOGIC

### 2.1 Models (Table Definitions)
**File:** `src/couche_b/models.py`  
**Content:** SQLAlchemy Core Table() for each of 10 tables

```python
from sqlalchemy import Table, Column, String, Integer, DECIMAL, DateTime, JSON, ARRAY, TEXT
from sqlalchemy import MetaData, Index, CheckConstraint, ForeignKey
from datetime import datetime

metadata = MetaData(schema="couche_b")

vendors = Table(
    "vendors",
    metadata,
    Column("vendor_id", String(20), primary_key=True),
    Column("canonical_name", String(200), nullable=False, unique=True),
    Column("legal_name", String(300)),
    Column("registration_number", String(50)),
    Column("tax_id", String(50)),
    Column("vendor_type", String(50)),
    Column("status", String(20), default="proposed"),
    Column("contact_json", JSON),
    Column("tags", ARRAY(TEXT)),
    Column("metadata_json", JSON),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column("created_by", String(100)),
)

# ... repeat for all 10 tables
```

### 2.2 Resolvers (Entity Matching)
**File:** `src/couche_b/resolvers.py`  
**Purpose:** Canonical entity resolution (vendor/item/unit/geo)

**Key functions:**
- `async def resolve_vendor(name: str) -> Optional[str]` - Returns vendor_id or None
- `async def resolve_item(description: str) -> Optional[str]` - Returns item_id or None
- `async def resolve_unit(text: str) -> Optional[str]` - Returns unit_id or None
- `async def resolve_geo(location: str) -> Optional[str]` - Returns geo_id or None
- `async def propose_new_vendor(name: str, created_by: str) -> str` - Creates status='proposed'

**Resolution strategy (Constitution § 5.2):**
1. Exact match canonical
2. Exact match alias
3. Fuzzy match (Levenshtein distance < 85%)
4. Return None → propose new entity

**Dependencies:**
```bash
pip install fuzzywuzzy python-Levenshtein
```

### 2.3 Signals (Market Intelligence Ingestion)
**File:** `src/couche_b/signals.py`  
**Purpose:** Record market observations

**Key function:**
```python
async def record_market_signal(
    source_type: str,  # procurement|mercurial|market_survey
    source_ref: str,   # case_id or external reference
    observation_date: date,
    geo_id: str,
    item_id: str,
    unit_id: str,
    vendor_id: Optional[str],
    quantity: Decimal,
    unit_price: Decimal,
    total_amount: Decimal,
    currency: str = "XOF",
    confidence: str = "ESTIMATED",
    metadata_json: Optional[dict] = None,
    created_by: str = "system",
) -> str:
    """
    Inserts a market signal (price observation).
    Returns signal_id.
    Non-blocking (async).
    """
    # Generate ULID
    # Insert into market_signals table
    # Return signal_id
```

---

## PHASE 3: SEED DATA

### 3.1 Create Migration 002: Seed Data
**File:** `alembic/versions/002_seed_couche_b_data.py`

**Seed vendors (Mali top 3):**
```sql
INSERT INTO couche_b.vendors (vendor_id, canonical_name, vendor_type, status) VALUES
('VND_SOGELEC', 'Société Générale d''Électricité (SOGELEC)', 'national', 'active'),
('VND_SOMAPEP', 'Société Malienne de Peinture et d''Entretien (SOMAPEP)', 'national', 'active'),
('VND_COVEC', 'China Overseas Engineering Group (COVEC Mali)', 'international', 'active');
```

**Seed items (common 3):**
```sql
INSERT INTO couche_b.items (item_id, canonical_name, category, status) VALUES
('ITM_CIM50', 'Ciment Portland CPA 42.5 - Sac 50kg', 'btp', 'active'),
('ITM_FER12', 'Fer à béton haute adhérence Ø12mm', 'btp', 'active'),
('ITM_RIZ25', 'Riz brisé parfumé - Sac 25kg', 'fournitures', 'active');
```

**Seed units (9 standard):**
```sql
INSERT INTO couche_b.units (unit_id, symbol, name, category, conversion_to_base, base_unit_id) VALUES
('UNT_KG', 'kg', 'Kilogramme', 'weight', 1.0, NULL),
('UNT_L', 'L', 'Litre', 'volume', 1.0, NULL),
('UNT_M', 'm', 'Mètre', 'length', 1.0, NULL),
('UNT_SAC', 'sac', 'Sac', 'count', 1.0, NULL),
('UNT_PIECE', 'pièce', 'Pièce', 'count', 1.0, NULL);
```

**Seed geo (Mali cities):**
```sql
INSERT INTO couche_b.geo_master (geo_id, canonical_name, geo_type, country_code, coordinates, population) VALUES
('GEO_ML', 'Mali', 'country', 'ML', '{"lat": 17.5707, "lng": -3.9962}', 20250000),
('GEO_BAMAKO', 'Bamako', 'city', 'ML', '{"lat": 12.6392, "lng": -8.0029}', 2500000),
('GEO_GAO', 'Gao', 'city', 'ML', '{"lat": 16.2719, "lng": -0.0451}', 86000);
```

See Constitution § 4.2 - 4.5 for complete seed data.

---

## PHASE 4: TESTS

### 4.1 Schema Tests
**File:** `tests/couche_b/test_schema.py`

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from src.db import metadata, DATABASE_URL

@pytest.mark.asyncio
async def test_tables_exist():
    """Verify all 10 Couche B tables are created"""
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'couche_b'
        """))
        tables = [row[0] for row in result]
    
    expected = ['vendors', 'vendor_aliases', 'vendor_events', 
                'items', 'item_aliases', 'units', 'unit_aliases',
                'geo_master', 'geo_aliases', 'market_signals']
    
    for table in expected:
        assert table in tables, f"Table {table} not found"

@pytest.mark.asyncio
async def test_indexes_exist():
    """Verify required indexes are created"""
    # Query pg_indexes for couche_b schema
    # Assert idx_signals_item_geo_date, idx_signals_vendor_date, etc. exist
    pass
```

### 4.2 Resolver Tests
**File:** `tests/couche_b/test_resolvers.py`

```python
import pytest
from src.couche_b.resolvers import (
    resolve_vendor, 
    resolve_item, 
    propose_new_vendor
)

@pytest.mark.asyncio
async def test_resolve_vendor_exact():
    """Test exact vendor match"""
    vendor_id = await resolve_vendor("SOGELEC")
    assert vendor_id == "VND_SOGELEC"

@pytest.mark.asyncio
async def test_resolve_vendor_alias():
    """Test vendor alias match"""
    # Insert test alias first
    # Then test resolution
    pass

@pytest.mark.asyncio
async def test_propose_new_vendor():
    """Test creating new vendor with status='proposed'"""
    vendor_id = await propose_new_vendor("Test Vendor Inc", created_by="test_user")
    assert vendor_id.startswith("VND_")
    
    # Verify status is 'proposed'
    # Verify canonical_name is "Test Vendor Inc"
    pass
```

### 4.3 Signals Tests
**File:** `tests/couche_b/test_signals.py`

```python
import pytest
from decimal import Decimal
from datetime import date
from src.couche_b.signals import record_market_signal

@pytest.mark.asyncio
async def test_record_market_signal():
    """Test market signal insertion"""
    signal_id = await record_market_signal(
        source_type="mercurial",
        source_ref="MERCURIAL_BTP_2026_02",
        observation_date=date(2026, 2, 1),
        geo_id="GEO_BAMAKO",
        item_id="ITM_CIM50",
        unit_id="UNT_SAC",
        vendor_id=None,
        quantity=Decimal("1.0"),
        unit_price=Decimal("6500.00"),
        total_amount=Decimal("6500.00"),
        currency="XOF",
        confidence="EXACT",
        created_by="test_user",
    )
    
    assert signal_id.startswith("SIG_")
    
    # Verify signal was inserted
    # Verify FK constraints are valid
    pass
```

---

## PHASE 5: CI FIXES

### 5.1 Update requirements.txt (IF TODO exists)
**Check first:**
```bash
grep -i "TODO\|FIXME" requirements.txt
```

**If TODO found, add:**
```txt
sqlalchemy==2.0.27
alembic==1.13.1
psycopg[binary,pool]==3.1.18
asyncpg==0.29.0
fuzzywuzzy==0.18.0
python-Levenshtein==0.25.0
```

**If NO TODO, create separate file:**
```bash
# Create requirements_couche_b.txt instead
# DO NOT MODIFY requirements.txt
```

### 5.2 Fix PYTHONPATH
**Option A: Create pyproject.toml** (Preferred)
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "dms"
version = "2.1.0"

[tool.setuptools]
packages = ["src"]
```

**Option B: Update CI workflow** (Only if allowed)
```yaml
# .github/workflows/ci.yml
- name: Install dependencies
  run: |
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    pip install -r requirements.txt
```

### 5.3 PostgreSQL in CI
**Option A: GitHub Actions service** (May fail with exit 125)
```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_DB: dms_test
      POSTGRES_USER: dms_user
      POSTGRES_PASSWORD: dms_password
    ports:
      - 5432:5432
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

**Option B: Skip DB tests in CI** (Minimal approach)
```python
# In tests, check if DATABASE_URL is available
import os
import pytest

@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL not available in CI"
)
async def test_couche_b_integration():
    pass
```

---

## VALIDATION CHECKLIST

Before submitting Couche B PR, verify:

- [ ] All 12 blockers from AUDIT resolved
- [ ] `alembic upgrade head` succeeds (creates 10 tables)
- [ ] `alembic downgrade base` succeeds (drops all tables)
- [ ] `pytest tests/couche_b/` passes (all tests green)
- [ ] `python -m compileall src/couche_b -q` succeeds
- [ ] No modifications to PROTECTED files:
  - [ ] main.py unchanged (unless TODO exists)
  - [ ] src/db.py unchanged (if existed before)
  - [ ] alembic/env.py unchanged (if existed before)
  - [ ] requirements.txt unchanged (unless TODO exists)
- [ ] No changes to Couche A:
  - [ ] src/couche_a/** untouched
  - [ ] templates/** untouched
  - [ ] static/** untouched
- [ ] CI workflow passes:
  - [ ] Compilation check green
  - [ ] Existing tests green (test_corrections_smoke.py, test_partial_offers.py)
  - [ ] New Couche B tests green (or skipped if PostgreSQL unavailable)

---

## ANTI-PATTERNS TO AVOID

❌ **DO NOT:**
- Use Django ORM or SQLAlchemy ORM (use Table() Core only)
- Add sync fallback code (async/await everywhere)
- Modify main.py (protected file)
- Touch Couche A code (src/mapping/**, templates/**, static/**)
- Create helper scripts to work around issues (use standard tools)
- Add dependencies without checking for TODO first
- Propose global refactoring (minimal changes only)

✅ **DO:**
- Use SQLAlchemy 2.0 Core (Table(), select(), insert())
- Use async/await for all DB operations
- Follow Constitution V2.1 exact schema (10 tables, columns, indexes)
- Create new files in src/couche_b/ and alembic/
- Add tests for every new function
- Keep diffs minimal and surgical

---

## NEXT STEPS

1. **Create new branch:** `git checkout -b implement-couche-b-minimal`
2. **Assign to Couche B agent** (not AUDIT agent)
3. **Follow phases 1-5** in order
4. **Run validation checklist**
5. **Submit PR** with reference to AUDIT_COUCHE_B_V2.1.md
6. **Request re-audit** from AUDIT agent to verify 12 blockers resolved

---

**END OF IMPLEMENTATION GUIDE**
