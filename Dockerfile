# DMS API — image production / staging (alignée Railway: start.sh + main:app)
# Variables attendues : DATABASE_URL, SECRET_KEY (ou JWT_SECRET), PORT
# Optionnel mais recommandé prod : REDIS_URL (rate limiting réel ; sinon no-op)
# DB prod : préférer un rôle NOBYPASSRLS (ex. dm_app), pas superuser — voir docs/audits/SEC_MT_01_BASELINE.md
#
# Build : docker build -t dms-api .
# Run   : docker run --rm -e DATABASE_URL=... -e SECRET_KEY=... -p 8000:8000 dms-api

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic/ ./alembic/
COPY main.py start.sh ./
COPY src/ ./src/
COPY static/ ./static/
COPY data/ ./data/

RUN chmod +x start.sh \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin dms \
    && chown -R dms:dms /app

USER dms
EXPOSE 8000

ENV PORT=8000
CMD ["./start.sh"]
