"""
M7.4 Phase C — Apply proposals approved → procurement_dict_items.
RÈGLE-V1  : UNIQUEMENT approved + human_validated=FALSE
RÈGLE-V3  : zéro UPDATE sans proposal approved
RÈGLE-M7-06 : 51 seeds intouchables · ROLLBACK si violés (STOP-V5)
STOP-V6   : human_validated=TRUE dans scope → ROLLBACK

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/fix_backfill_taxonomy.py --dry-run
    python scripts/fix_backfill_taxonomy.py
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-8s %(message)s")

SEED_ATTENDU = 51
TAXO_VERSION = "2.0.0"


def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("❌ DATABASE_URL manquante")
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def apply(dry_run: bool = True) -> None:
    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:

        # Count éligibles
        n_eligible = conn.execute("""
            SELECT COUNT(*) AS n
            FROM couche_b.taxo_proposals_v2 p
            JOIN couche_b.procurement_dict_items i USING (item_id)
            WHERE p.status        = 'approved'
              AND p.taxo_version  = %s
              AND i.domain_id     IS NULL
              AND i.human_validated = FALSE
              AND i.active        = TRUE
        """, (TAXO_VERSION,)).fetchone()["n"]

        logger.info(f"Items éligibles : {n_eligible}")

        if n_eligible == 0:
            logger.info("Rien à appliquer")
            return

        if dry_run:
            logger.info(f"DRY-RUN · {n_eligible} items seraient mis à jour")
            return

        with conn.transaction():

            # STOP-V6 : aucun seed dans le scope
            n_seed_scope = conn.execute("""
                SELECT COUNT(*) AS n
                FROM couche_b.taxo_proposals_v2 p
                JOIN couche_b.procurement_dict_items i USING (item_id)
                WHERE p.status          = 'approved'
                  AND p.taxo_version     = %s
                  AND i.domain_id       IS NULL
                  AND i.human_validated  = TRUE
                  AND i.active          = TRUE
            """, (TAXO_VERSION,)).fetchone()["n"]

            if n_seed_scope > 0:
                logger.error(
                    f"⛔ STOP-V6 : {n_seed_scope} seeds dans scope backfill. "
                    "human_validated=TRUE interdit."
                )
                raise RuntimeError("STOP-V6 : seeds dans scope backfill")

            # Apply approved → dict_items
            conn.execute("""
                UPDATE couche_b.procurement_dict_items i
                SET
                    domain_id               = p.domain_id,
                    family_l2_id            = p.family_l2_id,
                    subfamily_id            = p.subfamily_id,
                    taxo_version            = p.taxo_version,
                    classification_confidence = p.confidence,
                    classification_source   = 'llm_validated'
                FROM (
                    SELECT DISTINCT ON (item_id)
                        item_id, domain_id, family_l2_id, subfamily_id,
                        taxo_version, confidence
                    FROM couche_b.taxo_proposals_v2
                    WHERE status       = 'approved'
                      AND taxo_version = %s
                    ORDER BY item_id, approved_at DESC NULLS LAST, created_at DESC
                ) p
                WHERE i.item_id         = p.item_id
                  AND i.domain_id       IS NULL
                  AND i.human_validated = FALSE
                  AND i.active          = TRUE
            """, (TAXO_VERSION,))

            # STOP-V5 : vérifier seed intacts
            seed_n = conn.execute("""
                SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items
                WHERE human_validated = TRUE AND active = TRUE
            """).fetchone()["n"]
            if seed_n != SEED_ATTENDU:
                raise RuntimeError(
                    f"⛔ STOP-V5 : seed {seed_n} ≠ {SEED_ATTENDU} après apply. "
                    "ROLLBACK."
                )

        logger.info(f"✓ {n_eligible} items mis à jour (backfill Phase C)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Simuler sans écrire")
    args = parser.parse_args()
    apply(args.dry_run)
