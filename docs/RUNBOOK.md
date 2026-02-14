# DMS — Runbook (Local & CI)

Constitution V3 compliant. Reference: `docs/CADRE_TRAVAIL.md`, `docs/constitution_v3_addendum.md`.

## Tech Stack

- **Backend:** FastAPI, Python 3.11
- **DB:** PostgreSQL only (Constitution V2.1 ONLINE-ONLY)
- **Migrations:** Alembic
- **Tests:** pytest

## Prerequisites

- Python 3.11+
- Docker (for local PostgreSQL)
- Git

## 1. Clone & Branch Strategy

```bash
git clone https://github.com/ousma15abdoulaye-crypto/decision-memory-v1
cd decision-memory-v1
```

**Branch strategy:**
- `main` = protected, stable, deployable
- Work branches: `feature/<topic>` or `fix/<topic>` or `infra/<topic>`

## 2. Python Environment

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Database (Local)

```bash
# Start PostgreSQL via Docker Compose
docker compose up -d

# Wait for health (~5s), then set env
# Windows PowerShell:
$env:DATABASE_URL = "postgresql+psycopg://dms:dms@localhost:5432/dms"
# Linux/macOS:
# export DATABASE_URL="postgresql+psycopg://dms:dms@localhost:5432/dms"
```

## 4. Migrations

```bash
alembic upgrade head
```

## 5. Run Tests (Local = CI parity)

```bash
$env:DATABASE_URL = "postgresql+psycopg://dms:dms@localhost:5432/dms"
$env:TESTING = "true"
$env:PYTHONPATH = "."
pytest tests/ -v --tb=short
```

Linux/macOS:
```bash
export DATABASE_URL="postgresql+psycopg://dms:dms@localhost:5432/dms"
export TESTING="true"
export PYTHONPATH="."
pytest tests/ -v --tb=short
```

## 6. Run Application (Local)

```bash
$env:DATABASE_URL = "postgresql+psycopg://dms:dms@localhost:5432/dms"
python main.py
# or: uvicorn main:app --reload --port 5000
```

App: http://localhost:5000

## 7. CI Parity (Same as `.github/workflows/ci.yml`)

| Step              | Command |
|-------------------|---------|
| Install deps      | `pip install -r requirements.txt` |
| Migrations        | `alembic upgrade head` (DATABASE_URL set) |
| Tests             | `pytest tests/ -v --tb=short` (PYTHONPATH=.) |

## 8. Environment Variables

| Variable      | Required | Description |
|---------------|----------|-------------|
| DATABASE_URL  | Yes      | `postgresql+psycopg://user:pass@host:port/db` |
| PORT          | No       | Server port (default 5000, Railway uses $PORT) |
| TESTING       | No       | Set to `true` for test mode |

See `.env.example` for template.

## 9. Git Configuration (Workspace)

Before first commit, configure identity:

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

Use without `--global` to scope to this repo only.

## 10. Healthcheck

- `GET /` — App info
- `GET /health` — Health status
- `GET /api/constitution` — Invariants (Constitution V3)
