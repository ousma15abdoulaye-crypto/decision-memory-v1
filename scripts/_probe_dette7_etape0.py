#!/usr/bin/env python3
"""DETTE-7 ÉTAPE 0 — Probe obligatoire avant migration 046."""

import os
import subprocess
import sys

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    print("ERREUR: DATABASE_URL non défini")
    sys.exit(1)

# Normalize for psycopg (strip SQLAlchemy driver)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
if "postgresql+psycopg://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")

def run_sql(query: str, description: str) -> None:
    """Run SQL via psycopg and print results."""
    import psycopg
    from psycopg.rows import dict_row
    print(f"\n--- {description} ---")
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                if rows:
                    for r in rows:
                        print(dict(r))
                else:
                    print("(aucune ligne)")
    except Exception as e:
        print(f"ERREUR: {e}")

def main():
    import psycopg
    from psycopg.rows import dict_row

    print("=" * 60)
    print("DETTE-7 ÉTAPE 0 — PROBE")
    print("=" * 60)

    # 0.1 — Alembic head
    print("\n--- 0.1 alembic heads ---")
    r = subprocess.run(["alembic", "heads"], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    print(r.stdout or r.stderr)

    # 0.2 — Tables IMC
    run_sql("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name LIKE 'imc%'
        ORDER BY table_name;
    """, "0.2 Tables IMC existantes")

    # 0.3 — Structure imc_entries
    run_sql("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'imc_entries'
        ORDER BY ordinal_position;
    """, "0.3 Structure imc_entries")

    # 0.4 — Structure procurement_references (ou dict)
    run_sql("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'procurement_references'
        ORDER BY ordinal_position;
    """, "0.4 Structure procurement_references")

    # Si procurement_references n'existe pas, essayer procurement_dict_items
    run_sql("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'couche_b' AND table_name = 'procurement_dict_items'
        ORDER BY ordinal_position
        LIMIT 15;
    """, "0.4b Structure couche_b.procurement_dict_items")

    # 0.5 — Comptes
    run_sql("""
        SELECT
          (SELECT COUNT(*) FROM imc_entries) AS imc_entries_count,
          (SELECT COUNT(*) FROM imc_sources) AS imc_sources_count;
    """, "0.5 Comptes imc_entries, imc_sources")

    run_sql("""
        SELECT COUNT(*) AS dict_count FROM procurement_references;
    """, "0.5b Compte procurement_references")

    run_sql("""
        SELECT COUNT(*) AS dict_count FROM couche_b.procurement_dict_items;
    """, "0.5c Compte couche_b.procurement_dict_items")

    # 0.6 — Échantillon imc_entries (year/month vs period_year/period_month)
    run_sql("""
        SELECT category_raw, period_year AS year, period_month AS month, index_value
        FROM imc_entries
        LIMIT 10;
    """, "0.6 Échantillon imc_entries")

    # 0.7 — Échantillon dict
    run_sql("""
        SELECT id, canonical, category_id FROM procurement_references LIMIT 10;
    """, "0.7 Échantillon procurement_references (id, canonical, category_id)")

    run_sql("""
        SELECT item_id AS id, canonical_slug AS canonical, family_id AS category_id
        FROM couche_b.procurement_dict_items
        LIMIT 10;
    """, "0.7b Échantillon couche_b.procurement_dict_items")

    # 0.8 — Fichiers migrations
    print("\n--- 0.8 Fichiers migrations (5 derniers) ---")
    versions_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic", "versions")
    files = sorted([f for f in os.listdir(versions_dir) if f.endswith(".py") and not f.startswith("__")])
    for f in files[-5:]:
        print(f"  {f}")

    # 0.9 — Branche Git
    print("\n--- 0.9 Branche Git ---")
    r = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    print(f"  Branche: {r.stdout.strip()}")
    r = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    print("  Derniers commits:")
    for line in r.stdout.strip().split("\n"):
        print(f"    {line}")

    print("\n" + "=" * 60)
    print("PROBE ÉTAPE 0 TERMINÉE")
    print("=" * 60)

if __name__ == "__main__":
    main()
