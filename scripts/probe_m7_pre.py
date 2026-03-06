#!/usr/bin/env python3
"""
Probe pré-M7 · schéma réel couche_b.
RÈGLE-08 · DMSMISTRAL = warning en TEMPS 1 · pas stop.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/probe_m7_pre.py
"""

from __future__ import annotations
import os
import sys

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)
if not DATABASE_URL:
    sys.exit("[KO] DATABASE_URL manquante · STOP-01")

FAMILLES_ATTENDUES = {
    "carburants",
    "construction_agregats",
    "construction_fer",
    "construction_liants",
    "vehicules",
    "informatique",
    "alimentation",
    "medicaments",
    "equipements",
}


def _p(conn, label: str, sql: str, params=None) -> None:
    print(f"\n--- {label} ---")
    try:
        if params is not None:
            rows = conn.execute(sql, params).fetchall()
        else:
            rows = conn.execute(sql).fetchall()
        print("  (vide)" if not rows else "")
        for r in rows:
            print(f"  {dict(r)}")
    except Exception as exc:
        print(f"  [KO] {exc}")


def run() -> None:
    print("=" * 65)
    print("PROBE PRE-M7")
    print("=" * 65)

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:

        _p(conn, "P0_ALEMBIC", "SELECT version_num FROM alembic_version;")

        _p(
            conn,
            "P1_FAMILLES_REELLES",
            """
            SELECT family_id, label_fr, criticite
            FROM couche_b.procurement_dict_families
            ORDER BY family_id;
            """,
        )

        # P1-CHECK ecart attendu vs reel
        print("\n--- P1_CHECK_ECART ---")
        rows = conn.execute(
            """
            SELECT family_id
            FROM couche_b.procurement_dict_families
            ORDER BY family_id
            """
        ).fetchall()
        reels = {r["family_id"] for r in rows}
        manquants = FAMILLES_ATTENDUES - reels
        inattendus = reels - FAMILLES_ATTENDUES
        if manquants:
            print(f"  [WARN] MANQUANTS   : {manquants} -> STOP-04")
        if inattendus:
            print(f"  [WARN] INATTENDUS  : {inattendus} -> poster · GO CTO")
        if not manquants and not inattendus:
            print("  [OK] Familles coherentes")

        _p(
            conn,
            "P2_DISTRIBUTION",
            """
            SELECT
                f.family_id,
                f.label_fr,
                COUNT(i.item_id) AS nb_items,
                SUM(CASE WHEN i.human_validated
                    THEN 1 ELSE 0 END) AS nb_validated
            FROM couche_b.procurement_dict_families f
            LEFT JOIN couche_b.procurement_dict_items i
                ON  i.family_id = f.family_id
                AND i.active    = TRUE
            GROUP BY f.family_id, f.label_fr
            ORDER BY nb_items DESC;
            """,
        )

        _p(
            conn,
            "P3_EQUIPEMENTS_COUNT",
            """
            SELECT COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE family_id = 'equipements'
              AND active    = TRUE;
            """,
        )

        _p(
            conn,
            "P4_EQUIPEMENTS_SAMPLE",
            """
            SELECT item_id, label_fr, canonical_slug
            FROM couche_b.procurement_dict_items
            WHERE family_id = 'equipements'
              AND active    = TRUE
            ORDER BY item_id
            LIMIT 10;
            """,
        )

        _p(
            conn,
            "P5_SEED_INTACTS",
            """
            SELECT COUNT(*) AS nb_seed
            FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE
              AND active          = TRUE;
            """,
        )
        print("  Attendu : 51")

        _p(
            conn,
            "P6_PROPOSALS_M6",
            """
            SELECT status, COUNT(*) AS n
            FROM couche_b.dict_proposals
            GROUP BY status ORDER BY n DESC;
            """,
        )

        _p(
            conn,
            "P7_TABLE_M7_EXISTE",
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'couche_b'
              AND table_name   = 'dict_family_proposals';
            """,
        )
        print("  Attendu : vide")

        _p(
            conn,
            "P8_EXTENSIONS",
            """
            SELECT extname, extversion FROM pg_extension
            WHERE extname IN ('pg_trgm','unaccent')
            ORDER BY extname;
            """,
        )

    # P9 · Env vars · DMSMISTRAL = warning uniquement en TEMPS 1
    print("\n--- P9_ENV_VARS ---")
    for var in [
        "DATABASE_URL",
        "DMSMISTRAL",
        "MISTRAL_API_KEY",
        "M7_COST_PER_1M_INPUT",
        "M7_COST_PER_1M_OUTPUT",
    ]:
        val = os.environ.get(var)
        if val:
            print(f"  {var:<28} : [OK] ****{val[-4:]}")
        else:
            level = (
                "[WARN]"
                if var
                in (
                    "DMSMISTRAL",
                    "MISTRAL_API_KEY",
                    "M7_COST_PER_1M_INPUT",
                    "M7_COST_PER_1M_OUTPUT",
                )
                else "[KO] STOP"
            )
            print(f"  {var:<28} : {level} · absente")

    print("\n" + "=" * 65)
    print("POSTER P0->P9 · STOP · ATTENDRE GO CTO")
    print("=" * 65)


if __name__ == "__main__":
    run()
