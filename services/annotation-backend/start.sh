#!/bin/sh
set -e

if [ -z "${MISTRAL_API_KEY}" ]; then
  echo "[start.sh] ERROR: MISTRAL_API_KEY is required." >&2
  exit 1
fi

PORT="${PORT:-8080}"
echo "[start.sh] Starting uvicorn on port $PORT"
exec uvicorn backend:app --host 0.0.0.0 --port "$PORT" --log-level info 2>&1
