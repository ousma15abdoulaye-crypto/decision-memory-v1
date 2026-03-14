#!/bin/sh
# DMS Annotation ML Backend — startup script
# Runtime checks only. No build-time secrets.
set -e

if [ -z "${MISTRAL_API_KEY}" ]; then
  echo "[start.sh] ERROR: MISTRAL_API_KEY is required at runtime." >&2
  echo "[start.sh] Configure it in Railway Variables (runtime only)." >&2
  exit 1
fi

PORT="${PORT:-9090}"
exec uvicorn backend:app --host 0.0.0.0 --port "$PORT" --log-level info
