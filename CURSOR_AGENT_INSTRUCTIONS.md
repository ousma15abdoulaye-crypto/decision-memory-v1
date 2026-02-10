# CURSOR AGENT INSTRUCTIONS — Constitution V2.1 Implementation

**VERSION**: 2.1  
**STATUS**: Ready for execution  
**DURATION**: 6 sessions (~3 hours total)

---

## 🎯 OBJECTIVE
Implement Couche B (Market Intelligence Layer) following Constitution DMS V2.1 with 100% alignment.

## 📋 PRE-REQUISITES
✅ Repository structure created  
✅ Skeleton files in place  
✅ .cursorrules configured  
✅ Tests skeleton ready  
✅ Constitution V2.1 available at `docs/constitution_v2.1.md`

---

## 📅 SESSION PLAN

### **SESSION 1: Database Schema (45 min)**

#### 1.1 Setup (10 min)
- [ ] Review Constitution §4 (Catalogs schema)
- [ ] Verify src/db.py is properly configured
- [ ] Test database connection

#### 1.2 Implement Tables (35 min)
**File**: `src/couche_b/models.py`

Implement these 10 tables following Constitution §4:

1. **vendors** (§4.2.1)
   - vendor_id (PK, ULID)
   - canonical_name (unique)
   - status (enum: active/proposed/rejected)
   - created_at, updated_at

2. **vendor_aliases** (§4.2.2)
   - alias_id (PK, ULID)
   - vendor_id (FK → vendors)
   - alias_name
   - confidence_score

3. **vendor_events** (§4.2.3)
   - event_id (PK, ULID)
   - vendor_id (FK → vendors)
   - event_type (merger/split/name_change)
   - event_date
   - details (JSON)

4. **items** (§4.3.1)
   - item_id (PK, ULID)
   - canonical_description
   - category
   - status
   - created_at, updated_at

5. **item_aliases** (§4.3.2)
   - alias_id (PK, ULID)
   - item_id (FK → items)
   - alias_description
   - confidence_score

6. **units** (§4.4.1)
   - unit_id (PK, ULID)
   - canonical_symbol
   - canonical_name
   - unit_type (weight/volume/length/area/count/package)

7. **unit_aliases** (§4.4.2)
   - alias_id (PK, ULID)
   - unit_id (FK → units)
   - alias_symbol
   - alias_name

8. **geo_master** (§4.5.1)
   - geo_id (PK, ULID)
   - canonical_name
   - geo_type (region/city/commune)
   - parent_geo_id (FK → geo_master, nullable)
   - status

9. **geo_aliases** (§4.5.2)
   - alias_id (PK, ULID)
   - geo_id (FK → geo_master)
   - alias_name
   - confidence_score

10. **market_signals** (§5.1)
    - signal_id (PK, ULID)
    - survey_date
    - item_id (FK → items)
    - vendor_id (FK → vendors)
    - geo_id (FK → geo_master)
    - unit_id (FK → units)
    - price_value (decimal)
    - quantity (decimal)
    - status (proposed/validated/rejected)
    - created_at

**Indexes to add:**
- vendors(canonical_name)
- items(canonical_description)
- market_signals(survey_date, geo_id, item_id)
- All FK columns

**Commit**: `feat: Implement Couche B database schema (Constitution §4)`

---

### **SESSION 2: Resolvers & Seed (60 min)**

#### 2.1 Implement Resolvers (35 min)
**File**: `src/couche_b/resolvers.py`

Implement functions following Constitution §5.2:

1. **normalize_text(text: str) -> str**
   - Lowercase
   - Remove accents (unicodedata)
   - Strip whitespace
   - Remove special chars

2. **generate_ulid() -> str**
   - Use timestamp + random
   - Sortable format

3. **resolve_vendor(conn, vendor_name: str, threshold: int = 85) -> str**
   - Step 1: Exact match in vendors.canonical_name
   - Step 2: Exact match in vendor_aliases.alias_name
   - Step 3: Fuzzy match (fuzzywuzzy.fuzz.ratio >= threshold)
   - Step 4: Create proposed vendor if no match
   - Return: vendor_id

4. **resolve_item(conn, item_description: str, threshold: int = 85) -> str**
   - Same pattern as resolve_vendor
   - Return: item_id

5. **resolve_unit(conn, unit_text: str) -> str**
   - Exact match ONLY (no fuzzy)
   - Check canonical_symbol + aliases
   - Raise error if not found (strict)
   - Return: unit_id

6. **resolve_geo(conn, location_name: str, threshold: int = 90) -> str**
   - Same pattern as resolve_vendor
   - Higher threshold (90%) for accuracy
   - Return: geo_id

**Tests**: `tests/couche_b/test_resolvers.py`

**Commit**: `feat: Implement entity resolvers (Constitution §5.2)`

#### 2.2 Implement Seed Data (25 min)
**File**: `src/couche_b/seed.py`

Insert initial data (§4.4, §4.5):

**Geo Zones (8 for Mali)**:
- Bamako
- Gao
- Tombouctou
- Mopti
- Sikasso
- Ségou
- Kayes
- Koulikoro

**Units (9 standard)**:
- kg (kilogramme, weight)
- tonne (tonne, weight)
- L (litre, volume)
- m³ (mètre cube, volume)
- m (mètre, length)
- m² (mètre carré, area)
- pièce (pièce, count)
- sac (sac, package)
- carton (carton, package)

**Vendors (3 common)**:
- SOGELEC
- SOMAPEP
- COVEC

**Items (5 common)**:
- Ciment (50kg)
- Fer 12mm (barre)
- Riz (importé)
- Huile (végétale)
- Sucre (cristallisé)

**Tests**: `tests/couche_b/test_seed.py`

**Commit**: `feat: Add Mali seed data (Constitution §4.4-4.5)`

---

### **SESSION 3: API Endpoints (60 min)**

#### 3.1 Catalog Search (30 min)
**File**: `src/couche_b/routers.py`

Implement autocomplete endpoints:

1. **GET /api/catalog/vendors/search**
   - Search in vendors + vendor_aliases
   - Fuzzy match if needed
   - Return top 10 matches

2. **GET /api/catalog/items/search**
   - Search in items + item_aliases
   - Return top 10 matches

3. **GET /api/catalog/units/search**
   - Search in units + unit_aliases
   - Exact + prefix match only

4. **GET /api/catalog/geo/search**
   - Search in geo_master + geo_aliases
   - Return top 10 matches

**Response format**:
```json
[
  {
    "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "canonical_name": "SOGELEC",
    "match_type": "exact|alias|fuzzy",
    "confidence": 100
  }
]
```

**Commit**: `feat: Implement catalog search endpoints (Constitution §6.1)`

#### 3.2 Market Survey (30 min)
**File**: `src/couche_b/routers.py`

Implement survey endpoints:

1. **POST /api/market-survey**
   - Accept survey data
   - Use resolvers for all entities
   - Create market_signals with status='proposed'
   - Return signal_id

2. **GET /api/market-survey/validation-queue**
   - List all proposed signals
   - Filter by entity type
   - Pagination support

3. **PATCH /api/market-survey/{signal_id}/validate**
   - Admin only
   - Actions: approve → validate, reject → delete
   - If approve: update status to 'validated'

**Request format**:
```json
{
  "survey_date": "2024-01-15",
  "vendor_name": "SOGELEC",
  "item_description": "Ciment 50kg",
  "unit": "sac",
  "location": "Bamako",
  "price": 4500,
  "quantity": 100
}
```

**Commit**: `feat: Implement market survey endpoints (Constitution §6.2)`

---

### **SESSION 4: Market Intelligence (45 min)**

#### 4.1 Search Intelligence (25 min)
**File**: `src/couche_b/routers.py`

Implement:

**GET /api/market-intelligence/search**
- Filters: item, geo, vendor, date_from, date_to
- Only validated signals
- Return with canonical names
- Pagination (50 per page)

**Response**:
```json
{
  "total": 150,
  "page": 1,
  "signals": [
    {
      "signal_id": "...",
      "survey_date": "2024-01-15",
      "item": "Ciment 50kg",
      "vendor": "SOGELEC",
      "geo": "Bamako",
      "unit": "sac",
      "price": 4500,
      "quantity": 100
    }
  ]
}
```

**Commit**: `feat: Implement market intelligence search (Constitution §6.3)`

#### 4.2 Statistics (20 min)
**File**: `src/couche_b/routers.py`

Implement:

**GET /api/market-intelligence/stats**
- Required: item_id
- Optional: geo_id, date_from, date_to
- Calculate: avg, min, max, median, count
- Only validated signals

**Response**:
```json
{
  "item": "Ciment 50kg",
  "geo": "Bamako",
  "period": "2024-01-01 to 2024-01-31",
  "stats": {
    "avg_price": 4450.50,
    "min_price": 4200,
    "max_price": 4800,
    "median_price": 4500,
    "count": 45
  }
}
```

**Commit**: `feat: Implement market statistics (Constitution §6.3)`

---

### **SESSION 5: Testing & Validation (30 min)**

#### 5.1 Complete Tests (15 min)
Ensure all test files have:
- Unit tests for all resolvers
- Integration tests for all endpoints
- Edge case coverage
- Error handling tests

**Files**:
- tests/couche_b/test_resolvers.py
- tests/couche_b/test_routers.py
- tests/couche_b/test_seed.py

**Target**: >80% coverage

**Commit**: `test: Complete Couche B test suite`

#### 5.2 Run Validation (15 min)
```bash
# Run tests
pytest tests/couche_b/ -v --cov=src/couche_b

# Run validation script
python scripts/validate_alignment.py

# Check structure
./scripts/check_structure.sh
```

**Fix any issues found**

**Commit**: `chore: Validate alignment with Constitution V2.1`

---

### **SESSION 6: Documentation & Polish (30 min)**

#### 6.1 Update Docs (20 min)
- [ ] Complete docs/API_COUCHE_B.md with examples
- [ ] Complete docs/RESOLVERS_GUIDE.md with examples
- [ ] Add README section for Couche B
- [ ] Add migration guide from V1 to V2

**Commit**: `docs: Complete Couche B documentation`

#### 6.2 Final Review (10 min)
- [ ] Run all tests
- [ ] Check code quality (ruff, mypy)
- [ ] Verify all TODOs resolved
- [ ] Review commit history
- [ ] Update CHANGELOG.md

**Commit**: `chore: Finalize Couche B implementation`

---

## ✅ COMPLETION CHECKLIST

### Code Quality
- [ ] All tests pass (100%)
- [ ] Coverage >80%
- [ ] No linting errors
- [ ] Type hints complete
- [ ] Docstrings complete

### Alignment
- [ ] Schema matches Constitution §4
- [ ] Resolvers follow Constitution §5.2
- [ ] API matches Constitution §6
- [ ] Seed data matches §4.4-4.5

### Documentation
- [ ] API_COUCHE_B.md complete
- [ ] RESOLVERS_GUIDE.md complete
- [ ] README updated
- [ ] CHANGELOG updated

### Validation
- [ ] validate_alignment.py passes
- [ ] check_structure.sh passes
- [ ] Manual testing completed

---

## 🚀 READY TO START
Repository is now prepared for Cursor agent execution. Start with Session 1.1.

**Next command**:
```bash
cursor .
# Then follow SESSION 1 instructions
```
