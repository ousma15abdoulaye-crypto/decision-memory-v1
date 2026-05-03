#!/usr/bin/env python3
"""
Import IMC PDF → DMS DB · INSTAT Mali matériaux construction Bamako.

Usage :
  python scripts/import_imc.py --dry-run
  python scripts/import_imc.py

Local-first · pdfplumber · zéro LlamaCloud.
"""

from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "imports" / "imc"


def main() -> int:
    import argparse

    from src.couche_b.imc.parser import parse_imc_pdf
    from src.couche_b.imc.repository import (
        insert_entries_batch,
        insert_source,
        source_exists_by_sha256,
        update_source_status,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Parse sans écriture DB")
    args = parser.parse_args()

    if not DATA_DIR.exists():
        logger.error("Dossier %s introuvable", DATA_DIR)
        return 1

    files = sorted(DATA_DIR.glob("*.pdf"))
    if not files:
        logger.error("Aucun PDF dans %s", DATA_DIR)
        return 1

    total_entries = 0
    total_files = 0
    errors = []

    for filepath in files:
        try:
            sha256 = hashlib.sha256(filepath.read_bytes()).hexdigest()
            if not args.dry_run and source_exists_by_sha256(sha256):
                logger.info("Déjà importé (cache) : %s", filepath.name)
                continue

            entries = parse_imc_pdf(filepath)
            if not entries:
                logger.warning("Aucune entrée extraite : %s", filepath.name)
                continue

            period = entries[0]["period_year"], entries[0]["period_month"]
            logger.info(
                "%s · %d catégories · %d-%02d", filepath.name, len(entries), *period
            )

            if args.dry_run:
                total_entries += len(entries)
                total_files += 1
                continue

            row = insert_source(
                sha256=sha256,
                filename=filepath.name,
                source_year=period[0],
                source_month=period[1],
            )
            source_id = row.get("id")
            if not source_id:
                errors.append(f"{filepath.name}: insert source failed")
                continue

            inserted, skipped = insert_entries_batch(source_id, entries)
            total = len(entries)
            status = (
                "success" if skipped == 0 else "partial" if inserted > 0 else "failed"
            )
            update_source_status(source_id, status)
            logger.info(
                "%s → status=%s · %d/%d insérés · %d skipped",
                filepath.name,
                status,
                inserted,
                total,
                skipped,
            )
            total_entries += inserted
            total_files += 1

        except Exception as e:
            logger.exception("Erreur %s", filepath.name)
            errors.append(f"{filepath.name}: {e}")

    logger.info("=" * 50)
    logger.info("Résumé : %d fichiers · %d entrées", total_files, total_entries)
    if errors:
        logger.warning("Erreurs : %d", len(errors))
        for err in errors[:5]:
            logger.warning("  %s", err)
    logger.info("=" * 50)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
