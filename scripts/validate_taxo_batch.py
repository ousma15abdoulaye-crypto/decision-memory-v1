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
    $env:AO_USER_ID     = "<id AO dans users — INTEGER ou UUID selon public.users.id>"

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
import uuid
from typing import Optional, Union

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s"
)

SEUIL_AUTO_APPROVE = 0.90
SEUIL_REVIEW = 0.75
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


def _probe_users_id_type(conn: psycopg.Connection) -> str:
    """Retourne le data_type normalisé de public.users.id (ex: 'integer', 'uuid').
    Interrompt le script si la table ou la colonne est introuvable.
    Utilise un curseur dict_row explicite pour ne pas dépendre du row_factory
    de la connexion parente.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        row = cur.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'users'
              AND column_name  = 'id'
        """).fetchone()
    if row is None:
        sys.exit(
            "⛔ DA-AUDIT : public.users.id introuvable — "
            "impossible de résoudre le type de AO_USER_ID"
        )
    return row["data_type"].lower()


def resolve_ao_user_id(
    conn: psycopg.Connection,
    dry_run: bool,
) -> Union[int, uuid.UUID, None]:
    """DA-AUDIT : résout AO_USER_ID selon le type réel de public.users.id.

    Comportement :
      - dry-run + absent → None (simulation sans écriture)
      - live    + absent → sys.exit (approved_by NULL interdit par DA-AUDIT)
      - présent          → cast en INTEGER ou uuid.UUID selon information_schema
    """
    raw = os.environ.get("AO_USER_ID")
    if not raw:
        if dry_run:
            logger.info("AO_USER_ID absent · dry-run · actor_id non appliqué")
            return None
        sys.exit(
            "❌ AO_USER_ID obligatoire pour toute écriture d'audit (DA-AUDIT) — "
            "relancez avec --dry-run ou définissez AO_USER_ID"
        )

    id_type = _probe_users_id_type(conn)
    if id_type == "uuid":
        try:
            return uuid.UUID(raw)
        except ValueError:
            sys.exit(
                f"❌ AO_USER_ID '{raw}' invalide — " f"public.users.id est de type UUID"
            )
    else:
        try:
            return int(raw)
        except ValueError:
            sys.exit(
                f"❌ AO_USER_ID '{raw}' invalide — "
                f"public.users.id est de type {id_type} (entier attendu)"
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
    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:

        ao_user_id = resolve_ao_user_id(conn, dry_run)
        l2_to_l1 = load_taxonomy_fk(conn)

        # Mode approbation manuelle d'un item spécifique
        if approve_item:
            if dry_run:
                print(f"DRY-RUN · approbation {approve_item} simulée")
                return
            with conn.transaction():
                conn.execute(
                    """
                    UPDATE couche_b.taxo_proposals_v2
                    SET status      = 'approved',
                        approved_by = %s,
                        approved_at = NOW(),
                        reviewed_by = %s,
                        updated_at  = NOW()
                    WHERE item_id      = %s
                      AND taxo_version = %s
                      AND status       = 'pending'
                """,
                    (ao_user_id, ao_user_id, approve_item, TAXO_VERSION),
                )
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
            sql += " AND p.domain_id = %s"
            params.append(domain_filter)
        sql += " ORDER BY p.confidence DESC, p.domain_id"

        rows = conn.execute(sql, params).fetchall()
        logger.info(f"Proposals pending : {len(rows)}")

        auto_approved = 0
        review_list = []

        for row in rows:
            conf = float(row["confidence"])
            coherent = is_fk_coherent(row["domain_id"], row["family_l2_id"], l2_to_l1)
            residuel = row["subfamily_id"] == "DIVERS_NON_CLASSE"

            if conf >= SEUIL_AUTO_APPROVE and coherent and not residuel:
                if not dry_run:
                    with conn.transaction():
                        conn.execute(
                            """
                            UPDATE couche_b.taxo_proposals_v2
                            SET status      = 'approved',
                                approved_by = %s,
                                approved_at = NOW(),
                                updated_at  = NOW()
                            WHERE id = %s
                        """,
                            (ao_user_id, row["id"]),
                        )
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
            sys.exit(f"⛔ STOP-V5 : seed {seed_n} ≠ {SEED_ATTENDU} après Phase B")

        # Rapport
        print("\n" + "=" * 65)
        print(f"PHASE B — VALIDATION SEMI-AUTO " f"{'(DRY-RUN)' if dry_run else ''}")
        print("=" * 65)
        print(
            f"  Auto-approuvées (conf ≥ {SEUIL_AUTO_APPROVE})    : " f"{auto_approved}"
        )
        print(
            f"  Review AO requise (conf {SEUIL_REVIEW}–{SEUIL_AUTO_APPROVE}) : "
            f"{len(review_list)}"
        )
        print(f"  Total traité                              : {len(rows)}")
        print(
            f"  AO actor_id tracé                         : "
            f"{'OUI (' + str(ao_user_id)[:8] + '...)' if ao_user_id else 'NON · dégradé'}"
        )

        if review_list:
            print(
                f"\nFILE DE REVIEW AO ({len(review_list)} items · "
                f"top 50 priorité) :"
            )
            print(f"  {'ITEM_ID':<35} {'LABEL':<25} " f"{'L1':<14} {'L2':<18} CONF")
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
                f"  python scripts/validate_taxo_batch.py " f"--approve-item <item_id>"
            )
        print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--domain", type=str)
    parser.add_argument("--approve-item", type=str)
    args = parser.parse_args()
    run(args.dry_run, args.domain, args.approve_item)
