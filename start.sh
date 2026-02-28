#!/bin/bash
# Script de démarrage Railway — M2
# Exécute les migrations Alembic puis démarre uvicorn.
set -e
echo "[start.sh] Running alembic upgrade head..."
alembic upgrade head
echo "[start.sh] Migrations done. Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
