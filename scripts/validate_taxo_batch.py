"""
M7.4 Phase B — Validation semi-automatique.
DA-AUDIT : approved_by + approved_at obligatoires.
RÈGLE-25 : LLM propose · AO valide · jamais l'inverse.

Stratégies :
  AUTO-APPROVE : confidence ≥ 0.90 + FK cohérente + non résiduel
  REVIEW-AO    : 0.75 ≤ confidence < 0.90
  FLAGGED      : confidence < 0.75 OU résiduel OU FK incohérente

Usage :
    $env:DATABASE_URL   = "<Railway>"
    $env:AO_USER_ID     = "<INTEGER (users.id)>"

    python scripts/validate_taxo_batch.py --dry-run
    python scripts/validate_taxo_batch.py
    python scripts/validate_taxo_batch.py --domain SANTE
    python scripts/validate_taxo_batch.py --approve-item <item_id>
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-8s %(message)s")

SEUIL_AUTO_APPROVE = 0.90
SEUIL_REVIEW       = 0.75
SEED_ATTENDU       = 51
TAXO_VERSION       = "2.0.0"


def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("❌ DATABASE_URL manquante")
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def get_ao_user_id() -> Optional[int]:
    """DA-AUDIT : actor_id pour traçabilité complète. users.id = INTEGER.

    Retourne None si la variable n'est pas définie (autorisé uniquement en
    dry-run). Quitte le processus si la valeur est définie mais invalide.
    """
    uid = os.environ.get("AO_USER_ID")
    if uid is None:
        return None
    try:
        return int(uid)
    except ValueError:
        sys.exit(
            f"❌ AO_USER_ID '{uid}' n'est pas un entier valide "
            f"— attendu : users.id (INTEGER)"
        )


def load_taxonomy_fk(conn: psycopg.Connection) -> dict[str, str]:
    """Charge L2→L1 depuis DB · DA-TAXO-DB."""
    rows = conn.execute(
        "SELECT family_l2_id, domain_id FROM couche_b.taxo_l2_families"
    ).fetchall()
    return {r["family_l2_id"]: r["domain_id"] for r in rows}


def is_fk_coherent(
    domain_id: str,
    family_l2_id: str,
    l2_to_l1: dict[str, str],
) -> bool:
    expected = l2_to_l1.get(family_l2_id)
    return expected is None or expected == domain_id


def run(
    dry_run: bool,
    domain_filter: Optional[str] = None,
    approve_item: Optional[str] = None,
) -> None:
    ao_user_id = get_ao_user_id()
    if not dry_run and ao_user_id is None:
        sys.exit(
            "❌ AO_USER_ID manquant — export AO_USER_ID=<users.id INTEGER>\n"
            "   (DA-AUDIT : approved_by obligatoire hors dry-run)\n"
            "   Utilisez --dry-run pour simuler sans écriture."
        )

    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:

        l2_to_l1 = load_taxonomy_fk(conn)

        # Mode approbation manuelle d'un item spécifique
        if approve_item:
            if dry_run:
                print(f"DRY-RUN · approbation {approve_item} simulée")
                return
            with conn.transaction():
                conn.execute("""
                    UPDATE couche_b.taxo_proposals_v2
                    SET status      = 'approved',
                        approved_by = %s,
                        approved_at = NOW(),
                        reviewed_by = %s,
                        updated_at  = NOW()
                    WHERE item_id      = %s
                      AND taxo_version = %s
                      AND status       = 'pending'
                """, (ao_user_id, ao_user_id, approve_item, TAXO_VERSION))
            print(f"✓ {approve_item} approuvé manuellement")
            return

        # Charger proposals pending
        sql = """
            SELECT p.id, p.item_id, p.domain_id, p.family_l2_id,
                   p.subfamily_id, p.confidence, p.reason,
                   i.label_fr
            FROM couche_b.taxo_proposals_v2 p
            JOIN couche_b.procurement_dict_items i USING (item_id)
            WHERE p.status      = 'pending'
              AND p.taxo_version = %s
              AND i.human_validated = FALSE
        """
        params: list = [TAXO_VERSION]
        if domain_filter:
            sql    += " AND p.domain_id = %s"
            params.append(domain_filter)
        sql += " ORDER BY p.confidence DESC, p.domain_id"

        rows = conn.execute(sql, params).fetchall()
        logger.info(f"Proposals pending : {len(rows)}")

        auto_approved = 0
        review_list   = []

        for row in rows:
            conf     = float(row["confidence"])
            coherent = is_fk_coherent(
                row["domain_id"], row["family_l2_id"], l2_to_l1
            )
            residuel = row["subfamily_id"] == "DIVERS_NON_CLASSE"

            if conf >= SEUIL_AUTO_APPROVE and coherent and not residuel:
                if not dry_run:
                    with conn.transaction():
                        conn.execute("""
                            UPDATE couche_b.taxo_proposals_v2
                            SET status      = 'approved',
                                approved_by = %s,
                                approved_at = NOW(),
                                updated_at  = NOW()
                            WHERE id = %s
                        """, (ao_user_id, row["id"]))
                auto_approved += 1

            elif conf >= SEUIL_REVIEW and coherent and not residuel:
                review_list.append(row)

        if not dry_run:
            conn.commit()

        # Vérifier seed intacts
        seed_n = conn.execute("""
            SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items
            WHERE human_validated = TRUE AND active = TRUE
        """).fetchone()["n"]
        if seed_n != SEED_ATTENDU:
            sys.exit(
                f"⛔ STOP-V5 : seed {seed_n} ≠ {SEED_ATTENDU} après Phase B"
            )

        # Rapport
        print("\n" + "=" * 65)
        print(
            f"PHASE B — VALIDATION SEMI-AUTO "
            f"{'(DRY-RUN)' if dry_run else ''}"
        )
        print("=" * 65)
        print(f"  Auto-approuvées (conf ≥ {SEUIL_AUTO_APPROVE})    : "
              f"{auto_approved}")
        print(f"  Review AO requise (conf {SEUIL_REVIEW}–{SEUIL_AUTO_APPROVE}) : "
              f"{len(review_list)}")
        print(f"  Total traité                              : {len(rows)}")
        print(f"  AO actor_id tracé                         : "
              f"{'OUI (' + str(ao_user_id)[:8] + '...)' if ao_user_id else 'NON · dégradé'}")

        if review_list:
            print(f"\nFILE DE REVIEW AO ({len(review_list)} items · "
                  f"top 50 priorité) :")
            print(
                f"  {'ITEM_ID':<35} {'LABEL':<25} "
                f"{'L1':<14} {'L2':<18} CONF"
            )
            print("-" * 100)
            for r in review_list[:50]:
                print(
                    f"  {r['item_id']:<35} "
                    f"{str(r['label_fr'])[:22]:<25} "
                    f"{r['domain_id']:<14} "
                    f"{r['family_l2_id']:<18} "
                    f"{float(r['confidence']):.2f}"
                )
            if len(review_list) > 50:
                print(f"  ... et {len(review_list)-50} autres")
            print(f"\n  Pour approuver manuellement :")
            print(
                f"  python scripts/validate_taxo_batch.py "
                f"--approve-item <item_id>"
            )
        print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",       action="store_true")
    parser.add_argument("--domain",        type=str)
    parser.add_argument("--approve-item",  type=str)
    args = parser.parse_args()
    run(args.dry_run, args.domain, args.approve_item)
