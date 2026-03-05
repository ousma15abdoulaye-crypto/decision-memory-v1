"""
Repository IMC — DMS V4.1.0
SQL brut · psycopg via get_connection · zéro ORM
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.core import get_connection

logger = logging.getLogger(__name__)


def source_exists_by_sha256(sha256: str) -> bool:
    with get_connection() as conn:
        conn.execute(
            "SELECT id FROM imc_sources WHERE sha256 = %(sha256)s",
            {"sha256": sha256},
        )
        row = conn.fetchone()
    return row is not None


def insert_source(
    sha256: str,
    filename: str,
    source_year: int,
    source_month: int | None,
    parse_method: str = "native_pdf",
) -> dict[str, Any]:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO imc_sources (
                sha256, filename, source_year, source_month,
                parse_method, parse_status
            ) VALUES (
                %(sha256)s, %(filename)s, %(source_year)s, %(source_month)s,
                %(parse_method)s, 'pending'
            )
            ON CONFLICT (sha256) DO UPDATE SET
                filename = EXCLUDED.filename,
                source_year = EXCLUDED.source_year,
                source_month = EXCLUDED.source_month
            RETURNING id, sha256, filename, source_year, source_month
            """,
            {
                "sha256": sha256,
                "filename": filename,
                "source_year": source_year,
                "source_month": source_month,
                "parse_method": parse_method,
            },
        )
        row = conn.fetchone()
        conn.commit()
    return row or {}


def update_source_status(source_id: str, status: str) -> None:
    """
    Met à jour le statut de parsing d'une source IMC.
    Statuts valides : pending · success · partial · failed
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE imc_sources
            SET parse_status = %(status)s
            WHERE id = %(source_id)s
            """,
            {"status": status, "source_id": source_id},
        )
        conn.commit()


def insert_entries_batch(
    source_id: str,
    entries: list[dict[str, Any]],
) -> tuple[int, int]:
    """
    Insère les entrées IMC en batch.
    Retourne (inserted, skipped).
    Si skipped > 0 → l'appelant marque la source 'partial'.
    Si inserted == 0 → l'appelant marque la source 'failed'.
    """
    inserted = 0
    skipped = 0
    with get_connection() as conn:
        for e in entries:
            try:
                conn.execute(
                    """
                    INSERT INTO imc_entries (
                        source_id, category_raw, category_normalized,
                        period_year, period_month,
                        index_value, variation_mom, variation_yoy,
                        review_required
                    ) VALUES (
                        %(source_id)s, %(category_raw)s, %(category_normalized)s,
                        %(period_year)s, %(period_month)s,
                        %(index_value)s, %(variation_mom)s, %(variation_yoy)s,
                        %(review_required)s
                    )
                    ON CONFLICT (source_id, category_raw, period_year, period_month)
                    DO UPDATE SET
                        index_value = EXCLUDED.index_value,
                        variation_mom = EXCLUDED.variation_mom,
                        variation_yoy = EXCLUDED.variation_yoy
                    """,
                    {
                        "source_id": source_id,
                        "category_raw": e["category_raw"],
                        "category_normalized": e.get("category_normalized"),
                        "period_year": e["period_year"],
                        "period_month": e["period_month"],
                        "index_value": (
                            float(e["index_value"])
                            if e.get("index_value") is not None
                            else None
                        ),
                        "variation_mom": (
                            float(e["variation_mom"])
                            if e.get("variation_mom") is not None
                            else None
                        ),
                        "variation_yoy": (
                            float(e["variation_yoy"])
                            if e.get("variation_yoy") is not None
                            else None
                        ),
                        "review_required": e.get("review_required", False),
                    },
                )
                inserted += 1
            except Exception as exc:
                logger.warning(
                    "Entrée ignorée · category='%s' · %s/%s · %s",
                    e.get("category_raw", "?"),
                    e.get("period_year"),
                    e.get("period_month"),
                    exc,
                )
                skipped += 1
        conn.commit()
    return inserted, skipped
