# Build context MUST be the monorepo root (Railway: Root Directory = repo root, not this folder).
#   docker build -f services/annotation-backend/Dockerfile .
#
# If Railway "Root Directory" is services/annotation-backend only, COPY ../src is impossible —
# set Root Directory to "." / empty in Service → Settings.

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/annotation-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/annotation-backend/backend.py .
COPY services/annotation-backend/annotation_qa.py .
COPY services/annotation-backend/prompts/ ./prompts/

COPY src/__init__.py ./src/__init__.py
COPY src/annotation ./src/annotation

# Pas de COPY start.sh : démarrage inline. En Dockerfile, $$ → $ pour le shell final.
# Ne jamais écrire $$PORT : sous sh, $$ = PID (souvent 1) → littéral « 1PORT » si mal réduit.
CMD ["/bin/sh", "-c", "set -e; \
  if [ ! -f ./backend.py ]; then echo '[start] ERROR: backend.py absent — mauvaise image.' >&2; exit 1; fi; \
  if [ -z \"$${MISTRAL_API_KEY}\" ]; then echo '[start] ERROR: MISTRAL_API_KEY is required.' >&2; exit 1; fi; \
  PORT=$${PORT:-8080}; \
  echo \"[start] DMS annotation-backend — uvicorn backend:app — port=$${PORT}\"; \
  exec uvicorn backend:app --host 0.0.0.0 --port \"$${PORT}\" --log-level info"]
