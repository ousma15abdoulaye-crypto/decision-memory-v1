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
COPY services/annotation-backend/start.sh .
RUN chmod +x start.sh

COPY src/__init__.py ./src/__init__.py
COPY src/annotation ./src/annotation

# Pas de CMD inline : sur Railway le JSON + $$ produisait « 1{PORT} » / « 1PORT » (sh : $$ = PID).
CMD ["./start.sh"]
