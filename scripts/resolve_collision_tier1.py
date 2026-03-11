#!/usr/bin/env python3
"""
Résout les collisions TIER-1 du dict_collision_log.
fuzzy_score >= 0.95 → doublon quasi-certain (échelle 0.0-1.0).

Stratégie :
  Pour chaque paire (item_a, item_b) TIER-1 :
    - Garder l'item avec le plus d'usage
      (le plus référencé dans mercurials_item_map)
    - Marquer l'autre active = FALSE
    - Logger dans dict_collision_log resolution

Mode --propose : affiche sans modifier
Mode --apply   : applique après confirmation

Usage :
  python scripts/resolve_collision_tier1.py --propose
  python scripts/resolve_collision_tier1.py --apply
"""

import os
import sys
import logging
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)


def check_env() -> str:
    db = (
        os.environ.get("RAILWAY_DATABASE_URL", "")
        or os.environ.get("DATABASE_URL", "")
    ).replace("postgresql+psycopg://", "postgresql://")
    if not db:
        raise SystemExit("DATABASE_URL absent")
    return db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--propose", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not args.propose and not args.apply:
        print("Usage : --propose ou --apply")
        sys.exit(1)

    conn = psycopg.connect(check_env(), row_factory=dict_row)
    cur = conn.cursor()

    # Charger TIER-1 (fuzzy_score 0.0-1.0, seuil 0.95)
    cur.execute("""
        SELECT
            cl.id,
            cl.item_a_id,
            cl.item_b_id,
            cl.fuzzy_score,
            a.label_fr  AS label_a,
            a.active    AS active_a,
            b.label_fr  AS label_b,
            b.active    AS active_b,
            COALESCE(ua.usage_count, 0) AS usage_a,
            COALESCE(ub.usage_count, 0) AS usage_b
        FROM dict_collision_log cl
        JOIN couche_b.procurement_dict_items a
          ON a.item_id = cl.item_a_id
        JOIN couche_b.procurement_dict_items b
          ON b.item_id = cl.item_b_id
        LEFT JOIN (
            SELECT dict_item_id,
                   COUNT(*) AS usage_count
            FROM mercurials_item_map
            GROUP BY dict_item_id
        ) ua ON ua.dict_item_id = cl.item_a_id
        LEFT JOIN (
            SELECT dict_item_id,
                   COUNT(*) AS usage_count
            FROM mercurials_item_map
            GROUP BY dict_item_id
        ) ub ON ub.dict_item_id = cl.item_b_id
        WHERE cl.resolution = 'unresolved'
          AND cl.fuzzy_score >= 0.95
        ORDER BY cl.fuzzy_score DESC
    """)
    tier1 = cur.fetchall()
    log.info("TIER-1 chargés : %d", len(tier1))

    if not tier1:
        log.info("Aucun TIER-1 à résoudre")
        conn.close()
        sys.exit(0)

    decisions = []
    for row in tier1:
        if row["usage_b"] > row["usage_a"]:
            keep = row["item_b_id"]
            discard = row["item_a_id"]
            keep_label = row["label_b"]
            discard_label = row["label_a"]
        else:
            keep = row["item_a_id"]
            discard = row["item_b_id"]
            keep_label = row["label_a"]
            discard_label = row["label_b"]

        decisions.append({
            "collision_id": row["id"],
            "keep": keep,
            "keep_label": keep_label,
            "discard": discard,
            "discard_label": discard_label,
            "score": row["fuzzy_score"],
            "usage_keep": max(row["usage_a"], row["usage_b"]),
            "usage_discard": min(row["usage_a"], row["usage_b"]),
        })

    if args.propose:
        log.info("\n--- PROPOSITIONS TIER-1 ---")
        for d in decisions[:20]:
            log.info(
                "  GARDER  : %s (%d usages)",
                d["keep_label"], d["usage_keep"]
            )
            log.info(
                "  RETIRER : %s (%d usages) score=%.2f",
                d["discard_label"],
                d["usage_discard"],
                d["score"]
            )
            log.info("  ---")
        if len(decisions) > 20:
            log.info(
                "  ... et %d autres",
                len(decisions) - 20
            )
        conn.close()
        sys.exit(0)

    if args.apply:
        ok = err = 0
        for d in decisions:
            try:
                cur.execute("""
                    UPDATE couche_b.procurement_dict_items
                    SET active = FALSE,
                        updated_at = NOW()
                    WHERE item_id = %s
                """, (d["discard"],))

                cur.execute("""
                    UPDATE mercurials_item_map
                    SET dict_item_id = %s
                    WHERE dict_item_id = %s
                """, (d["keep"], d["discard"]))

                cur.execute("""
                    UPDATE dict_collision_log
                    SET resolution = 'auto_tier1',
                        resolved_by = 'M10A_auto'
                    WHERE id = %s
                """, (d["collision_id"],))

                ok += 1
            except Exception as e:
                log.error(
                    "ERR collision %s: %s",
                    d["collision_id"], e
                )
                err += 1

        conn.commit()
        log.info("DONE ok=%d err=%d", ok, err)

        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE active = TRUE)  AS actifs,
                COUNT(*) FILTER (WHERE active = FALSE) AS inactifs,
                COUNT(*) AS total
            FROM couche_b.procurement_dict_items
        """)
        r = cur.fetchone()
        log.info(
            "Dict : total=%d actifs=%d inactifs=%d",
            r["total"], r["actifs"], r["inactifs"]
        )

        cur.execute("""
            SELECT resolution, COUNT(*) AS n
            FROM dict_collision_log
            GROUP BY resolution
            ORDER BY resolution
        """)
        for r in cur.fetchall():
            log.info(
                "  collision %s : %d",
                r["resolution"], r["n"]
            )

        conn.close()
        sys.exit(1 if err > 0 else 0)


if __name__ == "__main__":
    main()
