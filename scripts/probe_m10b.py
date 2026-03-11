"""
PROBE PRÉ-M10B — RÈGLE-08
Vérifie l'état réel avant toute écriture.

Usage local   : DATABASE_URL=<local>   python scripts/probe_m10b.py
Usage Railway : DATABASE_URL=<railway> DMS_ALLOW_RAILWAY=1 \
                python scripts/probe_m10b.py
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

db_url = (
    os.environ.get("RAILWAY_DATABASE_URL", "")
    or os.environ.get("DATABASE_URL", "")
).replace("postgresql+psycopg://", "postgresql://", 1)
allow_railway = os.environ.get("DMS_ALLOW_RAILWAY", "0") == "1"

if not db_url:
    sys.exit("STOP — DATABASE_URL absente")
if "railway" in db_url.lower() and not allow_railway:
    sys.exit("STOP — CONTRACT-02 : set DMS_ALLOW_RAILWAY=1 pour Railway")

stops = []

with psycopg.connect(db_url, row_factory=dict_row) as conn:
    cur = conn.cursor()

    print("=" * 60)
    print("PROBE M10B - ETAT AVANT MIGRATION")
    print("=" * 60)

    # P0 — HEAD ALEMBIC
    # Valeur à copier EXACTEMENT dans down_revision de la migration 045
    cur.execute("SELECT version_num FROM alembic_version")
    r = cur.fetchone()
    head = r["version_num"] if r else "ABSENT"
    print(f"\n[P0] HEAD (down_revision à copier) : {head}")
    if not r:
        stops.append("STOP-P0 — alembic_version vide")

    # P1 — Tables M10B déjà présentes ?
    # Si head=045 : présent = OK (post-deploy). Si head!=045 : présent = STOP (idempotence)
    p1_present_count = 0
    for tbl in ["agent_checkpoints", "agent_runs_log"]:
        cur.execute(
            """
            SELECT table_schema
            FROM information_schema.tables
            WHERE table_name   = %s
            AND   table_schema = 'couche_a'
            """,
            (tbl,),
        )
        r = cur.fetchone()
        if r:
            p1_present_count += 1
        if head == "045_agent_native_foundation":
            status = "PRESENTE (OK post-deploy)" if r else "ABSENTE - anomalie"
        else:
            status = "DEJA PRESENTE - STOP" if r else "absente -> creer"
        print(f"[P1] couche_a.{tbl:25} {status}")
        if r and head != "045_agent_native_foundation":
            stops.append(f"STOP-P1 - couche_a.{tbl} deja presente")
    if head == "045_agent_native_foundation" and p1_present_count < 2:
        stops.append("STOP-P1 - head=045 mais tables absentes (migration incomplete)")

    # P2 — Tables cibles des triggers (doivent exister)
    for tbl in ["market_signals_v2", "market_surveys"]:
        cur.execute(
            """
            SELECT table_schema
            FROM information_schema.tables
            WHERE table_name = %s
            """,
            (tbl,),
        )
        r = cur.fetchone()
        status = (
            f"PRESENTE (schema={r['table_schema']})"
            if r
            else "ABSENTE - STOP"
        )
        print(f"[P2] {tbl:30} {status}")
        if not r:
            stops.append(f"STOP-P2 - {tbl} absente, trigger impossible")

    # P3 — Schéma couche_a existe ? (045 le crée si absent)
    cur.execute(
        """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name = 'couche_a'
        """
    )
    r = cur.fetchone()
    print(f"[P3] schema couche_a : {'PRESENT' if r else 'absent -> 045 le cree'}")

    # P4 — fn_dms_event_notify déjà présente ?
    cur.execute(
        """
        SELECT proname FROM pg_proc
        WHERE proname = 'fn_dms_event_notify'
        AND pronamespace = (
            SELECT oid FROM pg_namespace WHERE nspname = 'couche_a'
        )
        """
    )
    r = cur.fetchone()
    print(
        f"[P4] fn_dms_event_notify : "
        f"{'DEJA PRESENTE - noter' if r else 'absente -> creer'}"
    )

    # P5 — Migrations 042, 043, 044 présentes dans l'historique ?
    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    current = cur.fetchone()
    current_ver = current["version_num"] if current else ""
    for rev in [
        "042_market_surveys",
        "043_market_signals_v11",
        "044_decision_history",
    ]:
        ok = current_ver == rev if current_ver else False
        print(f"[P5] migration {rev} : {'OK' if ok else 'non-HEAD (normal)'}")

    print("=" * 60)
    if stops:
        print("\nSTOP SIGNALS DETECTES :")
        for s in stops:
            print(f"  - {s}")
        print("\nNE PAS CONTINUER.")
        print("POSTER CET OUTPUT COMPLET. ATTENDRE GO CTO.")
        sys.exit(1)
    else:
        print("\nPROBE OK")
        print("down_revision =", head)
        print("\nPOSTER CET OUTPUT COMPLET. STOP. ATTENDRE GO CTO.")
    print("=" * 60)
