FROM docker.io/library/python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY backend.py .
COPY prompts/ ./prompts/
COPY src/ ./src/
COPY start.sh .
RUN chmod +x start.sh
