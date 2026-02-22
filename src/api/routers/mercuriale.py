"""
Router FastAPI -- mercuriale -- DMS V3.3.2

Couche B uniquement -- Market Survey / memoire.
Zero import Couche A. Zero influence scoring.
ADR-0002 strict : SQL parametre, psycopg v3, get_db_cursor standard.
"""

from __future__ import annotations

import json

from fastapi import APIRouter

from src.couche_b.mercuriale.parser import parse_batch
from src.couche_b.mercuriale.schemas import (
    MercurialeParsedLine,
    MercurialeParseRequest,
)
from src.db.connection import get_db_cursor

router = APIRouter(prefix="/mercuriale", tags=["mercuriale"])

_TABLE_RAW_QUEUE = "couche_b.mercuriale_raw_queue"

_INSERT_RAW_QUEUE = """
    INSERT INTO couche_b.mercuriale_raw_queue (
        raw_line, source, parse_status,
        designation_raw, unite_raw,
        price_min, price_avg, price_max,
        currency, item_id, strategy, score, parse_errors
    ) VALUES (
        %(raw_line)s, %(source)s, %(parse_status)s,
        %(designation_raw)s, %(unite_raw)s,
        %(price_min)s, %(price_avg)s, %(price_max)s,
        %(currency)s, %(item_id)s, %(strategy)s, %(score)s,
        %(parse_errors)s::jsonb
    )
"""

_CHECK_TABLE = """
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'couche_b'
      AND table_name = 'mercuriale_raw_queue'
"""


def _table_exists(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute(_CHECK_TABLE)
        return cur.fetchone() is not None


def _persist(conn, results: list[MercurialeParsedLine], source: str | None) -> None:
    """Insere les resultats dans couche_b.mercuriale_raw_queue si la table existe."""
    if not _table_exists(conn):
        return
    with conn.cursor() as cur:
        for r in results:
            norm = r.normalisation
            cur.execute(
                _INSERT_RAW_QUEUE,
                {
                    "raw_line": r.raw_line,
                    "source": source,
                    "parse_status": str(r.status),
                    "designation_raw": r.designation_raw,
                    "unite_raw": r.unite_raw,
                    "price_min": r.price_min,
                    "price_avg": r.price_avg,
                    "price_max": r.price_max,
                    "currency": r.currency,
                    "item_id": norm.item_id if norm else None,
                    "strategy": str(norm.strategy) if norm else None,
                    "score": float(norm.score) if norm else None,
                    "parse_errors": json.dumps(r.parse_errors),
                },
            )


@router.post("/parse", response_model=list[MercurialeParsedLine])
def parse_mercuriale(body: MercurialeParseRequest) -> list[MercurialeParsedLine]:
    """
    Parse une liste de lignes brutes mercuriale.
    persist=true -> ecrit dans couche_b.mercuriale_raw_queue (si table existe).
    Interdit : ecrire dans procurement_dict_*.
    """
    with get_db_cursor() as cur:
        conn = cur.connection
        results = parse_batch(raw_lines=body.lines, conn=conn, source=body.source)
        if body.persist:
            _persist(conn, results, body.source)
        return results
