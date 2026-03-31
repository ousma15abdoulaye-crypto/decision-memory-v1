#!/bin/bash
# Script de démarrage Railway — M2
# Exécute les migrations Alembic puis démarre uvicorn.
set -e
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[start.sh] ERROR: DATABASE_URL is required (PostgreSQL). Add a Railway Postgres" >&2
  echo "[start.sh] plugin to this service and link it, or set DATABASE_URL in Variables." >&2
  exit 1
fi
if [ "${DMS_ALLOW_RAILWAY_MIGRATE:-0}" = "1" ]; then
  echo "[start.sh] DMS_ALLOW_RAILWAY_MIGRATE=1 — running alembic upgrade head..."
  alembic upgrade head
  echo "[start.sh] Migrations done."
else
  echo "[start.sh] Migrations skipped (REGLE-ANCHOR-06). Set DMS_ALLOW_RAILWAY_MIGRATE=1 to apply on Railway."
fi
echo "[start.sh] Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
