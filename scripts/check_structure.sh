#!/bin/bash
echo "🔍 Validation structure repo..."
echo ""

# Fichiers obligatoires
files=(
    ".cursorrules"
    "CURSOR_AGENT_INSTRUCTIONS.md"
    "requirements_v2.txt"
    "alembic.ini"
    "src/couche_b/__init__.py"
    "src/couche_b/models.py"
    "src/couche_b/resolvers.py"
    "src/couche_b/routers.py"
    "src/couche_b/seed.py"
    "tests/couche_b/test_resolvers.py"
    "scripts/seed_production.py"
    "scripts/validate_alignment.py"
)

missing=0
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file MISSING"
        missing=$((missing + 1))
    fi
done

echo ""
if [ $missing -eq 0 ]; then
    echo "🎉 Structure complète! Ready for Cursor agent."
    exit 0
else
    echo "⚠️  $missing fichiers manquants. Review structure."
    exit 1
fi
