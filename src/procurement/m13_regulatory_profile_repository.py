"""Persistance JSONB — table m13_regulatory_profile_versions (migration 057)."""

from __future__ import annotations

import logging
from typing import Any

from psycopg.types.json import Json

from src.db.core import get_db_connection

logger = logging.getLogger(__name__)


class M13RegulatoryProfileRepository:
    """Insert / lecture du dernier profil réglementaire par case."""

    def save_payload(
        self,
        *,
        case_id: str,
        payload: dict[str, Any],
        version: int | None = None,
    ) -> str | None:
        """Retourne l'id UUID inséré, ou None si erreur."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COALESCE(MAX(version), 0) + 1 FROM "
                        "public.m13_regulatory_profile_versions WHERE case_id = %s",
                        (case_id,),
                    )
                    row = cur.fetchone()
                    ver = int(row[0]) if row and row[0] is not None else 1
                    if version is not None:
                        ver = version
                    cur.execute(
                        """
                        INSERT INTO public.m13_regulatory_profile_versions
                        (case_id, version, payload)
                        VALUES (%s, %s, %s)
                        RETURNING id::text
                        """,
                        (case_id, ver, Json(payload)),
                    )
                    out = cur.fetchone()
                    return str(out[0]) if out else None
        except Exception as exc:
            logger.warning("m13_regulatory_profile save skipped: %s", exc)
            return None
