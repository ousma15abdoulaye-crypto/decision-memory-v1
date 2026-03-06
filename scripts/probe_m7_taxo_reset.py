#!/usr/bin/env python3
"""
Probe pre-M7.2 · etat reel couche_b avant migration taxonomie.
REGLE-08 · zero hypothese.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/probe_m7_taxo_reset.py
"""
from __future__ import annotations

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

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)
if not DATABASE_URL:
    sys.exit("[KO] DATABASE_URL manquante")


def _p(conn, label, sql, params=None):
    print(f"\n--- {label} ---")
    try:
        rows = conn.execute(sql, params).fetchall()
        print("  (vide)" if not rows else "")
        for r in rows:
            print(f"  {dict(r)}")
    except Exception as e:
        print(f"  [KO] {e}")


def run() -> None:
    print("=" * 65)
    print("PROBE PRE-M7.2 TAXONOMY RESET")
    print("=" * 65)

    with psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True) as conn:

        # T1 · Alembic
        _p(conn, "T1_ALEMBIC", "SELECT version_num FROM alembic_version")

        # T2 · Colonnes procurement_dict_items
        _p(
            conn,
            "T2_ITEMS_COLONNES",
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
            ORDER BY ordinal_position
            """,
        )

        # T3 · Counts
        print("\n--- T3_COUNTS ---")
        for label, sql in [
            (
                "procurement_dict_items actifs",
                "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items WHERE active=TRUE",
            ),
            (
                "procurement_dict_items human_validated",
                "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items WHERE human_validated=TRUE",
            ),
            (
                "procurement_dict_families",
                "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_families",
            ),
            (
                "dict_proposals",
                "SELECT COUNT(*) AS n FROM couche_b.dict_proposals",
            ),
        ]:
            try:
                r = conn.execute(sql).fetchone()
                print(f"  {label:<45} : {r['n']}")
            except Exception as e:
                print(f"  {label:<45} : [KO] {e}")

        # T4 · Familles legacy
        _p(
            conn,
            "T4_FAMILLES_LEGACY",
            """
            SELECT family_id, label_fr, criticite
            FROM couche_b.procurement_dict_families
            ORDER BY family_id
            """,
        )

        # T5 · Tables taxo_l* deja existantes ? (STOP-T1)
        print("\n--- T5_TAXO_TABLES_EXISTE ---")
        rows = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'couche_b'
              AND table_name IN (
                'taxo_l1_domains',
                'taxo_l2_families',
                'taxo_l3_subfamilies',
                'taxo_proposals_v2'
              )
            ORDER BY table_name
        """).fetchall()
        if rows:
            print("  [WARN] STOP-T1 · tables taxo deja presentes · poster · GO TL")
            for r in rows:
                print(f"  {dict(r)}")
        else:
            print("  [OK] Tables taxo absentes · GO migration")

        # T6 · Items par famille actuelle
        _p(
            conn,
            "T6_ITEMS_PAR_FAMILLE",
            """
            SELECT family_id, COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
            GROUP BY family_id
            ORDER BY n DESC
            """,
        )

        # T7 · Colonnes procurement_dict_families
        _p(
            conn,
            "T7_FAMILLES_COLONNES",
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_families'
            ORDER BY ordinal_position
            """,
        )

        # T8 · Vendors
        print("\n--- T8_VENDORS_ETAT ---")
        for tbl in [
            "public.vendors",
            "public.vendor_identities",
            "couche_b.vendors",
            "couche_b.vendor_identities",
        ]:
            try:
                r = conn.execute(f"SELECT COUNT(*) AS n FROM {tbl}").fetchone()
                print(f"  {tbl:<40} : {r['n']} lignes")
            except Exception as e:
                print(f"  {tbl:<40} : ABSENT ({e})")

        # T9 · dict_proposals M6 etat
        _p(
            conn,
            "T9_PROPOSALS_M6",
            """
            SELECT status, COUNT(*) AS n
            FROM couche_b.dict_proposals
            GROUP BY status ORDER BY n DESC
            """,
        )

        # T10 · Extensions
        _p(
            conn,
            "T10_EXTENSIONS",
            """
            SELECT extname, extversion FROM pg_extension
            WHERE extname IN ('pg_trgm','unaccent')
            ORDER BY extname
            """,
        )

    print("\n" + "=" * 65)
    print("POSTER T1->T10 · STOP · ATTENDRE GO TECH LEAD")
    print("=" * 65)


if __name__ == "__main__":
    run()
