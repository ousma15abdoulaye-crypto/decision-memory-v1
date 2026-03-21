#!/bin/sh
set -e

# Image attendue : Dockerfile services/annotation-backend (backend.py à la racine de WORKDIR).
# Si ce fichier manque, Railway build probablement le Dockerfile racine (API DMS) : /health LS échouera.
if [ ! -f ./backend.py ]; then
  echo "[start.sh] ERROR: backend.py absent — ce conteneur n'est pas l'image annotation-backend." >&2
  echo "[start.sh] Vérifier Dockerfile Path = services/annotation-backend/Dockerfile et root = repo." >&2
  exit 1
fi

if [ -z "${MISTRAL_API_KEY}" ]; then
  echo "[start.sh] ERROR: MISTRAL_API_KEY is required." >&2
  exit 1
fi

PORT="${PORT:-8080}"
echo "[start.sh] DMS annotation-backend — uvicorn backend:app — port=$PORT (Label Studio: GET /health)"
exec uvicorn backend:app --host 0.0.0.0 --port "$PORT" --log-level info 2>&1
