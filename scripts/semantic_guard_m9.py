#!/usr/bin/env python3
"""
CB-01 SEMANTIC_GUARD V2 -- M9
Usage : python scripts/semantic_guard_m9.py
"""

import re
import subprocess
import sys
from pathlib import Path

TARGETS = [
    "alembic/versions/043_market_signals_v11.py",
    "src/couche_a/market/formula_v11.py",
    "src/couche_a/market/signal_engine.py",
    "scripts/compute_market_signals.py",
    "scripts/seed_seasonal_patterns_mali.py",
    "scripts/seed_instat_seasonal_patterns.py",
    "scripts/seed_geo_corridors_mali.py",
    "tests/test_m9_invariants.py",
]

FORBIDDEN = [
    (r"op\.get_bind\(", "op.get_bind() interdit"),
    (r"\bautogenerate\b", "autogenerate interdit"),
    (r"WEIGHTS.*['\"]instat", "INSTAT interdit dans WEIGHTS"),
    (r"instat.*price_raw", "INSTAT ne peut pas alimenter price_raw"),
    (r"CROSS\s+JOIN.*geo_master", "CROSS JOIN global interdit"),
    (r"\bitem_uid\b.*procurement_dict", "item_uid interdit -- utiliser item_id"),
    (
        r"CREATE\s+TABLE.*\bmarket_signals\b(?!_v2)",
        "CREATE TABLE market_signals interdit",
    ),
]

MIGRATION_REQUIRED = [
    (r"down_revision\s*=\s*['\"]042_market_surveys", "down_revision manquant"),
    (r"def downgrade", "downgrade() absent"),
    (r"def upgrade", "upgrade() absent"),
    (r"FAIL-LOUD", "fail-loud manquant"),
    (r"IF NOT EXISTS", "IF NOT EXISTS manquant"),
    (r"DROP TRIGGER IF EXISTS", "DROP TRIGGER IF EXISTS manquant"),
    (r"market_signals_v2", "market_signals_v2 non referencee"),
]

FORMULA_REQUIRED = [
    (r"FORMULA_VERSION\s*[=:]\s*['\"]1\.1", "FORMULA_VERSION = '1.1' manquant"),
    (r"WEIGHTS\b", "WEIGHTS manquant"),
    (r"FRESHNESS\b", "FRESHNESS manquant"),
    (r"IQR_MULTIPLIER\s*=\s*2\.5", "IQR_MULTIPLIER = 2.5 manquant"),
]

EXEMPT_IN_TESTS = {
    r"CREATE\s+TABLE.*\bmarket_signals\b(?!_v2)",
    r"\bitem_uid\b.*procurement_dict",
}


def check_existing_migrations() -> list:
    r = subprocess.run(
        ["git", "diff", "HEAD", "--name-only"],
        capture_output=True,
        text=True,
    )
    base = subprocess.run(
        ["git", "merge-base", "HEAD", "main"],
        capture_output=True,
        text=True,
    )
    base_sha = base.stdout.strip() if base.returncode == 0 else None
    if base_sha:
        r = subprocess.run(
            ["git", "diff", base_sha, "HEAD", "--name-only"],
            capture_output=True,
            text=True,
        )
    return [
        f"MIGRATION EXISTANTE MODIFIEE : {f}"
        for f in r.stdout.strip().splitlines()
        if "alembic/versions/" in f and "043_market_signals_v11" not in f
    ]


def scan(path: Path) -> list:
    if not path.exists():
        return [f"ABSENT : {path}"]
    text = path.read_text(encoding="utf-8")
    errs = []
    is_test = path.name.startswith("test_")
    for pat, msg in FORBIDDEN:
        if is_test and pat in EXEMPT_IN_TESTS:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pat, line, re.IGNORECASE):
                errs.append(f"  L{lineno} : {msg}")
    if "043_market_signals" in str(path):
        for pat, msg in MIGRATION_REQUIRED:
            if not re.search(pat, text, re.IGNORECASE):
                errs.append(f"  MANQUANT : {msg}")
    if "formula_v11" in str(path):
        for pat, msg in FORMULA_REQUIRED:
            if not re.search(pat, text, re.IGNORECASE):
                errs.append(f"  MANQUANT : {msg}")
    return errs


def main():
    print("=" * 55)
    print("CB-01 SEMANTIC_GUARD V2 -- M9")
    print("=" * 55)
    total = 0
    for e in check_existing_migrations():
        print(e)
        total += 1
    for f in TARGETS:
        errs = scan(Path(f))
        if errs:
            print(f"\n{f}")
            for e in errs:
                print(e)
            total += len(errs)
        else:
            print(f"  OK : {f}")
    print(f"\n{'='*55}")
    if total:
        print(f"GUARD FAIL -- {total} violation(s)")
        sys.exit(1)
    print("GUARD PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
