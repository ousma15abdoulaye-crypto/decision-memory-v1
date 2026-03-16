#!/usr/bin/env python3
"""
Probe pré-M7.3 · état réel couche_b.
Inclut :
  N0   · prérequis M7.2 (STOP-PRE)
  N1   · alembic head
  N2   · colonnes procurement_dict_items
  N3   · colonnes M7.3 déjà présentes (STOP-N04)
  N4   · tables M7.3 déjà existantes (STOP-N04)
  N5   · counts état actuel
  N6   · triggers existants
  N7   · pgcrypto
  N8   · vendors
  N9   · distribution par domaine
  N_HASH · hash chain existant dans le projet (RÈGLE-N11)

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/probe_m7_3_nerve_center.py
"""

from __future__ import annotations

import os
import sys

import psycopg
from psycopg.rows import dict_row

try:
    from pathlib import Path

    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(_repo_root / ".env")
    load_dotenv(_repo_root / ".env.local")
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)
if not DATABASE_URL:
    sys.exit("[KO] DATABASE_URL manquante")


def _p(conn, label, sql):
    print(f"\n--- {label} ---")
    try:
        rows = conn.execute(sql).fetchall()
        if not rows:
            print("  (vide)")
        for r in rows:
            print(f"  {dict(r)}")
    except Exception as e:
        print(f"  [KO] {e}")


def run() -> None:
    print("=" * 70)
    print("PROBE PRÉ-M7.3 DICT NERVE CENTER")
    print("=" * 70)

    stop_signals = []

    with psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True) as conn:

        # ---- N0 · Prérequis M7.2 (STOP-PRE) --------------------------
        print("\n--- N0_PREREQUIS_M72 ---")
        for tbl in [
            "taxo_l1_domains",
            "taxo_l2_families",
            "taxo_l3_subfamilies",
            "taxo_proposals_v2",
        ]:
            r = conn.execute(
                """
                SELECT COUNT(*) AS n FROM information_schema.tables
                WHERE table_schema='couche_b' AND table_name=%s
                """,
                (tbl,),
            ).fetchone()
            ok = r["n"] > 0
            marker = "[OK]" if ok else "[KO] ABSENT · STOP-PRE"
            print(f"  {tbl:<35} : {marker}")
            if not ok:
                stop_signals.append(
                    f"STOP-PRE · couche_b.{tbl} absent · M7.2 requise"
                )

        # ---- N1 · Alembic -----------------------------------------------
        _p(conn, "N1_ALEMBIC", "SELECT version_num FROM alembic_version")

        # ---- N2 · Colonnes actuelles procurement_dict_items -----------
        _p(
            conn,
            "N2_ITEMS_COLONNES",
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema='couche_b'
              AND table_name='procurement_dict_items'
            ORDER BY ordinal_position
            """,
        )

        # ---- N3 · Colonnes M7.3 déjà présentes (STOP-N04) ---------------
        print("\n--- N3_COLONNES_M73 ---")
        for col in [
            "item_type",
            "default_uom",
            "default_currency",
            "unspsc_code",
            "classification_confidence",
            "classification_source",
            "needs_review",
            "quality_score",
            "last_hash",
        ]:
            r = conn.execute(
                """
                SELECT COUNT(*) AS n FROM information_schema.columns
                WHERE table_schema='couche_b'
                  AND table_name='procurement_dict_items'
                  AND column_name=%s
                """,
                (col,),
            ).fetchone()
            present = r["n"] > 0
            marker = (
                "[WARN] DÉJÀ PRÉSENTE · STOP-N04" if present else "[OK] absente"
            )
            print(f"  {col:<35} : {marker}")
            if present:
                stop_signals.append(f"STOP-N04 · colonne {col} déjà présente")

        # ---- N4 · Tables M7.3 déjà existantes (STOP-N04) -----------------
        print("\n--- N4_TABLES_M73 ---")
        for tbl in [
            "dict_item_history",
            "dict_price_references",
            "dict_uom_conversions",
            "dgmp_thresholds",
            "dict_item_suppliers",
        ]:
            r = conn.execute(
                """
                SELECT COUNT(*) AS n FROM information_schema.tables
                WHERE table_schema='couche_b' AND table_name=%s
                """,
                (tbl,),
            ).fetchone()
            present = r["n"] > 0
            marker = (
                "[WARN] DÉJÀ PRÉSENTE · STOP-N04" if present else "[OK] absente"
            )
            print(f"  {tbl:<35} : {marker}")
            if present:
                stop_signals.append(
                    f"STOP-N04 · table couche_b.{tbl} déjà présente"
                )

        # ---- N5 · Counts -------------------------------------------------
        print("\n--- N5_COUNTS ---")
        queries = [
            (
                "items actifs",
                "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items "
                "WHERE active=TRUE",
            ),
            (
                "items avec domain_id",
                "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items "
                "WHERE domain_id IS NOT NULL",
            ),
            (
                "items taxo_validated",
                "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items "
                "WHERE taxo_validated=TRUE",
            ),
            (
                "seed human_validated",
                "SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items "
                "WHERE human_validated=TRUE",
            ),
            (
                "taxo_proposals_v2 approved",
                "SELECT COUNT(*) AS n FROM couche_b.taxo_proposals_v2 "
                "WHERE status='approved'",
            ),
            (
                "taxo_l1_domains",
                "SELECT COUNT(*) AS n FROM couche_b.taxo_l1_domains",
            ),
            (
                "taxo_l2_families",
                "SELECT COUNT(*) AS n FROM couche_b.taxo_l2_families",
            ),
            (
                "taxo_l3_subfamilies",
                "SELECT COUNT(*) AS n FROM couche_b.taxo_l3_subfamilies",
            ),
        ]
        for label, sql in queries:
            try:
                r = conn.execute(sql).fetchone()
                print(f"  {label:<45} : {r['n']}")
            except Exception as e:
                print(f"  {label:<45} : [KO] {e}")

        # ---- N6 · Triggers existants ------------------------------------
        _p(
            conn,
            "N6_TRIGGERS_EXISTANTS",
            """
            SELECT trigger_name, event_manipulation, action_timing
            FROM information_schema.triggers
            WHERE event_object_schema='couche_b'
              AND event_object_table='procurement_dict_items'
            ORDER BY trigger_name
            """,
        )

        # ---- N7 · pgcrypto ----------------------------------------------
        print("\n--- N7_PGCRYPTO ---")
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM pg_extension WHERE extname='pgcrypto'"
        ).fetchone()
        status = (
            "[OK] présent"
            if r["n"] > 0
            else "[WARN] absent · migration ajoutera CREATE EXTENSION"
        )
        print(f"  pgcrypto : {status}")

        # ---- N8 · Vendors (référentiel canonique) -----------------------
        # Priorité : vendor_identities (référentiel vivant) > legacy vendors
        print("\n--- N8_VENDORS ---")
        tables_vendor = conn.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name ILIKE '%vendor%'
            ORDER BY table_schema, table_name
        """).fetchall()
        for r in tables_vendor:
            print(f"  Table existante : {r['table_schema']}.{r['table_name']}")

        canonical_tables = [
            ("public.vendor_identities", "référentiel vivant"),
            ("couche_b.vendor_identities", "référentiel couche_b"),
            ("public.vendors", "legacy fallback"),
            ("couche_b.vendors", "legacy couche_b"),
        ]
        canonical_source = None
        for tbl, label in canonical_tables:
            try:
                r = conn.execute(
                    f"SELECT COUNT(*) AS n FROM {tbl}"
                ).fetchone()
                n = r["n"]
                marker = " [canonique]" if canonical_source is None else ""
                print(f"  {tbl:<40} : {n} lignes ({label}){marker}")
                if canonical_source is None:
                    canonical_source = tbl
            except Exception as e:
                print(f"  {tbl:<40} : ABSENT ({e})")

        if canonical_source is None:
            print("  -> Aucune table vendors trouvee · ABSENT")

        # ---- N9 · Distribution items par domaine ------------------------
        _p(
            conn,
            "N9_ITEMS_PAR_DOMAINE",
            """
            SELECT COALESCE(domain_id,'NON_CLASSE') AS domain_id,
                   COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE active=TRUE
            GROUP BY domain_id ORDER BY n DESC LIMIT 20
            """,
        )

        # ---- N_HASH · Hash chain existant (RÈGLE-N11) · INFO ONLY ------
        print("\n--- N_HASH_EXISTANT ---")
        print("  Recherche tables/colonnes hash existantes :")

        rows_tables = conn.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name ILIKE '%hash%'
               OR table_name ILIKE '%audit%'
               OR table_name ILIKE '%history%'
               OR table_name ILIKE '%chain%'
            ORDER BY table_schema, table_name
        """).fetchall()
        for r in rows_tables:
            print(f"  TABLE  : {r['table_schema']}.{r['table_name']}")
        if rows_tables:
            stop_signals.append(
                "STOP-N11 · tables hash/audit/history existantes · "
                "vérifier alignement avant créer dict_item_history"
            )

        rows_cols = conn.execute("""
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE column_name ILIKE '%hash%'
            ORDER BY table_schema, table_name, column_name
        """).fetchall()
        for r in rows_cols:
            print(
                f"  COLONNE: {r['table_schema']}.{r['table_name']}"
                f".{r['column_name']} ({r['data_type']})"
            )

        rows_funcs = conn.execute("""
            SELECT routine_schema, routine_name
            FROM information_schema.routines
            WHERE routine_schema IN ('couche_b','public')
              AND (routine_name ILIKE '%hash%'
                   OR routine_name ILIKE '%digest%'
                   OR routine_name ILIKE '%audit%')
            ORDER BY routine_schema, routine_name
        """).fetchall()
        for r in rows_funcs:
            print(f"  FUNC   : {r['routine_schema']}.{r['routine_name']}")

        rows_triggers = conn.execute("""
            SELECT trigger_schema, trigger_name,
                   event_object_table, action_timing, event_manipulation
            FROM information_schema.triggers
            WHERE trigger_name ILIKE '%hash%'
               OR trigger_name ILIKE '%audit%'
               OR trigger_name ILIKE '%history%'
            ORDER BY trigger_schema, trigger_name
        """).fetchall()
        for r in rows_triggers:
            print(
                f"  TRIGGER: {r['trigger_schema']}.{r['trigger_name']} "
                f"[{r['action_timing']} {r['event_manipulation']} "
                f"ON {r['event_object_table']}]"
            )

        if not rows_tables and not rows_cols and not rows_funcs and not rows_triggers:
            print("  [OK] Aucun mécanisme hash existant · création libre")

    # ---- Résumé STOP signals -------------------------------------------
    print("\n" + "=" * 70)
    if stop_signals:
        print("[STOP] STOP SIGNALS :")
        for s in stop_signals:
            print(f"  -> {s}")
        print("\nNE PAS CONTINUER · POSTER · GO TECH LEAD")
    else:
        print("[OK] PROBE OK · POSTER N0->N_HASH · GO TECH LEAD")
    print("=" * 70)


if __name__ == "__main__":
    run()
