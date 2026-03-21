# Build context MUST be the monorepo root:
#   docker build -f services/annotation-backend/Dockerfile .
#
# Copies classifier package (ARCH-02A) so `from src.annotation.document_classifier` works with PYTHONPATH=/app.

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/annotation-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/annotation-backend/backend.py .
COPY services/annotation-backend/prompts/ ./prompts/
COPY services/annotation-backend/start.sh .
RUN chmod +x start.sh

COPY src/__init__.py ./src/__init__.py
COPY src/annotation ./src/annotation

CMD ["./start.sh"]
