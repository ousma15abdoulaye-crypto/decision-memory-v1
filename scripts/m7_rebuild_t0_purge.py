"""
M7-REBUILD · Temps 0 · Purge propre.
Une seule transaction. Ordre strict.
REGLE-39 : psycopg v3 · get_db_url()

Usage:
    $env:DATABASE_URL = "<Railway>"
    python scripts/m7_rebuild_t0_purge.py
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
    print("=" * 60)
    print("M7-REBUILD · TEMPS 0 · PURGE PROPRE")
    print("=" * 60)

    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
        with conn.transaction():
            # T0-A : Purger proposals bancales
            conn.execute("TRUNCATE couche_b.taxo_proposals_v2")
            print("  T0-A : taxo_proposals_v2 truncated")

            # T0-C : Remettre classification à zéro AVANT truncate (FK)
            # 1) Tous les items : domain_id/family_l2_id/subfamily_id = NULL (pour TRUNCATE)
            # 2) Non-seeds : birth_*, llm_*, etc. = NULL · seeds intouchables (item_uid)
            cur1 = conn.execute("""
                UPDATE couche_b.procurement_dict_items
                SET domain_id = NULL, family_l2_id = NULL, subfamily_id = NULL
            """)
            cur = conn.execute("""
                UPDATE couche_b.procurement_dict_items
                SET
                    taxo_version              = NULL,
                    classification_confidence = NULL,
                    classification_source     = NULL,
                    birth_domain_id           = NULL,
                    birth_family_l2_id        = NULL,
                    birth_subfamily_id        = NULL,
                    llm_domain_id_raw         = NULL,
                    llm_family_l2_id_raw      = NULL,
                    llm_subfamily_id_raw      = NULL
                WHERE human_validated = FALSE
            """)
            print(f"  T0-C : {cur1.rowcount} items domain_id null · {cur.rowcount} non-seeds reset")

            # T0-B : Purger taxonomie théorique · DELETE (pas TRUNCATE CASCADE)
            # TRUNCATE CASCADE supprimerait dict_items (FK vers taxo)
            conn.execute("DELETE FROM couche_b.taxo_l3_subfamilies")
            conn.execute("DELETE FROM couche_b.taxo_l2_families")
            conn.execute("DELETE FROM couche_b.taxo_l1_domains")
            print("  T0-B : taxo L1/L2/L3 deleted")

        # T0-D : Vérification
        r = conn.execute("""
            SELECT
                COUNT(*)                                              AS total_actifs,
                COUNT(*) FILTER (WHERE domain_id IS NULL)             AS sans_taxo,
                COUNT(*) FILTER (WHERE human_validated = TRUE)        AS seeds,
                COUNT(*) FILTER (WHERE item_uid IS NOT NULL)          AS avec_uid,
                (SELECT COUNT(*) FROM couche_b.taxo_l1_domains)       AS l1_count,
                (SELECT COUNT(*) FROM couche_b.taxo_l2_families)      AS l2_count,
                (SELECT COUNT(*) FROM couche_b.taxo_l3_subfamilies)   AS l3_count,
                (SELECT COUNT(*) FROM couche_b.taxo_proposals_v2)     AS proposals_count
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
        """).fetchone()

    print()
    print("  T0-D : Vérification")
    print("-" * 40)
    for k, v in r.items():
        print(f"  {k:<20} : {v}")
    print("-" * 40)

    # STOP-T0
    if r["seeds"] != 51:
        print(f"\n  STOP-T0 : seeds != 51 (got {r['seeds']})")
        sys.exit(1)
    if r["avec_uid"] != 1489:
        print(f"\n  STOP-T0 : avec_uid != 1489 (got {r['avec_uid']})")
        sys.exit(1)

    print("\n  OK : seeds=51 · uid=1489 · purge OK")
    print("=" * 60)


if __name__ == "__main__":
    run()
