#!/usr/bin/env python3
"""
Probe M10A — Périmètre exact avant mandat.
Exécute les 6 vérifications demandées et affiche les résultats en détail.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Charger .env
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    print("ERROR: DATABASE_URL absente")
    sys.exit(1)
db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

import psycopg

QUERIES = [
    ("1. État mercurials après mapping", """
SELECT COUNT(*) AS total,
       COUNT(item_id) AS avec_item_id,
       ROUND(COUNT(item_id)::numeric / NULLIF(COUNT(*)::numeric, 0) * 100, 1) AS couverture_pct
FROM mercurials;
"""),
    ("2. État market_signals_v2", """
SELECT signal_quality, COUNT(*) AS n
FROM market_signals_v2
GROUP BY signal_quality;
"""),
    ("3. État seasonal_patterns", """
SELECT computation_version, COUNT(*) AS n
FROM seasonal_patterns
GROUP BY computation_version;
"""),
    ("4. collision_log par résolution", """
SELECT resolution, COUNT(*) AS n
FROM dict_collision_log
GROUP BY resolution;
"""),
    ("5a. tracked_market_items count", "SELECT COUNT(*) AS n FROM tracked_market_items;"),
    ("5b. tracked_market_zones count", "SELECT COUNT(*) AS n FROM tracked_market_zones;"),
]


def run_query(conn, title: str, sql: str):
    print(f"\n{'='*60}")
    print(f"# {title}")
    print("=" * 60)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d.name for d in cur.description] if cur.description else []
            if cols:
                print(" | ".join(cols))
                print("-" * 50)
            for r in rows:
                print(" | ".join(str(x) for x in r))
            if not rows:
                print("(0 rows)")
    except Exception as e:
        print(f"ERREUR: {e}")


def main():
    print("\n" + "=" * 60)
    print("PROBE M10A — PÉRIMÈTRE EXACT AVANT MANDAT")
    print("=" * 60)
    print(f"DB: {db_url.split('@')[-1] if '@' in db_url else '...'}")

    with psycopg.connect(db_url, autocommit=True) as conn:
        for title, sql in QUERIES:
            run_query(conn, title, sql)

    # 6. compute_market_signals --dry-run
    print("\n" + "=" * 60)
    print("# 6. Vérifier que compute tourne")
    print("=" * 60)
    script = ROOT / "scripts" / "compute_market_signals.py"
    if script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--dry-run"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = result.stdout + result.stderr
            lines = out.strip().split("\n")
            tail = lines[-20:] if len(lines) >= 20 else lines
            for line in tail:
                print(line)
            if result.returncode != 0:
                print(f"\n[Exit code: {result.returncode}]")
        except Exception as e:
            print(f"ERREUR: {e}")
    else:
        print(f"SCRIPT ABSENT: {script}")
        print("(compute_market_signals.py non présent sur main — peut être sur feat/m9)")

    print("\n" + "=" * 60)
    print("FIN PROBE M10A")
    print("=" * 60)


if __name__ == "__main__":
    main()
