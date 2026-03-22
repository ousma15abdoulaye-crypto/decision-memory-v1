# Build context MUST be the monorepo root (Railway: Root Directory = repo root, not this folder).
#   docker build -f services/annotation-backend/Dockerfile .
#
# If Railway "Root Directory" is services/annotation-backend only, COPY ../src is impossible —
# set Root Directory to "." / empty in Service → Settings.
#
# Après ajout de modules Python : redéployer sans cache si besoin (évite un vieux layer sans *.py).

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/annotation-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tout le dossier backend (tests exclus par .dockerignore à la racine du repo).
# Évite tout ModuleNotFoundError si un *.py ou sous-dossier manque au COPY explicite.
COPY services/annotation-backend/ .
RUN chmod +x start.sh

COPY src/__init__.py ./src/__init__.py
COPY src/annotation ./src/annotation

# Pas de CMD inline : sur Railway le JSON + $$ produisait « 1{PORT} » / « 1PORT » (sh : $$ = PID).
CMD ["./start.sh"]
