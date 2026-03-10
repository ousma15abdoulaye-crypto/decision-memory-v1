#!/usr/bin/env python3
"""
CB-01 SEMANTIC_GUARD V1 — M8
Usage : python scripts/semantic_guard_m8.py
"""

import re
import subprocess
import sys
from pathlib import Path

TARGETS = [
    "alembic/versions/042_market_surveys.py",
    "scripts/seed_zone_context_mali.py",
    "scripts/seed_tracked_market_scope.py",
    "scripts/triage_collisions_m8.py",
    "tests/test_m8_invariants.py",
]

# Patterns interdits — pas de DOTALL (chaque pattern ne traverse pas les lignes)
FORBIDDEN = [
    (r"op\.get_bind\(", "op.get_bind() interdit"),
    (r"\bautogenerate\b", "autogenerate interdit"),
    (r"\bmarket_signals\b", "market_signals hors scope M8"),
    (r"\bformula_version\b", "formula_version hors scope M8"),
    (r"\bcompute_signal\b", "compute_signal hors scope M8"),
    (r"VIEW\s+vendor_price_positioning", "vendor_price_positioning hors scope M8"),
    (r"VIEW\s+basket_cost_by_zone", "basket_cost_by_zone hors scope M8"),
    (r"VIEW\s+price_series", "price_series hors scope M8"),
    (r"CROSS\s+JOIN.*geo_master", "CROSS JOIN global interdit"),
    (r"collection_method.*['\"]mercuriale['\"]", "mercuriale interdit"),
    # Refresh dans un trigger — pattern restreint à la même ligne
    (r"EXECUTE\s+FUNCTION.*REFRESH", "refresh dans trigger interdit"),
    (r"\bFN_REJECT_MUTATION_NAME\b", "placeholder non résolu"),
    (r"\bis_bidirectional\b", "is_bidirectional absent du schéma M8"),
    (r"humanitarian_reference", "utiliser humanitarian_nfi"),
    # org_id dans market_baskets — uniquement dans CREATE TABLE/ALTER TABLE
    (
        r"org_id\s+\w.*market_baskets|market_baskets.*org_id\s+\w",
        "market_baskets GLOBAL_CORE — pas d'org_id",
    ),
    # railway : seulement si c'est une vraie URL (pas une ligne de garde)
    (r"['\"].*railway.*['\"](?!.*\.lower\(\))", "railway interdit dans URL"),
]

# Patterns exemptés dans les fichiers de test
# (les tests vérifient l'absence de ces éléments — mentions légitimes)
EXEMPT_IN_TESTS = {
    r"\bmarket_signals\b",
    r"\bis_bidirectional\b",
    r"humanitarian_reference",
    r"collection_method.*['\"]mercuriale['\"]",
    r"org_id\s+\w.*market_baskets|market_baskets.*org_id\s+\w",
    r"['\"].*railway.*['\"](?!.*\.lower\(\))",
}

MIGRATION_REQUIRED = [
    (r"down_revision\s*=\s*['\"]m7_7_genome_stable['\"]", "down_revision manquant"),
    (r"def downgrade", "downgrade() absent"),
    (r"def upgrade", "upgrade() absent"),
    (r"-- CLASSIFICATION\s*:", "CLASSIFICATION manquante"),
    (r"FAIL-LOUD", "bloc fail-loud manquant"),
]


def check_no_existing_migration_modified() -> list:
    """
    Vérifie que 042_market_surveys.py est le seul fichier alembic/versions/
    ajouté ou modifié dans les commits M8 (comparaison avec main).
    """
    # Cherche la base de la branche M8 par rapport à main
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
    else:
        # Fallback : fichiers stagés uniquement
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
        )
    return [
        f"MIGRATION EXISTANTE MODIFIÉE : {f}"
        for f in r.stdout.strip().splitlines()
        if "alembic/versions/" in f and "042_market_surveys" not in f
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
        # Scan ligne par ligne — pas de DOTALL
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pat, line, re.IGNORECASE):
                errs.append(f"  L{lineno} : {msg}")
    if "042_market_surveys" in str(path):
        for pat, msg in MIGRATION_REQUIRED:
            if not re.search(pat, text, re.IGNORECASE):
                errs.append(f"  MANQUANT : {msg}")
    return errs


def main():
    print("=" * 55)
    print("CB-01 SEMANTIC_GUARD V1 — M8")
    print("=" * 55)
    total = 0
    for e in check_no_existing_migration_modified():
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
        print(f"GUARD FAIL — {total} violation(s)")
        sys.exit(1)
    print("GUARD PASS OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
