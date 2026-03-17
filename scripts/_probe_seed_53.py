"""
PROBE-SEED · Identification des 53 seeds vs 51 attendus.
Exécution immédiate · zéro écriture.
GO CTO sur chaque output.
"""
from __future__ import annotations

import os
import sys

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("DATABASE_URL manquante")
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def run() -> None:
    print("=" * 80)
    print("PROBE-SEED · 53 vs 51 · IDENTIFICATION INTRUS")
    print("=" * 80)

    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
        # PROBE-SEED-1
        print("\n--- PROBE-SEED-1 : Liste complete des 53 seeds (ordre item_id) ---")
        rows = conn.execute("""
            SELECT
                item_id,
                label_fr,
                sources::text AS sources,
                confidence_score,
                updated_at
            FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE
              AND active = TRUE
            ORDER BY item_id ASC
        """).fetchall()
        print(f"Total : {len(rows)}")
        for r in rows:
            print(
                f"  {r['item_id']:<30} | {str(r['label_fr'])[:35]:<35} | "
                f"{str(r['sources'])[:25]:<25} | conf={r['confidence_score']}"
            )

        # PROBE-SEED-2
        print("\n--- PROBE-SEED-2 : Derniers par updated_at (intrus probables) ---")
        rows = conn.execute("""
            SELECT
                item_id,
                label_fr,
                sources::text AS sources,
                confidence_score,
                updated_at
            FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE
              AND active = TRUE
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 10
        """).fetchall()
        for r in rows:
            print(
                f"  {r['item_id']:<30} | {str(r['label_fr'])[:35]:<35} | "
                f"{str(r['sources'])[:25]:<25} | {r['updated_at']}"
            )

        # PROBE-SEED-3
        print("\n--- PROBE-SEED-3 : Seeds dont sources NE contient PAS 'seed' ---")
        rows = conn.execute("""
            SELECT
                item_id,
                label_fr,
                sources::text AS sources,
                updated_at
            FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE
              AND active = TRUE
              AND sources::text NOT LIKE '%seed%'
            ORDER BY item_id
        """).fetchall()
        print(f"Total : {len(rows)}")
        for r in rows:
            print(f"  {r['item_id']:<30} | {str(r['label_fr'])[:40]:<40} | {r['sources']}")

        # PROBE-SEED-4
        print("\n--- PROBE-SEED-4 : Seeds avec sources mercuriale ---")
        rows = conn.execute("""
            SELECT
                item_id,
                label_fr,
                sources::text AS sources,
                confidence_score,
                updated_at
            FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE
              AND active = TRUE
              AND sources::text LIKE '%mercuriale%'
            ORDER BY updated_at DESC NULLS LAST
        """).fetchall()
        print(f"Total : {len(rows)}")
        for r in rows:
            print(
                f"  {r['item_id']:<30} | {str(r['label_fr'])[:35]:<35} | "
                f"{str(r['sources'])[:30]:<30} | conf={r['confidence_score']}"
            )

    print("\n" + "=" * 80)
    print("POSTER P1-P4. STOP. GO CTO.")
    print("=" * 80)


if __name__ == "__main__":
    run()
