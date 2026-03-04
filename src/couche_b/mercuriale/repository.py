"""
Repository mercuriale — DMS V4.1.0
SQL brut · psycopg v3 via _ConnectionWrapper · zéro ORM

API _ConnectionWrapper (src/db/core.py) :
  execute(sql, params_dict) → None  (pas chainable)
  fetchone()  → dict | None
  fetchall()  → list[dict]
  commit()    · rollback()
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.db.core import get_connection

logger = logging.getLogger(__name__)


def source_exists_by_sha256(sha256: str) -> bool:
    with get_connection() as conn:
        conn.execute(
            "SELECT id FROM mercuriale_sources WHERE sha256 = %(sha256)s",
            {"sha256": sha256},
        )
        row = conn.fetchone()
    return row is not None


def insert_source(data: dict[str, Any]) -> dict[str, Any]:
    """INSERT idempotent ON CONFLICT sha256 DO NOTHING."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO mercuriale_sources (
                filename, sha256, year,
                source_type, extraction_engine, notes
            ) VALUES (
                %(filename)s, %(sha256)s, %(year)s,
                %(source_type)s, %(extraction_engine)s, %(notes)s
            )
            ON CONFLICT (sha256) DO NOTHING
            RETURNING *
            """,
            data,
        )
        row = conn.fetchone()
        conn.commit()
    return row if row else {}


def update_source_status(
    source_id: str,
    status: str,
    row_count: int | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE mercuriale_sources
            SET parse_status = %(status)s,
                row_count    = COALESCE(%(row_count)s, row_count)
            WHERE id = %(source_id)s
            """,
            {"status": status, "row_count": row_count, "source_id": source_id},
        )
        conn.commit()


def resolve_zone_id(zone_raw: str) -> str | None:
    """
    Résout zone_raw → geo_master.id.
    1 connexion · exact match d'abord · contains match ensuite.
    LIMIT 2 pour détecter les ambiguïtés.
    Retourne str si résolution unique · None sinon.
    """
    with get_connection() as conn:
        # Exact match
        conn.execute(
            """
            SELECT id FROM geo_master
            WHERE name ILIKE %(zone_raw)s
            ORDER BY level
            LIMIT 2
            """,
            {"zone_raw": zone_raw},
        )
        rows = conn.fetchall()

        if len(rows) == 1:
            return str(rows[0]["id"])

        if len(rows) == 0:
            # Contains match dans la même connexion
            conn.execute(
                """
                SELECT id FROM geo_master
                WHERE name ILIKE %(zone_pattern)s
                ORDER BY level
                LIMIT 2
                """,
                {"zone_pattern": f"%{zone_raw}%"},
            )
            rows = conn.fetchall()

            if len(rows) == 1:
                return str(rows[0]["id"])

    if len(rows) > 1:
        logger.warning(
            "Zone ambiguë : '%s' → %d résultats · zone_id = NULL",
            zone_raw,
            len(rows),
        )
    else:
        logger.warning(
            "Zone non résolue : '%s' → 0 résultat · zone_id = NULL",
            zone_raw,
        )
    return None


def insert_mercurial_lines_batch(
    lines: list[dict[str, Any]],
    batch_size: int = 500,
) -> int:
    """
    Insert par batch · 1 transaction par batch.
    unit_price = price_avg (enforced ici aussi).
    """
    if not lines:
        return 0

    inserted = 0
    with get_connection() as conn:
        for i in range(0, len(lines), batch_size):
            batch = lines[i : i + batch_size]
            for line in batch:
                metadata = line.get("extraction_metadata", {})
                if isinstance(metadata, dict):
                    metadata = json.dumps(metadata)

                conn.execute(
                    """
                    INSERT INTO mercurials (
                        source_id, item_code, item_canonical, group_label,
                        price_min, price_avg, price_max, unit_price,
                        currency, unit_raw, zone_raw, zone_id, year,
                        confidence, review_required, extraction_metadata
                    ) VALUES (
                        %(source_id)s, %(item_code)s, %(item_canonical)s,
                        %(group_label)s,
                        %(price_min)s, %(price_avg)s, %(price_max)s,
                        %(price_avg)s,
                        %(currency)s, %(unit_raw)s, %(zone_raw)s,
                        %(zone_id)s, %(year)s,
                        %(confidence)s, %(review_required)s,
                        %(extraction_metadata)s
                    )
                    """,
                    {**line, "extraction_metadata": metadata},
                )

            inserted += len(batch)
            logger.info(
                "Batch %d · %d lignes insérées",
                i // batch_size + 1,
                len(batch),
            )

        conn.commit()

    return inserted
