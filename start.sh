#!/bin/bash
# Script de démarrage Railway — M2
# Exécute les migrations Alembic puis démarre uvicorn.
set -e
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[start.sh] ERROR: DATABASE_URL is required (PostgreSQL). Add a Railway Postgres" >&2
  echo "[start.sh] plugin to this service and link it, or set DATABASE_URL in Variables." >&2
  exit 1
fi
echo "[start.sh] Running alembic upgrade head..."
alembic upgrade head
echo "[start.sh] Migrations done. Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
