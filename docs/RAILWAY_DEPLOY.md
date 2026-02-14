# DMS — Railway Deployment (Constitution V3)

CD target: Railway (Nixpacks). Constitution V2.1: ONLINE-ONLY (PostgreSQL).

## Detection

Railway auto-detects:
- **Runtime:** Python 3.11 (from `runtime.txt`)
- **Start command:** From `Procfile` → `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Build:** `pip install -r requirements.txt`

## Required Environment Variables

| Variable      | Required | Description |
|---------------|----------|-------------|
| DATABASE_URL  | **Yes**  | PostgreSQL connection string. Add Railway PostgreSQL plugin → URL auto-injected. Format: `postgresql+psycopg://user:pass@host:port/db` |
| PORT          | No       | Railway injects automatically |

## Migrations Strategy

1. **Pre-deploy:** Run migrations manually or via release command
2. **Option A (manual):** Before first deploy, run `alembic upgrade head` against production DB
3. **Option B (release phase):** Add to `Procfile` or Railway release command:
   ```
   release: alembic upgrade head
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
   Railway runs `release` before `web` on deploy.

## Healthcheck

- **Endpoint:** `GET /health` or `GET /`
- **Constitution:** `GET /api/constitution` — returns invariants

Railway uses HTTP health checks by default. Ensure the app responds on `$PORT`.

## Boot Verification

- App binds to `0.0.0.0` (all interfaces)
- Port read from `$PORT` (Railway sets this)
- `init_db_schema()` runs on startup (creates tables if missing; Alembic for migrations)

## Secrets

- **Never commit** `.env` or credentials
- Use Railway Variables for `DATABASE_URL` and any API keys
- `.env.example` documents expected vars (no secrets)
