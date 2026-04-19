#!/usr/bin/env python3
"""Backfill ``criterion_assessments.dao_criterion_id`` (résolution M16 / pg_trgm).

One-shot aligné sur ``resolve_criterion_id_sync`` (même logique que le bridge M14).

Usage::
    python scripts/backfill_dao_criterion_ids.py --workspace-id <UUID> [--dry-run]

Ne remplace pas une migration Alembic : met à jour les données existantes uniquement.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_dao_criterion_ids")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from src.db import db_execute, db_fetchall, get_connection
    from src.db.tenant_context import reset_rls_request_context, set_rls_is_admin
    from src.services.m16_backfill import resolve_criterion_id_sync

    wid = args.workspace_id.strip()
    set_rls_is_admin(True)
    try:
        with get_connection() as conn:
            crit_rows = db_fetchall(
                conn,
                """
                SELECT id::text AS id, m16_criterion_code, critere_nom, categorie
                FROM dao_criteria
                WHERE workspace_id = CAST(:wid AS uuid)
                """,
                {"wid": wid},
            )
            rows = db_fetchall(
                conn,
                """
                SELECT id::text AS id, criterion_key
                FROM criterion_assessments
                WHERE workspace_id = CAST(:wid AS uuid)
                  AND dao_criterion_id IS NULL
                """,
                {"wid": wid},
            )
            trgm_cache: dict[str, str | None] = {}
            updated = 0
            for row in rows:
                ck = str(row.get("criterion_key") or "")
                cid = resolve_criterion_id_sync(conn, wid, ck, crit_rows, trgm_cache)
                if not cid:
                    logger.debug("Non résolu criterion_key=%r", ck)
                    continue
                updated += 1
                if args.dry_run:
                    continue
                db_execute(
                    conn,
                    """
                    UPDATE criterion_assessments
                    SET dao_criterion_id = :cid, updated_at = NOW()
                    WHERE id = CAST(:id AS uuid)
                    """,
                    {"cid": cid, "id": row["id"]},
                )
            logger.info(
                "Lignes résolues=%d (dry_run=%s, total_null_scanné=%d)",
                updated,
                args.dry_run,
                len(rows),
            )
    finally:
        reset_rls_request_context()


if __name__ == "__main__":
    main()
