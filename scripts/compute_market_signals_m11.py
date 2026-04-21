"""
COMPUTE M11 — Recompute complet post-seeds DETTE-1 a DETTE-5.

Preconditions :
  - 14 zones mappees (DETTE-1)          ETAPE 1
  - zone-menaka-1 + corridor (DETTE-5)  ETAPE 2
  - seasonal_patterns completes (DETTE-4) ETAPE 3
  - market_surveys initialises (DETTE-2) ETAPE 5
  - decision_history initialise (DETTE-3) ETAPE 6

Attendu post-compute :
  severity_level NULL = 0 (signaux en zones sans context)
  market_signals_v2 > 578
  CRITICAL/WATCH sur zones ipc_3_crisis / ipc_4_emergency

Usage : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
        python scripts/compute_market_signals_m11.py
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

BASELINE_M10B = 578

db_url = os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get(
    "DATABASE_URL", ""
)
if not db_url:
    sys.exit("STOP — DATABASE_URL absente")
if "railway" in db_url.lower() and os.environ.get("DMS_ALLOW_RAILWAY", "0") != "1":
    sys.exit("STOP — CONTRACT-02")

url = db_url.replace("postgresql+psycopg://", "postgresql://")
env = {**os.environ, "DATABASE_URL": url, "DMS_ALLOW_RAILWAY": "1"}

print("=" * 64)
print("COMPUTE M11 — RECOMPUTE POST-SEEDS")
print("=" * 64)

result = subprocess.run(
    [sys.executable, "scripts/compute_market_signals.py"],
    env=env,
    cwd=Path(__file__).resolve().parents[1],
)
if result.returncode != 0:
    print(f"ERR — compute_market_signals.py exit {result.returncode}")
    sys.exit(result.returncode)

with psycopg.connect(url, row_factory=dict_row) as conn:
    cur = conn.cursor()

    cur.execute("""
        SELECT
            signal_quality,
            alert_level,
            COUNT(*) AS n,
            ROUND(AVG(residual_pct), 2) AS residuel_moyen,
            ROUND(AVG(price_avg)) AS prix_moyen
        FROM market_signals_v2
        GROUP BY signal_quality, alert_level
        ORDER BY signal_quality, alert_level
    """)
    rows = cur.fetchall()

    print(f"\n{'quality':12} {'alert':20} {'n':>5} {'resid':>6} {'prix_moy':>10}")
    print("-" * 60)
    total = 0
    for r in rows:
        print(
            f"{str(r['signal_quality']):12} "
            f"{str(r['alert_level']):20} "
            f"{r['n']:>5} "
            f"{str(r['residuel_moyen']):>6} "
            f"{str(r['prix_moyen']):>10}"
        )
        total += r["n"]
    print(f"\nTOTAL : {total} signaux")

    cur.execute("""
        SELECT COUNT(*) AS n
        FROM market_signals_v2 ms
        LEFT JOIN zone_context_registry zcr ON zcr.zone_id = ms.zone_id AND zcr.valid_until IS NULL
        WHERE zcr.zone_id IS NULL
    """)
    n_null = cur.fetchone()["n"]
    print(f"\nSignaux en zones sans severity : {n_null}")
    if n_null > 0:
        cur.execute("""
            SELECT DISTINCT ms.zone_id
            FROM market_signals_v2 ms
            LEFT JOIN zone_context_registry zcr ON zcr.zone_id = ms.zone_id AND zcr.valid_until IS NULL
            WHERE zcr.zone_id IS NULL
        """)
        zones = [r["zone_id"] for r in cur.fetchall()]
        print(f"  Zones non mappees : {zones}")
        print("  WARNING — signaux en zones sans context subsistent")
    else:
        print("  OK — toutes zones mappees")

    delta = total - BASELINE_M10B
    print(f"\nBaseline M10B : {BASELINE_M10B}")
    print(f"Post-M11      : {total}")
    print(f"Delta         : {'+' if delta >= 0 else ''}{delta}")

    if total < BASELINE_M10B:
        print("STOP-COMPUTE — signaux < baseline M10B")
        sys.exit(1)

    print("\nCOMPUTE M11 OK")
    print("=" * 64)
