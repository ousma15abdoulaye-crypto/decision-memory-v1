# scripts/seed_classification_backfill.py
"""
Backfill classification_confidence sur procurement_dict_items
depuis taxo_proposals_v2 (status = 'approved').

HORS MIGRATION : DML interdit dans Alembic (doctrine migration-checklist.md)
Exécution manuelle APRÈS alembic upgrade head.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/seed_classification_backfill.py

    # Dry-run (lecture seule · RÈGLE-42) :
    python scripts/seed_classification_backfill.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("❌ DATABASE_URL manquante")


def run(dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "RÉEL"
    print(f"{'='*60}")
    print(f"BACKFILL classification_confidence · {mode}")
    print(f"{'='*60}")

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:

        # Probe · colonnes existantes avant tout
        cols = conn.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'classification_confidence'
        """).fetchone()

        if not cols:
            sys.exit(
                "❌ Colonne classification_confidence absente. "
                "Lancer alembic upgrade head d'abord."
            )

        # Compter les lignes à mettre à jour
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM couche_b.procurement_dict_items p
            JOIN (
                SELECT item_id, confidence,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY created_at DESC) AS rn
                FROM couche_b.taxo_proposals_v2
                WHERE status = 'approved'
            ) t ON p.item_id = t.item_id AND t.rn = 1
            WHERE p.classification_confidence IS NULL OR p.classification_source IS NULL
        """).fetchone()

        print(f"  Lignes à mettre à jour : {r['n']}")

        if dry_run:
            print("  DRY-RUN · aucune écriture")
            print(f"{'='*60}")
            return

        if r["n"] == 0:
            print("  Rien à faire · déjà backfillé ou aucun approved")
            print(f"{'='*60}")
            return

        # Backfill idempotent
        with conn.transaction():
            result = conn.execute("""
                UPDATE couche_b.procurement_dict_items p
                SET classification_confidence = t.confidence,
                    classification_source    = 'taxo_proposals_v2'
                FROM (
                    SELECT item_id, confidence,
                           ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY created_at DESC) AS rn
                    FROM couche_b.taxo_proposals_v2
                    WHERE status = 'approved'
                ) t
                WHERE p.item_id = t.item_id
                  AND t.rn = 1
                  AND (p.classification_confidence IS NULL OR p.classification_source IS NULL)
            """)
            updated = result.rowcount

        print(f"  Lignes mises à jour : {updated}")
        print("  ✓ Backfill terminé")
        print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.dry_run)
