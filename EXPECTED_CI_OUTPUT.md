# Expected CI Output After Fix

When the GitHub Actions CI runs on the PR branch, you should see the following output:

## Step 1: Show versions
```
Python 3.11.x
pip 24.x.x
PYTHONPATH=/home/runner/work/decision-memory-v1/decision-memory-v1
DATABASE_URL=postgresql+asyncpg://dms:dms@localhost:5432/dms
```

## Step 2: Wait for PostgreSQL
```
⏳ Waiting for PostgreSQL to be ready...
/tmp:5432 - accepting connections
✅ PostgreSQL is ready
```

## Step 3: Install dependencies
```
Collecting asyncpg==0.29.0
Collecting sqlalchemy==2.0.27
Collecting pytest==8.0.0
Collecting pytest-asyncio==0.23.5
...
Successfully installed asyncpg-0.29.0 sqlalchemy-2.0.27 pytest-8.0.0 ...
```

## Step 4: Sanity import check
```
🔍 Checking imports...
✅ src imported
✅ src.couche_b imported
✅ All Couche B modules imported
```

## Step 5: Compile check
```
🔍 Compiling all Python files...
(no output means success)
```

## Step 6: Run core tests
```
🧪 Running core tests...
test_corrections_smoke.py: OK
test_partial_offers.py: OK
✅ All core tests passed
```

## Step 7: Run Couche B tests
```
🧪 Running Couche B tests...
tests/couche_b/test_resolvers.py::test_normalize_text PASSED
tests/couche_b/test_resolvers.py::test_generate_ulid PASSED
tests/couche_b/test_routers.py::test_router_prefix PASSED
...
✅ Couche B tests completed
```

## Step 8: Run Postgres smoke test
```
🔥 Running PostgreSQL smoke test...
============================================================
SMOKE TEST: PostgreSQL + Couche B
============================================================

🔍 Testing imports...
  ✅ src imported
  ✅ src.couche_b imported
  ✅ All Couche B modules imported
  ✅ Tables defined correctly

📊 DATABASE_URL: postgresql+asyncpg://dms:dms@localhost:5432/dms
🔌 Testing async connection: postgresql+asyncpg://dms:dms@***
✅ Async PostgreSQL connection successful

============================================================
✅ All smoke tests PASSED
============================================================

✅ Smoke test completed
```

## Overall CI Status
```
✅ All checks passed
```

---

## What to Look For

### ✅ SUCCESS Indicators
- PostgreSQL service starts and accepts connections
- PYTHONPATH is set correctly
- All imports work (no ModuleNotFoundError)
- asyncpg driver connects successfully
- All tests pass or skip gracefully

### ❌ FAILURE Indicators (should NOT see)
- ModuleNotFoundError: No module named 'src'
- connection refused (PostgreSQL not ready)
- asyncpg not installed
- Tests fail due to import errors

---

## Troubleshooting

If you see `ModuleNotFoundError: No module named 'src'`:
- Check PYTHONPATH is set in job env
- Verify it's ${{ github.workspace }} not ${{ github.workspace }}/src

If you see `connection refused`:
- Check PostgreSQL service is defined
- Verify pg_isready wait loop completed
- Check DATABASE_URL uses correct host (localhost)

If you see `asyncpg not found`:
- Verify requirements_v2.txt is being installed
- Check cache-dependency-path points to requirements_v2.txt

---

*This is the expected output after CI fix commits dc83be7 and 591ba98*
