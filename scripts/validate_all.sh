#!/usr/bin/env bash
set -e

echo "This repo's hard gates are compileall + two core tests. Alembic and couche_* tests are optional when present."

echo "Running compileall..."
python -m compileall . -q

echo "Running core test: corrections smoke..."
python3 tests/test_corrections_smoke.py

echo "Running core test: partial offers..."
python3 tests/test_partial_offers.py

if command -v alembic >/dev/null 2>&1; then
  echo "Running migrations..."
  alembic upgrade head
else
  echo "SKIP alembic (not installed)"
fi

if [ -d tests/couche_b ]; then
  echo "Running Couche B tests..."
  pytest tests/couche_b/ -v
else
  echo "SKIP tests/couche_b (directory missing)"
fi

if [ -d tests/couche_a ]; then
  echo "Running Couche A tests..."
  pytest tests/couche_a/ -v
else
  echo "SKIP tests/couche_a (directory missing)"
fi

echo "All checks passed ✅"
