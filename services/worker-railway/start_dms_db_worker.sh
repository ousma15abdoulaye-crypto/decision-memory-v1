#!/usr/bin/env bash
# M6X-E startup smoke diagnostics for dms-db-worker (Railway Docker).
# No env dump, secrets, DATABASE_URL, or raw payloads.
set -eu

echo "[M6X-E] pwd=$(pwd)"

echo "[M6X-E] python_version:"
python --version || echo "[M6X-E] python_missing"

echo "[M6X-E] which_python="
which python || echo "[M6X-E] which_python_FAILED"

echo "[M6X-E] which_uvicorn="
which uvicorn || echo "[M6X-E] which_uvicorn_FAILED"

echo "[M6X-E] ls_app="
ls -la /app || echo "[M6X-E] ls_app_FAILED"

if test -d /app/src; then
  echo "[M6X-E] APP_SRC_DIR=YES"
else
  echo "[M6X-E] APP_SRC_DIR=NO"
fi

if test -f /app/services/worker-railway/main.py; then
  echo "[M6X-E] WORKER_MAIN_PY=YES"
else
  echo "[M6X-E] WORKER_MAIN_PY=NO"
fi

python -c 'import sys; print("[M6X-E] sys.path=" + repr(sys.path))'

# Avoid isolated import of src here: cwd is worker-railway and set -e would exit before uvicorn.
# Resolving src/ is exercised by importing main (_bootstrap_repo_root_for_src).

python -c 'import main; print("MAIN_IMPORT_OK")'

echo "[M6X-E] exec_uvicorn"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
