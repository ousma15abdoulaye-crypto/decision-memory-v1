#!/usr/bin/env bash
# Apply Ruff auto-fixes so CI passes. Run from repo root.
# Usage: ./scripts/lint_fix.sh  (or: bash scripts/lint_fix.sh)
set -e
cd "$(dirname "$0")/.."
pip install -q ruff
ruff check src tests --fix
echo "Done. Run: git add -u && git status"
