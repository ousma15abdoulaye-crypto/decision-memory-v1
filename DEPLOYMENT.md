# DMS Deployment — Constitution V2.1 ONLINE-ONLY

DMS is **online-only**. No SQLite, no offline mode. DATABASE_URL is required.

## Local Development (PostgreSQL)

Use Docker for local Postgres:

```bash
docker run -d --name dms-pg -p 5432:5432 \
  -e POSTGRES_USER=dms -e POSTGRES_PASSWORD=dms -e POSTGRES_DB=dms \
  postgres:16
export DATABASE_URL="postgresql+psycopg://dms:dms@localhost:5432/dms"
python3 -m uvicorn main:app --host 0.0.0.0 --port 5000
```

Or use `docker-compose.yml` if present.

## Railway Deploy

1. **New Project** → Deploy from GitHub → select repo + branch
2. **Add Plugin** → PostgreSQL
3. Confirm **Variables** → `DATABASE_URL` exists
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy
6. Hit `/api/health` and confirm response

## Render / Supabase / Cloud Run

Set `DATABASE_URL` to your provider's Postgres connection string.

## Verification Checklist

- [ ] `DATABASE_URL` present (non-empty)
- [ ] `python3 -c "from src.db import engine; print(engine.dialect.name)"` → postgresql
- [ ] `python3 scripts/smoke_postgres.py` → PASSED
- [ ] Create case → status open → decide → status decided
