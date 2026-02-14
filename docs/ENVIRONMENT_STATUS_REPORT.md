# Environment Status Report — Workspace Setup

**Date:** 2026-02-14  
**Branch:** `infra/workspace-setup-ci-railway`  
**Mission:** Prepare full working environment for DMS (Constitution V3 compliant)

---

## A) Constitution / Invariants Summary

**Reference:** `docs/constitution_v3_addendum.md` (V3.1 FROZEN)

### Key Invariants (DO NOT VIOLATE)

- **cognitive_load_never_increase** — Features must reduce mental effort
- **human_decision_final** — System never decides; human always decides
- **no_scoring_no_ranking_no_recommendations** — No vendor recommendations or global scoring
- **memory_is_byproduct_never_a_task** — Couche B feeds from real activity, not manual data entry
- **erp_agnostic** — No ERP dependency
- **online_only** — PostgreSQL only; no SQLite fallback
- **traceability_keep_sources** — Append-only, timestamps
- **one_dao_one_cba_one_pv** — One consolidated output per process

### Stack (Constitution §3)

- Backend: FastAPI, Python 3.11
- DB: PostgreSQL, Alembic (no ORM for app logic)
- Auth: JWT + RBAC
- CI: GitHub Actions
- CD: Railway (Nixpacks)

### Frontier Couche A / B

- Couche B is **read-only** vis-à-vis Couche A
- No B module may modify scores, rankings, or exports

---

## B) Workspace / Tooling Installed

| Item | Status |
|------|--------|
| `.gitignore` | Updated: `.env`, `.env.local`, `.env.*.local` excluded |
| `.vscode/extensions.json` | Created: Python, Pylance, Ruff, YAML, GitLens, EditorConfig, Docker, Markdown |
| `.editorconfig` | Created: indent 4, UTF-8, trim trailing WS |
| Branch strategy | Documented in RUNBOOK: main protected, work branches `feature/`, `fix/`, `infra/` |

### Extensions to Install (Cursor/VS Code)

Run "Install Recommended Extensions" or install manually:

- `ms-python.python`
- `ms-python.vscode-pylance`
- `charliermarsh.ruff`
- `redhat.vscode-yaml`
- `eamodio.gitlens`
- `editorconfig.editorconfig`
- `ms-azuretools.vscode-docker`
- `davidanson.vscode-markdownlint`

---

## C) Local Run Steps (docs/RUNBOOK.md)

1. `python -m venv .venv` && activate
2. `pip install -r requirements.txt`
3. `docker compose up -d` (PostgreSQL)
4. `alembic upgrade head`
5. `pytest tests/ -v --tb=short` (with DATABASE_URL, TESTING, PYTHONPATH)
6. `python main.py` or `uvicorn main:app --reload`

---

## D) CI Status and Fixes

### Changes Made

- Added **Verify syntax (compileall)** step to `.github/workflows/ci.yml` per CADRE_TRAVAIL
- CI pipeline: checkout → Python 3.11 → deps → compileall → migrations → verify migrations → pytest

### CI Pipeline (Unchanged Logic)

- PostgreSQL 15 service
- `alembic upgrade head`
- `pytest tests/ -v --tb=short` with PYTHONPATH

### No `|| true` or Masks

- CI fails clearly if pytest fails (Constitution discipline)

---

## E) Railway Deploy Readiness

| Item | Status |
|------|--------|
| Procfile | ✅ `web: uvicorn main:app --host 0.0.0.0 --port $PORT` |
| runtime.txt | ✅ `python-3.11.9` |
| DATABASE_URL | Documented; Railway PostgreSQL plugin injects |
| Migrations | Documented in docs/RAILWAY_DEPLOY.md (release phase option) |
| Healthcheck | `/health`, `/api/constitution` |
| .env | Never committed; .gitignore updated |

See `docs/RAILWAY_DEPLOY.md` for deployment details.
