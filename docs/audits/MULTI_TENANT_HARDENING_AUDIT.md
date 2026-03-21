# Multi-Tenant Isolation Hardening Audit

**Date:** 2026-03-21
**Auditor:** Principal Systems Engineer (automated)
**System:** DMS V4.1.0 — Decision Memory System
**Status:** ⚠️ HARDENING IN PROGRESS

---

## PHASE 1 — REALITY CHECK

### 1. DATA ISOLATION

| Question | Answer | Evidence |
|----------|--------|----------|
| Are all tables tenant-scoped? | **NO** | Only 8/90+ tables have `org_id` |
| Are all joins tenant-safe? | **NO** | Committee sub-tables join without org_id |
| Are there any global reads? | **YES** | `src/api/cases.py:70` — `SELECT * FROM cases` |

**Tables WITH org_id (8 tables):**
- `criteria` — `alembic/versions/020_m_criteria_typing.py`
- `committees` — `alembic/versions/028_create_committee_tables.py`
- `market_surveys` — `alembic/versions/042_market_surveys.py`
- `price_anomaly_alerts` — `alembic/versions/042_market_surveys.py`
- `survey_campaigns` — `alembic/versions/042_market_surveys.py`
- `survey_campaign_items` — `alembic/versions/042_market_surveys.py`
- `survey_campaign_zones` — `alembic/versions/042_market_surveys.py`
- `decision_history` — `alembic/versions/044_decision_history.py`

**Tables WITHOUT org_id (CRITICAL — core tables):**
- `cases` — `alembic/versions/002_add_couche_a.py`
- `artifacts` — `alembic/versions/002_add_couche_a.py`
- `documents` — `alembic/versions/002_add_couche_a.py`
- `extractions` — `alembic/versions/002_add_couche_a.py`
- `offers` — `alembic/versions/002_add_couche_a.py`
- `memory_entries` — `alembic/versions/002_add_couche_a.py`
- `pipeline_runs` — `alembic/versions/032_create_pipeline_runs.py`
- `audit_log` — `alembic/versions/038_audit_hash_chain.py`

### 2. ENFORCEMENT LEVEL

| Question | Answer | Evidence |
|----------|--------|----------|
| Is isolation enforced at DB level? | **NO** | Zero RLS policies pre-migration 051 |
| Only at application level? | **YES** | `src/couche_a/criteria/service.py` — `WHERE org_id = %s` |

### 3. LEAKAGE PATHS

| Path | File | Impact |
|------|------|--------|
| `GET /api/cases` — no auth, no org_id | `src/api/cases.py:70` | Returns ALL cases to ANY caller |
| `GET /api/cases/{id}` — no org_id | `src/api/cases.py:77` | Any case accessible by ID |
| `POST /api/upload/{case_id}/{kind}` — no auth | `src/api/documents.py` | Upload to any case |
| `GET /api/download/{case_id}/{kind}` — no auth | `src/api/documents.py` | Download from any case |
| Committee GET without org_id filter | `src/couche_a/committee/service.py:46` | Cross-org committee access |
| Cases table has no org_id column | `alembic/versions/002_add_couche_a.py` | No tenant isolation possible |

### 4. LOGIC CONTAMINATION

| Question | Answer | Evidence |
|----------|--------|----------|
| Country/tenant logic inside core? | **NO** | Core engine is context-agnostic |
| Hardcoded branching? | **NO** | No country-specific branching in scoring/pipeline |

---

## PHASE 2 — FAILURE SIMULATION

### CRITICAL Scenarios

**CRIT-1: Unauthorised Case Listing**
- Entry: `GET /api/cases`
- Path: No auth required → `SELECT * FROM cases ORDER BY created_at DESC`
- Leak: ALL cases from ALL tenants returned
- Impact: Full data exposure of case titles, types, statuses

**CRIT-2: Cross-Tenant Document Download**
- Entry: `GET /api/download/{case_id}/dao`
- Path: No auth → case_id lookup → file served
- Leak: Documents from any tenant accessible by guessing case_id (UUID)
- Impact: Sensitive procurement documents (DAO, offers) exposed

**CRIT-3: Cross-Org Committee Read**
- Entry: `GET /committee/{committee_id}`
- Path: No auth → `SELECT * FROM committees WHERE committee_id = %s` (no org_id)
- Leak: Committee decisions, members, rationale visible cross-org
- Impact: Procurement decision data leak; legal exposure

### HIGH Scenarios

**HIGH-1: Unscoped Pipeline Execution**
- Entry: `POST /{case_id}/pipeline/a/run`
- Path: Pipeline runs stored without org_id
- Issue: Cannot audit which org triggered pipeline execution
- Impact: Audit trail incomplete; non-repudiation failure

**HIGH-2: Memory Entry Cross-Access**
- Entry: `GET /api/memory/{case_id}`
- Path: No auth → `SELECT * FROM memory_entries WHERE case_id = :cid`
- Issue: Memory entries (decision rationale) accessible cross-tenant
- Impact: Strategic procurement intelligence leaked

**HIGH-3: Analysis Without Tenant Boundary**
- Entry: `POST /api/analyze`
- Path: No auth → case lookup → full analysis
- Issue: Any caller can trigger analysis on any case
- Impact: Computational resource abuse; result exposure

---

## PHASE 3 — GAP CLASSIFICATION

| Category | Count | Examples |
|----------|-------|---------|
| **CRITICAL** | 3 | No auth on case listing, document download, committee read |
| **HIGH** | 5 | Unscoped pipeline, memory entries, analysis, committee queries ignore org_id |
| **MEDIUM** | 4 | Cases table missing org_id, pipeline_runs missing org_id, audit_log unscoped |
| **LOW** | 2 | Reference tables (geo, items) globally shared by design |

**System Risk Level: FRAGILE**

The system has partial multi-tenant isolation (criteria module is well-designed)
but critical endpoints lack authentication and tenant scoping. The cases table —
the foundational entity — has no org_id column.

---

## PHASE 4 — ENFORCEMENT DESIGN

### A. DATABASE (MANDATORY LAYER)

**Migration 051 — RLS Policies (IMPLEMENTED)**

```sql
-- Enable RLS on all org_id-bearing tables
ALTER TABLE public.criteria ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.committees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.market_surveys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_anomaly_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.survey_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.survey_campaign_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.survey_campaign_zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_history ENABLE ROW LEVEL SECURITY;

-- Policy pattern (applied to each table)
CREATE POLICY rls_tenant_{table} ON public.{table}
  USING (
    org_id = current_setting('app.org_id', true)
    OR current_setting('app.org_id', true) = ''
  )
  WITH CHECK (
    org_id = current_setting('app.org_id', true)
    OR current_setting('app.org_id', true) = ''
  );
```

**Future Migration — Add org_id to cases (PLANNED)**

```sql
-- Step 1: Add nullable org_id
ALTER TABLE public.cases ADD COLUMN org_id TEXT;

-- Step 2: Backfill from owner's org
UPDATE public.cases c
SET org_id = u.org_id
FROM public.users u
WHERE c.owner_id = u.id;

-- Step 3: Set NOT NULL
ALTER TABLE public.cases ALTER COLUMN org_id SET NOT NULL;

-- Step 4: Add index
CREATE INDEX idx_cases_org_id ON public.cases (org_id);

-- Step 5: Enable RLS
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_tenant_cases ON public.cases
  USING (org_id = current_setting('app.org_id', true));
```

### B. APPLICATION

**Tenant Context Middleware (IMPLEMENTED)**
- `src/middleware/tenant_context.py` — `TenantContextMiddleware`
- Extracts `org_id` from JWT claims and query parameters
- Stores in `request.state.org_id`
- Provides `set_tenant_context(conn, org_id)` helper

**Forbidden Patterns:**
- `SELECT * FROM {tenant_table}` without `WHERE org_id = %s`
- `DELETE FROM {tenant_table}` without `AND org_id = %s`
- `UPDATE {tenant_table} SET ... ` without `WHERE org_id = %s`
- Any endpoint accessing tenant data without auth

**Safe Patterns (Approved):**
- `WHERE case_id = %s AND org_id = %s` (criteria service pattern)
- `org_id: str = Query(...)` mandatory query parameter
- `set_tenant_context(conn, org_id)` before tenant queries

### C. TESTING (IMPLEMENTED)

**File:** `tests/invariants/test_tenant_isolation.py`

- `test_tenant_scoped_tables_have_org_id_in_queries` — static AST analysis
- `test_no_global_select_on_tenant_tables` — regex scan for unscoped SELECTs
- `test_rls_migration_exists` — verifies RLS migration present
- `test_tenant_middleware_exists` — verifies middleware present

---

## PHASE 5 — EXECUTION PLAN

| Step | Objective | Files | Risk | Rollback |
|------|-----------|-------|------|----------|
| S-01 | Create tenant middleware | `src/middleware/tenant_context.py`, `main.py` | LOW | Remove middleware import |
| S-02 | Add RLS migration | `alembic/versions/051_rls_tenant_isolation.py` | LOW | `alembic downgrade -1` |
| S-03 | Add invariant tests | `tests/invariants/test_tenant_isolation.py` | NONE | Remove test file |
| S-04 | Add org_id to cases table | New migration (FUTURE) | MEDIUM | `alembic downgrade -1` |
| S-05 | Add auth to unprotected endpoints | `src/api/cases.py`, `src/api/documents.py` | MEDIUM | Revert file |
| S-06 | Enable FORCE RLS | New migration (FUTURE) | HIGH | `alembic downgrade -1` |
| S-07 | Add org_id to JWT claims | `src/couche_a/auth/jwt_handler.py` | LOW | Revert file |

**Steps S-01 through S-03 are implemented in this PR.**
Steps S-04 through S-07 require dedicated mandates.

---

## PHASE 6 — VERDICT

### 1. Is the system PRODUCTION-SAFE for multi-tenant?

**NO**

### 2. Risk Assessment

- **Time to failure:** First external user with API access can enumerate all cases immediately.
- **First catastrophic event:** `GET /api/cases` returns all tenant data without authentication.

### 3. Minimum Enforcement Set for Non-Breakable Isolation

| # | Requirement | Status |
|---|-------------|--------|
| 1 | RLS policies on org_id tables | ✅ DONE (migration 051) |
| 2 | Tenant context middleware | ✅ DONE |
| 3 | CI invariant tests | ✅ DONE |
| 4 | org_id on cases table | ❌ FUTURE — requires dedicated migration |
| 5 | Auth on ALL endpoints | ❌ FUTURE — requires endpoint-by-endpoint audit |
| 6 | FORCE RLS enabled | ❌ FUTURE — requires all code paths to set org_id |
| 7 | org_id in JWT claims | ❌ FUTURE — requires auth system update |

**This PR delivers items 1-3 (infrastructure layer). Items 4-7 require dedicated mandates.**
