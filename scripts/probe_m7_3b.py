"""
Probe pré-migration M7.3b · RÈGLE-08.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/probe_m7_3b.py
"""

from __future__ import annotations

import os
import sys

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("❌ DATABASE_URL manquante")


def run() -> None:
    print("=" * 65)
    print("PROBE M7.3b · PRÉ-MIGRATION LEGACY FAMILIES")
    print("=" * 65)

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:

        # L1 · HEAD Alembic réel → down_revision à copier
        print("\n--- L1_ALEMBIC_HEAD ---")
        r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        print(f"  HEAD : {r['version_num']}")
        print("  → Copier exactement dans down_revision")

        # L2 · Usage family_id actuel
        print("\n--- L2_FAMILY_ID_USAGE ---")
        r = conn.execute("""
            SELECT
                COUNT(*)                                       AS total,
                COUNT(*) FILTER (WHERE family_id IS NOT NULL)  AS avec,
                COUNT(*) FILTER (WHERE family_id IS NULL)      AS sans,
                COUNT(DISTINCT family_id)                      AS distinctes
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
        """).fetchone()
        print(f"  Total actifs     : {r['total']}")
        print(f"  Avec family_id   : {r['avec']}")
        print(f"  Sans family_id   : {r['sans']}")
        print(f"  Valeurs distinct : {r['distinctes']}")

        # L3 · Valeurs distinctes
        print("\n--- L3_FAMILY_ID_VALEURS ---")
        rows = conn.execute("""
            SELECT family_id, COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE AND family_id IS NOT NULL
            GROUP BY family_id ORDER BY n DESC
        """).fetchall()
        for r in rows:
            print(f"  {r['family_id']:<30} {r['n']}")

        # L4 · Triggers existants sur dict_items
        print("\n--- L4_TRIGGERS_EXISTANTS ---")
        rows = conn.execute("""
            SELECT trigger_name, event_manipulation, action_timing
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
            ORDER BY trigger_name
        """).fetchall()
        if not rows:
            print("  (aucun)")
        for r in rows:
            print(
                f"  {r['trigger_name']:<45} "
                f"{r['action_timing']} {r['event_manipulation']}"
            )

        # L5 · Colonne deprecated déjà présente ?
        print("\n--- L5_DEPRECATED_EXISTE ---")
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_families'
              AND column_name  = 'deprecated'
        """).fetchone()
        print(f"  deprecated présente : {'OUI' if r['n'] > 0 else 'NON'}")

        # L6 · Vue legacy déjà présente ?
        print("\n--- L6_VUE_LEGACY ---")
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.views
            WHERE table_schema = 'couche_b'
              AND table_name   = 'legacy_procurement_families'
        """).fetchone()
        print(f"  vue legacy présente : {'OUI' if r['n'] > 0 else 'NON'}")

        # L7 · match_item() en DB ?
        print("\n--- L7_MATCH_ITEM_DB ---")
        rows = conn.execute("""
            SELECT routine_schema, routine_name
            FROM information_schema.routines
            WHERE routine_name ILIKE '%match%item%'
               OR routine_name ILIKE '%item%match%'
            ORDER BY 1, 2
        """).fetchall()
        if not rows:
            print("  (aucune fonction match_item en DB)")
        for r in rows:
            print(f"  {r['routine_schema']}.{r['routine_name']}")

    print("\n--- L8_USAGE_FAMILY_ID_CODE ---")
    print("  Commande à exécuter séparément :")
    print('  grep -rn "family_id" src/ ' "--include='*.py' | grep -v '#'")
    print("\n" + "=" * 65)
    print("POSTER L1→L7 + grep L8 · STOP · GO TECH LEAD")
    print("=" * 65)


if __name__ == "__main__":
    run()
