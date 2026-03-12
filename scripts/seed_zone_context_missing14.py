"""
SEED — DETTE-1 M11
Mappe les 14 zones tracked sans severity_level
vers zone_context_registry.

Mapping FEWS Mali — Sources :
  FEWS NET Mali Food Security Outlook 2024-2025
  Rapport IPC Mali Octobre 2024
  Geographie et acces humanitaire OCHA Mali

Regle rollback : conn.rollback() sur tout except.
Regle idempotence : skip si zone deja presente.

Schema reel : valid_from, valid_until, source, access_difficulty obligatoires.
Pas de fews_context_code — code FEWS dans notes.

Usage : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
        python scripts/seed_zone_context_missing14.py
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

# (zone_id, context_type, severity_level, structural_markup_pct, access_difficulty, fews_code)
ZONE_CONTEXTS = [
    ("zone-bougouni-1", "normal", "ipc_1_minimal", 0.0, "open", "ML-1"),
    ("zone-koutiala-1", "normal", "ipc_1_minimal", 0.0, "open", "ML-1"),
    ("zone-sikasso-1", "normal", "ipc_1_minimal", 0.0, "open", "ML-1"),
    ("zone-dioila-1", "seasonal_lean", "ipc_2_stressed", 8.0, "open", "ML-7"),
    ("zone-koulikoro-1", "seasonal_lean", "ipc_2_stressed", 8.0, "open", "ML-7"),
    ("zone-kita-1", "seasonal_lean", "ipc_2_stressed", 8.0, "open", "ML-7"),
    ("zone-segou-1", "seasonal_lean", "ipc_2_stressed", 8.0, "open", "ML-7"),
    ("zone-san-1", "seasonal_lean", "ipc_2_stressed", 8.0, "open", "ML-7"),
    ("zone-nioro-1", "seasonal_lean", "ipc_2_stressed", 8.0, "open", "ML-7"),
    ("zone-mopti-1", "security_crisis", "ipc_3_crisis", 18.0, "restricted", "ML-2"),
    ("zone-bandiagara-1", "security_crisis", "ipc_3_crisis", 18.0, "restricted", "ML-2"),
    ("zone-nara-1", "security_crisis", "ipc_3_crisis", 18.0, "restricted", "ML-2"),
    ("zone-douentza-1", "security_crisis", "ipc_3_crisis", 25.0, "restricted", "ML-8"),
    ("zone-taoudeni-1", "security_crisis", "ipc_4_emergency", 32.0, "very_restricted", "ML-9"),
]

VALID_FROM = date(2026, 1, 1)
SOURCE = "FEWS NET Mali M11 DETTE-1"


def main():
    db_url = (
        os.environ.get("RAILWAY_DATABASE_URL", "")
        or os.environ.get("DATABASE_URL", "")
    )
    if not db_url:
        sys.exit("STOP — DATABASE_URL absente")
    if "railway" in db_url.lower() and os.environ.get("DMS_ALLOW_RAILWAY", "0") != "1":
        sys.exit("STOP — CONTRACT-02")
    url = db_url.replace("postgresql+psycopg://", "postgresql://")

    ok = skip = err = 0

    with psycopg.connect(url, row_factory=dict_row) as conn:
        cur = conn.cursor()
        for zone_id, ctx_type, severity, markup_pct, access, fews_code in ZONE_CONTEXTS:
            cur.execute(
                "SELECT 1 FROM tracked_market_zones WHERE zone_id = %s",
                (zone_id,),
            )
            if not cur.fetchone():
                print(f"SKIP {zone_id:28} — absent tracked_market_zones")
                skip += 1
                continue

            cur.execute(
                "SELECT 1 FROM zone_context_registry WHERE zone_id = %s AND valid_until IS NULL",
                (zone_id,),
            )
            if cur.fetchone():
                print(f"SKIP {zone_id:28} — deja dans zone_context_registry")
                skip += 1
                continue

            notes = f"FEWS {fews_code}"
            try:
                cur.execute(
                    """
                    INSERT INTO zone_context_registry
                        (zone_id, context_type, severity_level,
                         structural_markup_pct, access_difficulty,
                         valid_from, valid_until, source, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s)
                    """,
                    (zone_id, ctx_type, severity, markup_pct, access, VALID_FROM, SOURCE, notes),
                )
                conn.commit()
                print(f"OK   {zone_id:28} {severity:20} +{markup_pct:5.1f}%  [{fews_code}]")
                ok += 1
            except Exception as e:
                conn.rollback()
                print(f"ERR  {zone_id} — {e}")
                err += 1

    print(f"\nRESULTAT ok={ok} skip={skip} err={err}")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
