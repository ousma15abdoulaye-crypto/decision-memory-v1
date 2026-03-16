"""PROBE-COV + PROBE-UID · Verification couverture et item_uid."""
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
    print("PROBE-COV + PROBE-UID")
    print("=" * 80)

    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
        print("\n--- PROBE-COV-1 : Etat reel des proposals ---")
        rows = conn.execute("""
            SELECT status, subfamily_id, COUNT(*) AS n
            FROM couche_b.taxo_proposals_v2
            WHERE taxo_version = '2.0.0'
            GROUP BY status, subfamily_id
            ORDER BY n DESC
            LIMIT 30
        """).fetchall()
        for r in rows:
            print(f"  {r['status']:<12} | {r['subfamily_id']:<35} | {r['n']}")

        print("\n--- PROBE-COV-2 : Items a classifier vs proposals valides ---")
        r = conn.execute("""
            SELECT
                COUNT(*) AS total_a_classifier,
                COUNT(*) FILTER (WHERE EXISTS (
                    SELECT 1 FROM couche_b.taxo_proposals_v2 p
                    WHERE p.item_id = i.item_id
                      AND p.status IN ('pending', 'approved')
                      AND p.taxo_version = '2.0.0'
                )) AS avec_proposal_valide,
                COUNT(*) FILTER (WHERE NOT EXISTS (
                    SELECT 1 FROM couche_b.taxo_proposals_v2 p
                    WHERE p.item_id = i.item_id
                      AND p.status IN ('pending', 'approved')
                      AND p.taxo_version = '2.0.0'
                )) AS sans_proposal_valide
            FROM couche_b.procurement_dict_items i
            WHERE i.active = TRUE AND i.domain_id IS NULL
              AND i.label_fr IS NOT NULL AND LENGTH(TRIM(i.label_fr)) > 5
        """).fetchone()
        print(f"  total_a_classifier   : {r['total_a_classifier']}")
        print(f"  avec_proposal_valide : {r['avec_proposal_valide']}")
        print(f"  sans_proposal_valide: {r['sans_proposal_valide']}")

        print("\n--- PROBE-UID-1 : Echantillon item_uid (UUIDv7?) ---")
        rows = conn.execute("""
            SELECT item_uid, LEFT(item_uid, 8) AS prefix_time, LENGTH(item_uid) AS len
            FROM couche_b.procurement_dict_items
            WHERE item_uid IS NOT NULL
            ORDER BY item_uid
            LIMIT 5
        """).fetchall()
        for r in rows:
            print(f"  {r['item_uid']} | prefix={r['prefix_time']} len={r['len']}")

        print("\n--- PROBE-UID-2 : Comptage item_uid ---")
        r = conn.execute("""
            SELECT
                COUNT(*) FILTER (WHERE item_uid IS NULL)     AS uid_null,
                COUNT(*) FILTER (WHERE item_uid IS NOT NULL) AS uid_present,
                COUNT(*) AS total
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
        """).fetchone()
        print(f"  uid_null    : {r['uid_null']}")
        print(f"  uid_present : {r['uid_present']}")
        print(f"  total       : {r['total']}")

    print("\n" + "=" * 80)
    print("POSTER 4 OUTPUTS. STOP. GO CTO.")
    print("=" * 80)


if __name__ == "__main__":
    run()
