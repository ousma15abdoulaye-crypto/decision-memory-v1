#!/usr/bin/env python3
"""
Seed geo_price_corridors Mali.
Donnees terrain + FEWS NET 2026. Une ligne = un sens.

Usage : python scripts/seed_geo_corridors_mali.py
"""

import os
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

CORRIDORS = [
    {
        "from": "Bamako",
        "to": "Mopti",
        "markup": 1.12,
        "rel": 0.90,
        "route": "paved",
        "crisis": 1.05,
    },
    {
        "from": "Bamako",
        "to": "Gao",
        "markup": 1.32,
        "rel": 0.55,
        "route": "paved",
        "crisis": 1.18,
    },
    {
        "from": "Mopti",
        "to": "Tombouctou",
        "markup": 1.35,
        "rel": 0.65,
        "route": "unpaved",
        "crisis": 1.20,
    },
    {
        "from": "Mopti",
        "to": "Gao",
        "markup": 1.28,
        "rel": 0.60,
        "route": "paved",
        "crisis": 1.15,
    },
    {
        "from": "Gao",
        "to": "Menaka",
        "markup": 1.40,
        "rel": 0.40,
        "route": "unpaved",
        "crisis": 1.25,
    },
    {
        "from": "Gao",
        "to": "Kidal",
        "markup": 1.65,
        "rel": 0.25,
        "route": "air_only",
        "crisis": 1.35,
    },
    {
        "from": "Tombouctou",
        "to": "Gao",
        "markup": 1.20,
        "rel": 0.50,
        "route": "unpaved",
        "crisis": 1.15,
    },
]


def env() -> str:
    u = os.environ.get("DATABASE_URL", "")
    if not u:
        raise SystemExit("DATABASE_URL absent")
    return u.replace("postgresql+psycopg://", "postgresql://")


def main():
    conn = psycopg.connect(env(), row_factory=dict_row)
    cur = conn.cursor()
    ok = skip = err = 0

    for c in CORRIDORS:
        cur.execute(
            "SELECT id FROM public.geo_master WHERE LOWER(name) = LOWER(%s) LIMIT 1",
            (c["from"],),
        )
        zf = cur.fetchone()
        cur.execute(
            "SELECT id FROM public.geo_master WHERE LOWER(name) = LOWER(%s) LIMIT 1",
            (c["to"],),
        )
        zt = cur.fetchone()

        if not zf or not zt:
            print(f"SKIP {c['from']} -> {c['to']}")
            skip += 1
            continue

        try:
            cur.execute(
                """
                INSERT INTO public.geo_price_corridors (
                    zone_from, zone_to,
                    transport_markup, reliability,
                    route_type, crisis_multiplier,
                    last_verified
                ) VALUES (%s,%s,%s,%s,%s,%s,CURRENT_DATE)
                ON CONFLICT (zone_from, zone_to) DO UPDATE SET
                    transport_markup  = EXCLUDED.transport_markup,
                    reliability       = EXCLUDED.reliability,
                    crisis_multiplier = EXCLUDED.crisis_multiplier,
                    last_verified     = CURRENT_DATE
                """,
                (zf["id"], zt["id"], c["markup"], c["rel"], c["route"], c["crisis"]),
            )
            print(f"OK {c['from']:12} -> {c['to']:12} x{c['markup']} {c['route']}")
            ok += 1
        except Exception as e:
            print(f"ERR {c['from']} -> {c['to']}: {e}")
            err += 1

    conn.commit()
    print(f"\nCorridors: ok={ok} skip={skip} err={err}")
    conn.close()
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
