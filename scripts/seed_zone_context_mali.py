#!/usr/bin/env python3
"""
Seed zone_context_registry — FEWS NET Mali mars 2026.
S'applique à TOUS les secteurs : ONG/État/Mines/Privé.
Usage : python scripts/seed_zone_context_mali.py

Adaptation schéma réel : geo_master n'a pas de colonne code.
Mapping FEWS (ML-X) → geo_master par name.
"""

import os
import sys
from datetime import date

try:
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

# FEWS code → geo_master.name (schéma réel sans colonne code)
ZONE_MAP = {
    "ML-1": "Bamako",
    "ML-2": "Gao",
    "ML-6": "Kidal",
    "ML-7": "Mopti",
    "ML-8": "Tombouctou",
    "ML-9": "Ménaka",
}

CONTEXTS = [
    {
        "code": "ML-1",
        "type": "normal",
        "sev": "ipc_1_minimal",
        "markup": 0.0,
        "access": "open",
        "from": date(2026, 1, 1),
        "until": None,
        "src": "FEWS NET Mali Feb 2026",
        "url": "https://fews.net/west-africa/mali",
        "notes": "Bamako — référence prix. Marché ouvert.",
    },
    {
        "code": "ML-7",
        "type": "seasonal_lean",
        "sev": "ipc_2_stressed",
        "markup": 8.0,
        "access": "open",
        "from": date(2026, 2, 1),
        "until": date(2026, 6, 30),
        "src": "FEWS NET Mali Feb 2026",
        "url": "https://fews.net/west-africa/mali",
        "notes": "Mopti pré-soudure +8%. Tous secteurs.",
    },
    {
        "code": "ML-8",
        "type": "security_crisis",
        "sev": "ipc_3_crisis",
        "markup": 25.0,
        "access": "restricted",
        "from": date(2026, 1, 1),
        "until": None,
        "src": "FEWS NET Mali Feb 2026",
        "url": "https://fews.net/west-africa/mali",
        "notes": "Tombouctou nord +25%. Axe Goundam restreint. Tous secteurs.",
    },
    {
        "code": "ML-2",
        "type": "security_crisis",
        "sev": "ipc_3_crisis",
        "markup": 18.0,
        "access": "restricted",
        "from": date(2026, 1, 1),
        "until": None,
        "src": "FEWS NET Mali Feb 2026",
        "url": "https://fews.net/west-africa/mali",
        "notes": "Gao IPC2-3 +18%. Carburant et matériaux impactés.",
    },
    {
        "code": "ML-9",
        "type": "security_crisis",
        "sev": "ipc_4_emergency",
        "markup": 32.0,
        "access": "very_restricted",
        "from": date(2026, 1, 1),
        "until": None,
        "src": "FEWS NET Mali + terrain mars 2026",
        "url": "https://fews.net/west-africa/mali",
        "notes": "Ménaka IPC4→IPC5 probable avril. Rançons 120k FCFA/camion. +32% ONG/État/Mines.",
    },
    {
        "code": "ML-6",
        "type": "security_crisis",
        "sev": "ipc_4_emergency",
        "markup": 50.0,
        "access": "very_restricted",
        "from": date(2026, 1, 1),
        "until": None,
        "src": "FEWS NET Mali Feb 2026",
        "url": "https://fews.net/west-africa/mali",
        "notes": "Kidal IPC4. Routes air_only. +50% vs Bamako tous secteurs.",
    },
]


def main():
    db = os.environ.get("DATABASE_URL", "")
    if not db:
        raise SystemExit("DATABASE_URL absente")
    if "railway" in db.lower():
        raise SystemExit("CONTRACT-02")
    url = db.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(url, row_factory=dict_row)
    cur = conn.cursor()
    ok = skip = err = 0
    for c in CONTEXTS:
        name = ZONE_MAP.get(c["code"])
        if not name:
            print(f"STOP : {c['code']} absent du mapping")
            conn.close()
            sys.exit(1)
        cur.execute(
            "SELECT id FROM public.geo_master WHERE name = %s LIMIT 1",
            (name,),
        )
        z = cur.fetchone()
        if not z:
            print(f"STOP : {name} absent geo_master")
            conn.close()
            sys.exit(1)
        zid = z["id"]
        if c["until"] is None:
            cur.execute(
                """
                SELECT id FROM public.zone_context_registry
                WHERE zone_id = %s AND valid_until IS NULL
                LIMIT 1
            """,
                (zid,),
            )
            if cur.fetchone():
                print(f"  SKIP {c['code']} : actif existant")
                skip += 1
                continue
        try:
            cur.execute(
                """
                INSERT INTO public.zone_context_registry (
                    zone_id, context_type, severity_level,
                    structural_markup_pct, access_difficulty,
                    valid_from, valid_until,
                    source, source_url, notes
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
                (
                    zid,
                    c["type"],
                    c["sev"],
                    c["markup"],
                    c["access"],
                    c["from"],
                    c["until"],
                    c["src"],
                    c["url"],
                    c["notes"],
                ),
            )
            print(f"  OK {c['code']} {c['type']} {c['sev']} +{c['markup']}%")
            ok += 1
        except Exception as e:
            print(f"  ERR {c['code']} : {e}")
            err += 1
    conn.commit()
    print(f"\nRÉSULTAT ok={ok} skip={skip} err={err}")
    conn.close()
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
