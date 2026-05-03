"""ÉTAPE 2 · Vérification colonnes post-migration M7.4a."""

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
    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
        print("--- Colonnes identite M7.4a ---")
        rows = conn.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name IN (
                  'item_uid', 'item_code',
                  'birth_domain_id', 'birth_family_l2_id', 'birth_subfamily_id',
                  'id_version',
                  'llm_domain_id_raw', 'llm_family_l2_id_raw', 'llm_subfamily_id_raw'
              )
            ORDER BY column_name
        """).fetchall()
        for r in rows:
            print(
                f"  {r['column_name']:<30} {r['data_type']:<30} nullable={r['is_nullable']}"
            )

        print(f"\n  Total : {len(rows)} colonnes")

        print("\n--- Backfill seeds (birth_* rempli) ---")
        r = conn.execute("""
            SELECT
                COUNT(*) FILTER (WHERE birth_domain_id IS NOT NULL) AS seeds_avec_birth,
                COUNT(*) FILTER (WHERE birth_domain_id IS NULL)     AS seeds_sans_birth,
                COUNT(*)                                            AS total_seeds
            FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE
              AND active = TRUE
        """).fetchone()
        print(f"  seeds_avec_birth : {r['seeds_avec_birth']}")
        print(f"  seeds_sans_birth : {r['seeds_sans_birth']}")
        print(f"  total_seeds      : {r['total_seeds']}")


if __name__ == "__main__":
    run()
