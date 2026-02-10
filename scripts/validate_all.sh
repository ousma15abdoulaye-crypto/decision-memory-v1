#!/usr/bin/env bash
set -e

echo "Running migrations..."
alembic upgrade head

echo "Running Couche B tests..."
pytest tests/couche_b/ -v

echo "Running Couche A tests..."
pytest tests/couche_a/ -v

echo "All checks passed ✅"
