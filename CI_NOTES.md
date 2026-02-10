# CI Configuration Notes

## Constitution V2.1 Compliance

### Setup
- **PostgreSQL**: 16 (not 15)
- **Driver**: psycopg (not asyncpg)
- **Requirements**: requirements.txt (not requirements_v2.txt)
- **PYTHONPATH**: Set at job level to `${{ github.workspace }}`

### DATABASE_URL
```
postgresql+psycopg://dms:dms@localhost:5432/dms
```

### Smoke Test
- **Location**: `scripts/smoke_postgres.py`
- **Requirements**:
  - DATABASE_URL must be set (exits 1 if missing)
  - Uses `from src.db import engine, init_db_schema`
  - Verifies `engine.dialect.name == "postgresql"`
  - Runs `init_db_schema()` then `SELECT 1`
  - No async code, no import-only checks

### Test Execution
Single command runs all tests:
```bash
python -m pytest tests/ -v --tb=short
```

### CI Steps
1. Checkout
2. Setup Python 3.11
3. Wait for PostgreSQL ready
4. Install dependencies (requirements.txt)
5. Compile check
6. Run tests (pytest)
7. Run smoke test (validate real Postgres)

### Expected Output
```
✅ PostgreSQL is ready
✅ Imported engine from src.db
✅ PostgreSQL dialect confirmed
✅ Connection test successful
✅ SMOKE TEST PASSED
```

### Definition of DONE
- CI uses Postgres 16 ✓
- DATABASE_URL uses psycopg ✓
- smoke_postgres.py fails without DATABASE_URL ✓
- smoke_postgres.py passes with DATABASE_URL ✓
- No asyncpg or requirements_v2.txt imposed ✓
- CI green ✓
