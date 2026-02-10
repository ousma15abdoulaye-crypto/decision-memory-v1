#!/usr/bin/env python3
"""
Validate codebase alignment with Constitution V2.1
Usage: python scripts/validate_alignment.py
"""

import subprocess
import sys
import os
from pathlib import Path

def check(name: str, cmd: str, expected: str = None):
    """Run check and report"""
    print(f"⏳ {name}...", end=" ")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ FAIL")
        print(result.stderr)
        return False
    
    if expected and expected not in result.stdout:
        print(f"❌ FAIL (expected: {expected})")
        return False
    
    print("✅ PASS")
    return True

def main():
    print("=" * 60)
    print("VALIDATION ALIGNMENT CONSTITUTION V2.1")
    print("=" * 60)
    print()
    
    # Detect database type
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/dms.sqlite3")
    is_postgres = "postgresql" in database_url
    
    checks = [
        ("Async migration", "grep -r '^def ' main.py | wc -l", "0"),
        ("Tests pass", "pytest tests/ -v --tb=short"),
    ]
    
    # Add PostgreSQL-specific checks only if using PostgreSQL
    if is_postgres:
        checks.extend([
            ("Couche B tables", "psql $DATABASE_URL -c '\\dt couche_b.*' 2>/dev/null | grep -c table", "9"),
            ("Seed geo", "psql $DATABASE_URL -c 'SELECT COUNT(*) FROM couche_b.geo_master' 2>/dev/null", "8"),
            ("Seed units", "psql $DATABASE_URL -c 'SELECT COUNT(*) FROM couche_b.units' 2>/dev/null", "9"),
        ])
    else:
        print("⏭️  PostgreSQL checks SKIPPED (SQLite mode)")
        print()
    
    passed = 0
    for name, cmd, expected in checks:
        if check(name, cmd, expected):
            passed += 1
    
    print()
    print("=" * 60)
    print(f"RÉSULTAT: {passed}/{len(checks)} checks passed")
    print("=" * 60)
    
    sys.exit(0 if passed == len(checks) else 1)

if __name__ == "__main__":
    main()
