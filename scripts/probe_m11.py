"""
PROBE PRE-M11 — REGLE-08
Verifie l'etat reel de Railway avant toute ecriture.
Aucun seed ne demarre sans probe exit 0.

Usage local   : DATABASE_URL=<local>   python scripts/probe_m11.py
Usage Railway : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
                python scripts/probe_m11.py
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

db_url = os.environ.get("RAILWAY_DATABASE_URL", "") or os.environ.get(
    "DATABASE_URL", ""
)
if "://" in db_url:
    scheme_part, rest = db_url.split("://", 1)
    db_url = f"{scheme_part.split('+')[0]}://{rest}"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

allow_railway = os.environ.get("DMS_ALLOW_RAILWAY", "0") == "1"

if not db_url:
    sys.exit("STOP — DATABASE_URL absente")
if "railway" in db_url.lower() and not allow_railway:
    sys.exit("STOP — CONTRACT-02 : set DMS_ALLOW_RAILWAY=1 pour Railway")

stops = []

with psycopg.connect(db_url, row_factory=dict_row) as conn:
    cur = conn.cursor()

    print("=" * 64)
    print("PROBE M11 — ETAT AVANT SEEDS")
    print("=" * 64)

    # ── P0 — HEAD ALEMBIC ──────────────────────────────────────────
    cur.execute("SELECT version_num FROM alembic_version")
    r = cur.fetchone()
    head = r["version_num"] if r else "ABSENT"
    print(f"\n[P0] HEAD alembic : {head}")
    if head != "045_agent_native_foundation":
        stops.append(
            f"STOP-P0 — head attendu 045_agent_native_foundation, " f"obtenu '{head}'"
        )

    # ── P1 — DETTE-1 : zones sans severity_level (contextes actifs) ──
    cur.execute("""
        SELECT COUNT(*) AS n
        FROM tracked_market_zones tmz
        LEFT JOIN zone_context_registry zcr
               ON zcr.zone_id = tmz.zone_id
               AND (zcr.valid_until IS NULL OR zcr.valid_until > CURRENT_DATE)
        WHERE zcr.zone_id IS NULL
    """)
    r = cur.fetchone()
    n_missing = r["n"] if r else -1
    print(f"[P1] zones sans severity_level       : {n_missing}")
    print(f"     attendu ~14 — DETTE-1")

    # ── P2 — DETTE-2 : market_surveys ──────────────────────────────
    cur.execute("SELECT COUNT(*) AS n FROM market_surveys")
    r = cur.fetchone()
    n_surveys = r["n"] if r else -1
    print(f"[P2] market_surveys                  : {n_surveys} lignes")

    # ── P3 — DETTE-3 : decision_history ────────────────────────────
    cur.execute("SELECT COUNT(*) AS n FROM decision_history")
    r = cur.fetchone()
    n_dh = r["n"] if r else -1
    print(f"[P3] decision_history                : {n_dh} lignes")

    # ── P4 — DETTE-4 : seasonal_patterns ───────────────────────────
    cur.execute("SELECT COUNT(*) AS n FROM seasonal_patterns")
    r = cur.fetchone()
    n_sp = r["n"] if r else -1
    print(f"[P4] seasonal_patterns               : {n_sp} lignes")
    print(f"     baseline M10B = 1786")

    # ── P5 — DETTE-5 : zone-menaka-1 + corridor ────────────────────
    cur.execute("""
        SELECT COUNT(*) AS n FROM zone_context_registry
        WHERE zone_id = 'zone-menaka-1'
        AND (valid_until IS NULL OR valid_until > CURRENT_DATE)
    """)
    r = cur.fetchone()
    menaka_ctx = r["n"] if r else 0
    print(
        f"[P5] zone-menaka-1 context           : "
        f"{'present' if menaka_ctx else 'absent -> creer'}"
    )

    cur.execute("""
        SELECT COUNT(*) AS n FROM geo_price_corridors
        WHERE zone_from = 'zone-gao-1'
        AND   zone_to   = 'zone-menaka-1'
    """)
    r = cur.fetchone()
    menaka_corr = r["n"] if r else 0
    print(
        f"[P5] corridor Gao->Menaka             : "
        f"{'present' if menaka_corr else 'absent -> creer'}"
    )

    # ── P6 — BASELINE signaux ──────────────────────────────────────
    cur.execute("SELECT COUNT(*) AS n FROM market_signals_v2")
    r = cur.fetchone()
    n_sig = r["n"] if r else 0
    print(f"[P6] market_signals_v2 baseline      : {n_sig}")
    print(f"     attendu >= 578")
    if n_sig < 578:
        stops.append(f"STOP-P6 — baseline signaux degrade : {n_sig} < 578")

    # ── P7 — TABLES CRITIQUES PRESENTES ───────────────────────────
    tables_requises = [
        "tracked_market_zones",
        "zone_context_registry",
        "geo_price_corridors",
        "market_signals_v2",
        "market_surveys",
        "decision_history",
        "seasonal_patterns",
        "mercurials",
        "mercurials_item_map",
    ]
    for tbl in tables_requises:
        cur.execute(
            """
            SELECT table_schema
            FROM information_schema.tables
            WHERE table_name   = %s
            AND   table_type   = 'BASE TABLE'
            """,
            (tbl,),
        )
        r = cur.fetchone()
        status = f"OK ({r['table_schema']})" if r else "ABSENTE — STOP"
        print(f"[P7] {tbl:35} {status}")
        if not r:
            stops.append(f"STOP-P7 — table {tbl} absente")

    # ── P8 — STRUCTURE market_surveys (colonnes requises) ──────────
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name   = 'market_surveys'
        AND   table_schema = 'public'
        ORDER BY ordinal_position
    """)
    cols = cur.fetchall()
    col_names = [c["column_name"] for c in cols]
    print(f"[P8] market_surveys colonnes         : {col_names}")

    # ── P9 — STRUCTURE decision_history (colonnes requises) ────────
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name   = 'decision_history'
        AND   table_schema = 'public'
        ORDER BY ordinal_position
    """)
    cols = cur.fetchall()
    col_names_dh = [c["column_name"] for c in cols]
    print(f"[P9] decision_history colonnes       : {col_names_dh}")

    # ── P10 — signaux en zones sans context actif ────────────────────
    cur.execute("""
        SELECT COUNT(*) AS n
        FROM market_signals_v2 ms
        LEFT JOIN zone_context_registry zcr
               ON zcr.zone_id = ms.zone_id
               AND (zcr.valid_until IS NULL OR zcr.valid_until > CURRENT_DATE)
        WHERE zcr.zone_id IS NULL
    """)
    r = cur.fetchone()
    n_null = r["n"] if r else 0
    print(f"[P10] signals en zones sans severity : {n_null}")
    print(f"      attendu 0 post-seed DETTE-1 (contextes actifs)")

    print("=" * 64)

    if stops:
        print("\nSTOP SIGNALS DETECTES :")
        for s in stops:
            print(f"  - {s}")
        print("\nNE PAS CONTINUER.")
        print("POSTER CET OUTPUT COMPLET. ATTENDRE GO CTO.")
        sys.exit(1)
    else:
        print("\nPROBE OK")
        print(f"  HEAD          : {head}")
        print(f"  Baseline sig  : {n_sig}")
        print(f"  Zones missing : {n_missing}")
        print(f"  Surveys       : {n_surveys}")
        print(f"  Dec. history  : {n_dh}")
        print(f"  Seasonal      : {n_sp}")
        print(f"  Null severity : {n_null}")
        print(f"\nPOSTER CET OUTPUT. STOP. ATTENDRE GO CTO.")
    print("=" * 64)
