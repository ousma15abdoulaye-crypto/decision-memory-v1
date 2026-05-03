"""
SEED — DETTE-5 M11
Ajoute zone-menaka-1 dans zone_context_registry (si absent)
et le corridor Gao -> Menaka dans geo_price_corridors.

Menaka : zone IPC-4 emergency (ML-9) — conflit severe,
         acces humanitaire tres contraint.
Corridor Gao -> Menaka : piste degradee, insecurite,
                         cout transport x1.45 vs Gao.

Schema reel : zone_from, zone_to, transport_markup, route_type.

Usage : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
        python scripts/seed_menaka_corridor.py
"""

import os
import sys
from datetime import date
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row


def main():
    db_url = os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get(
        "DATABASE_URL", ""
    )
    if not db_url:
        sys.exit("STOP — DATABASE_URL absente")
    if "railway" in db_url.lower() and os.environ.get("DMS_ALLOW_RAILWAY", "0") != "1":
        sys.exit("STOP — CONTRACT-02")
    url = db_url.replace("postgresql+psycopg://", "postgresql://")

    ok = skip = err = 0

    with psycopg.connect(url, row_factory=dict_row) as conn:
        cur = conn.cursor()

        # 1. zone_context_registry — Menaka (si absent)
        cur.execute(
            "SELECT 1 FROM zone_context_registry WHERE zone_id = 'zone-menaka-1' AND valid_until IS NULL"
        )
        if cur.fetchone():
            print("SKIP zone-menaka-1 context — deja present")
            skip += 1
        else:
            try:
                cur.execute(
                    """
                    INSERT INTO zone_context_registry
                        (zone_id, context_type, severity_level,
                         structural_markup_pct, access_difficulty,
                         valid_from, valid_until, source, notes)
                    VALUES (
                        'zone-menaka-1',
                        'security_crisis',
                        'ipc_4_emergency',
                        32.0,
                        'very_restricted',
                        %s, NULL, 'FEWS NET Mali M11 DETTE-5', 'ML-9'
                    )
                    """,
                    (date(2026, 1, 1),),
                )
                conn.commit()
                print("OK   zone-menaka-1 -> ipc_4_emergency +32.0% [ML-9]")
                ok += 1
            except Exception as e:
                conn.rollback()
                print(f"ERR  zone-menaka-1 context — {e}")
                err += 1

        # 2. geo_price_corridors — Gao -> Menaka
        cur.execute("""
            SELECT 1 FROM geo_price_corridors
            WHERE zone_from = 'zone-gao-1'
            AND   zone_to   = 'zone-menaka-1'
            """)
        if cur.fetchone():
            print("SKIP corridor Gao->Menaka — deja present")
            skip += 1
        else:
            try:
                cur.execute("""
                    INSERT INTO geo_price_corridors
                        (zone_from, zone_to, transport_markup, route_type,
                         reliability, crisis_multiplier, last_verified)
                    VALUES (
                        'zone-gao-1',
                        'zone-menaka-1',
                        1.45,
                        'unpaved',
                        0.40,
                        1.25,
                        CURRENT_DATE
                    )
                    """)
                conn.commit()
                print("OK   corridor Gao->Menaka x1.45 unpaved")
                ok += 1
            except Exception as e:
                conn.rollback()
                print(f"ERR  corridor Gao->Menaka — {e}")
                err += 1

    print(f"\nRESULTAT ok={ok} skip={skip} err={err}")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
