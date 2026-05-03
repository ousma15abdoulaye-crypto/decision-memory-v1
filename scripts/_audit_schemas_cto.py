"""
Audit schémas — CTO décision M10B.
Exécute les 3 requêtes sur la DB pointée par DATABASE_URL.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

import psycopg

db_url = os.environ.get("DATABASE_URL", "") or os.environ.get(
    "RAILWAY_DATABASE_URL", ""
)
if not db_url:
    print("STOP - DATABASE_URL absente")
    sys.exit(1)

# Normaliser pour psycopg
if "://" in db_url:
    scheme_part, rest = db_url.split("://", 1)
    base_scheme = scheme_part.split("+")[0]
    db_url = f"{base_scheme}://{rest}"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

label = (
    "RAILWAY" if "railway" in db_url.lower() or "rlwy" in db_url.lower() else "LOCAL"
)
print(f"\n=== AUDIT SCHEMAS — {label} ===\n")

with psycopg.connect(db_url) as conn:
    cur = conn.cursor()

    # Requête 1 — Tous les schémas non-système
    print("--- Requête 1 : Schémas non-système ---")
    cur.execute("""
        SELECT nspname, pg_get_userbyid(nspowner) as owner
        FROM pg_namespace
        WHERE nspname NOT IN (
            'pg_catalog', 'information_schema',
            'pg_toast', 'pg_temp_1', 'pg_toast_temp_1'
        )
        AND nspname NOT LIKE 'pg_%%'
        ORDER BY nspname
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:30} owner={r[1]}")
    print()

    # Requête 2 — Nombre de tables par schéma
    print("--- Requête 2 : Tables par schéma ---")
    cur.execute("""
        SELECT table_schema,
               COUNT(*) as nb_tables
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
        AND   table_schema NOT IN (
            'pg_catalog', 'information_schema'
        )
        GROUP BY table_schema
        ORDER BY table_schema
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:30} {r[1]} tables")
    print()

    # Requête 3 — Tables hors public et couche_b
    print("--- Requête 3 : Tables hors public et couche_b ---")
    cur.execute("""
        SELECT table_schema,
               table_name
        FROM information_schema.tables
        WHERE table_type   = 'BASE TABLE'
        AND   table_schema NOT IN (
            'pg_catalog', 'information_schema',
            'public', 'couche_b'
        )
        ORDER BY table_schema, table_name
    """)
    rows = cur.fetchall()
    if not rows:
        print("  Aucune table hors public et couche_b")
    for r in rows:
        print(f"  {r[0]:30} {r[1]}")
