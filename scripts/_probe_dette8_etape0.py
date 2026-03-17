#!/usr/bin/env python3
"""
DETTE-8 ÉTAPE 0 — PROBE OBLIGATOIRE
Exécute les requêtes probe du mandat.
Usage: python scripts/_probe_dette8_etape0.py
"""
from __future__ import annotations

import os
import sys

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERREUR: DATABASE_URL non défini")
        sys.exit(1)

    url = url.replace("postgresql+psycopg://", "postgresql://")

    # STOP-5: Railway sans DMS_ALLOW_RAILWAY
    if "railway" in url.lower() and os.environ.get("DMS_ALLOW_RAILWAY") != "1":
        print("STOP-5: DATABASE_URL Railway détecté sans DMS_ALLOW_RAILWAY=1")
        sys.exit(1)

    conn = psycopg.connect(conninfo=url, row_factory=dict_row)
    conn.autocommit = True

    print("=" * 60)
    print("0.2 — Structure market_signals_v2")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'market_signals_v2'
            ORDER BY ordinal_position;
        """)
        for r in cur.fetchall():
            print(f"  {r['column_name']}: {r['data_type']}")

    print("\n" + "=" * 60)
    print("0.3 — Colonnes imc_revision_*")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'market_signals_v2'
              AND column_name IN (
                'imc_revision_applied',
                'imc_revision_factor',
                'imc_revision_at'
              );
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"  {r['column_name']}: {r['data_type']}")
        if not rows:
            print("  (aucune — 046b non appliqué?)")

    print("\n" + "=" * 60)
    print("0.4 — Échantillon market_signals_v2")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM market_signals_v2;")
        total = cur.fetchone()["n"]
        print(f"  Total rows: {total}")
        cur.execute("""
            SELECT
              item_id, zone_id, price_avg, formula_version,
              imc_revision_applied, created_at
            FROM market_signals_v2
            LIMIT 5;
        """)
        for r in cur.fetchall():
            print(f"  {r}")

    print("\n" + "=" * 60)
    print("0.5 — imc_entries (catégories)")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT category_raw, COUNT(*) as nb_periodes
            FROM imc_entries
            GROUP BY category_raw
            ORDER BY nb_periodes DESC
            LIMIT 15;
        """)
        for r in cur.fetchall():
            print(f"  {r['category_raw']}: {r['nb_periodes']}")

    print("\n" + "=" * 60)
    print("0.6 — imc_category_item_map COUNT (doit être 0)")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM imc_category_item_map;")
        row = cur.fetchone()
        n = row["n"] if isinstance(row, dict) else row[0]
        print(f"  COUNT = {n}")

    print("\n" + "=" * 60)
    print("0.7 — Structure imc_category_item_map")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'imc_category_item_map'
            ORDER BY ordinal_position;
        """)
        for r in cur.fetchall():
            print(f"  {r['column_name']}: {r['data_type']}")

    print("\n" + "=" * 60)
    print("0.8 — Échantillon couche_b.procurement_dict_items")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT item_id, canonical_slug, family_id
            FROM couche_b.procurement_dict_items
            LIMIT 10;
        """)
        for r in cur.fetchall():
            print(f"  {r}")

    conn.close()
    print("\n[PROBE ÉTAPE 0 terminée]")


if __name__ == "__main__":
    main()
