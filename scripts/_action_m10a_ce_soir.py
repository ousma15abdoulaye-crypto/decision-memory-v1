#!/usr/bin/env python3
"""
ACTION IMMÉDIATE M10A — 3 commandes sur Railway.
1. Propager mercurials_item_map -> mercurials.item_id
2. Lancer compute_market_signals (si existe)
3. Vérifier signaux
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

db_url = os.environ.get("RAILWAY_DATABASE_URL", "")
if not db_url:
    print("ERROR: RAILWAY_DATABASE_URL absente")
    sys.exit(1)
db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

import psycopg


def main():
    print("=" * 60)
    print("ACTION M10A — 3 COMMANDES RAILWAY")
    print("=" * 60)
    print(f"DB: {db_url.split('@')[-1][:50] if '@' in db_url else '...'}\n")

    with psycopg.connect(db_url, autocommit=True) as conn:
        cur = conn.cursor()

        # --- 1. Propager le mapping ---
        print("--- COMMANDE 1 : Propager mapping mercurials_item_map -> mercurials.item_id ---")
        # mercurials_item_map a dict_item_id (pas item_id)
        cur.execute("""
            UPDATE mercurials m
            SET item_id = mim.dict_item_id::text
            FROM mercurials_item_map mim
            WHERE LOWER(TRIM(m.item_canonical)) = LOWER(TRIM(mim.item_canonical))
              AND m.item_id IS NULL
        """)
        updated = cur.rowcount
        print(f"Rows updated: {updated}")

        # Vérifier couverture
        cur.execute("""
            SELECT COUNT(*)        AS total,
                   COUNT(item_id)  AS mappes,
                   ROUND(COUNT(item_id)::numeric / NULLIF(COUNT(*)::numeric, 0) * 100, 1) AS couverture_pct
            FROM mercurials
        """)
        r = cur.fetchone()
        print(f"\nCouverture mercurials après UPDATE:")
        print(f"  total={r[0]}  mappes={r[1]}  couverture_pct={r[2]}%")

        # --- 3. Vérifier signaux (avant compute) ---
        print("\n--- COMMANDE 3 : Signaux par zone x qualité (avant compute) ---")
        cur.execute("""
            SELECT
                zcr.severity_level,
                sig.signal_quality,
                sig.alert_level,
                COUNT(*)                       AS n,
                ROUND(AVG(sig.residual_pct)::numeric, 1) AS residuel_moyen,
                ROUND(AVG(sig.price_avg)::numeric, 0)  AS prix_moyen
            FROM market_signals_v2 sig
            LEFT JOIN zone_context_registry zcr
              ON zcr.zone_id     = sig.zone_id
             AND zcr.valid_until IS NULL
            GROUP BY
                zcr.severity_level,
                sig.signal_quality,
                sig.alert_level
            ORDER BY
                zcr.severity_level,
                sig.alert_level
        """)
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
        print(" | ".join(cols))
        print("-" * 60)
        for row in rows:
            print(" | ".join(str(x) for x in row))
        if not rows:
            print("(0 rows — table vide, compute non lancé)")

    # --- 2. Lancer compute ---
    print("\n--- COMMANDE 2 : compute_market_signals.py ---")
    script = ROOT / "scripts" / "compute_market_signals.py"
    if script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(ROOT),
                env={**os.environ, "DATABASE_URL": db_url},
                capture_output=True,
                text=True,
                timeout=300,
            )
            out = result.stdout + result.stderr
            print(out[-2000:] if len(out) > 2000 else out)
            print(f"\nExit code: {result.returncode}")
        except Exception as e:
            print(f"ERREUR: {e}")
    else:
        print(f"SCRIPT ABSENT: {script}")
        print("(compute_market_signals.py — à récupérer via merge M9)")

    # Re-vérifier signaux après compute
    print("\n--- COMMANDE 3 (après compute) : Signaux ---")
    with psycopg.connect(db_url, autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                zcr.severity_level,
                sig.signal_quality,
                sig.alert_level,
                COUNT(*)                       AS n,
                ROUND(AVG(sig.residual_pct)::numeric, 1) AS residuel_moyen,
                ROUND(AVG(sig.price_avg)::numeric, 0)  AS prix_moyen
            FROM market_signals_v2 sig
            LEFT JOIN zone_context_registry zcr
              ON zcr.zone_id     = sig.zone_id
             AND zcr.valid_until IS NULL
            GROUP BY
                zcr.severity_level,
                sig.signal_quality,
                sig.alert_level
            ORDER BY
                zcr.severity_level,
                sig.alert_level
        """)
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
        print(" | ".join(cols))
        print("-" * 60)
        for row in rows:
            print(" | ".join(str(x) for x in row))
        if not rows:
            print("(0 rows)")

    print("\n" + "=" * 60)
    print("FIN ACTION M10A")


if __name__ == "__main__":
    main()
