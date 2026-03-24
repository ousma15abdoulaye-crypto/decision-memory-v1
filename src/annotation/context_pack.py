"""
Upstream context pack for annotation pipeline (Couche B read-only signals).

See: docs/contracts/annotation/UPSTREAM_CONTEXT_PACK_STANDARD.md
"""

from __future__ import annotations

import logging
import os
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PACK_VERSION = "1.0.0"


class UpstreamContextPack(BaseModel):
    """Read-only context for Pass 1+ (no PII by default)."""

    document_id: str = Field(..., min_length=1)
    case_id: str | None = None
    vendor_catalog_summary: dict[str, Any] = Field(default_factory=dict)
    mercuriale_summary: dict[str, Any] = Field(default_factory=dict)
    market_signal_hint: dict[str, Any] | None = None
    procurement_hints: list[str] = Field(default_factory=list)
    pack_version: str = PACK_VERSION
    sources_used: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


def _table_exists(cur, table: str, schema: str = "public") -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        LIMIT 1
        """,
        (schema, table),
    )
    return cur.fetchone() is not None


def resolve_case_id_for_document(document_id: str) -> str | None:
    """Return case_id for a DMS document id, or None if unknown / DB error."""
    if os.environ.get("ANNOTATION_CONTEXT_PACK_SKIP_DB", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return None
    try:
        from src.db.connection import get_db_cursor
    except ImportError:
        return None

    try:
        with get_db_cursor() as cur:
            if not _table_exists(cur, "documents"):
                return None
            cur.execute(
                "SELECT case_id FROM documents WHERE id = %s LIMIT 1",
                (document_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cid = row.get("case_id")
            return str(cid) if cid is not None else None
    except Exception:
        logger.debug("resolve_case_id_for_document failed", exc_info=True)
        return None


def build_upstream_context_pack(
    document_id: str,
    *,
    case_id: str | None = None,
    load_from_database: bool | None = None,
) -> UpstreamContextPack:
    """
    Assemble UpstreamContextPack.

    When load_from_database is True (default: True unless SKIP_DB env), runs
    aggregate read-only queries on vendor_identities and mercurials.
    """
    if load_from_database is None:
        load_from_database = os.environ.get(
            "ANNOTATION_CONTEXT_PACK_SKIP_DB", ""
        ).lower() not in ("1", "true", "yes", "on")

    cid = case_id
    if cid is None and load_from_database:
        cid = resolve_case_id_for_document(document_id)

    pack = UpstreamContextPack(
        document_id=document_id,
        case_id=cid,
        sources_used=[],
    )

    if not load_from_database:
        pack.sources_used = ["none"]
        return pack

    try:
        from src.db.connection import get_db_cursor
    except ImportError:
        pack.sources_used = ["none"]
        return pack

    try:
        with get_db_cursor() as cur:
            sources: list[str] = []

            if _table_exists(cur, "vendor_identities"):
                cur.execute(
                    "SELECT COUNT(*) AS c FROM vendor_identities WHERE is_active = TRUE"
                )
                row = cur.fetchone() or {}
                active_vendors = int(row.get("c") or 0)
                cur.execute(
                    "SELECT COUNT(DISTINCT region_code) AS c FROM vendor_identities "
                    "WHERE is_active = TRUE"
                )
                row2 = cur.fetchone() or {}
                regions = int(row2.get("c") or 0)
                pack.vendor_catalog_summary = {
                    "active_vendor_count": active_vendors,
                    "distinct_region_codes": regions,
                }
                sources.append("vendor_identities")

            if _table_exists(cur, "mercurials"):
                cur.execute("SELECT COUNT(*) AS c FROM mercurials")
                row = cur.fetchone() or {}
                mcount = int(row.get("c") or 0)
                cur.execute("SELECT MAX(year) AS y FROM mercurials")
                row2 = cur.fetchone() or {}
                latest_year = row2.get("y")
                pack.mercuriale_summary = {
                    "mercurial_row_count": mcount,
                    "latest_year": int(latest_year) if latest_year is not None else None,
                }
                sources.append("mercurials")

            pack.procurement_hints = [
                "Couche B context is non-prescriptive — no winner/rank/recommendation.",
            ]
            pack.market_signal_hint = None
            pack.sources_used = sources if sources else ["none"]
    except Exception:
        logger.warning("build_upstream_context_pack DB aggregate failed", exc_info=True)
        pack.sources_used = ["none"]

    return pack
