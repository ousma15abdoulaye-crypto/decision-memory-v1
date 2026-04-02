"""Persistance JSONB — table m13_regulatory_profile_versions (migration 057)."""

from __future__ import annotations

import logging
from typing import Any

import psycopg.errors
from psycopg.types.json import Json

from src.db.core import get_connection

logger = logging.getLogger(__name__)

_MAX_INSERT_RETRIES = 5


def _is_rls_denied(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "row-level security" in msg or "violates row-level security" in msg


class M13RegulatoryProfileRepository:
    """Insert / lecture du dernier profil réglementaire par case."""

    def save_payload(
        self,
        *,
        case_id: str,
        payload: dict[str, Any],
        version: int | None = None,
    ) -> str | None:
        """Retourne l'id UUID inséré, ou None si erreur.

        Utilise ``get_connection()`` (contexte tenant RLS) — pas ``get_db_connection()``.
        En cas de course sur ``(case_id, version)``, réessaie après ``UniqueViolation``.
        """
        for attempt in range(_MAX_INSERT_RETRIES):
            try:
                with get_connection() as conn:
                    conn.execute(
                        "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM "
                        "public.m13_regulatory_profile_versions WHERE case_id = :cid",
                        {"cid": case_id},
                    )
                    row = conn.fetchone()
                    ver = int(row["v"]) if row and row["v"] is not None else 1
                    if version is not None:
                        ver = version
                    conn.execute(
                        """
                        INSERT INTO public.m13_regulatory_profile_versions
                        (case_id, version, payload)
                        VALUES (:case_id, :ver, :payload)
                        RETURNING id::text AS id
                        """,
                        {
                            "case_id": case_id,
                            "ver": ver,
                            "payload": Json(payload),
                        },
                    )
                    out = conn.fetchone()
                    return str(out["id"]) if out else None
            except psycopg.errors.UniqueViolation:
                if attempt + 1 >= _MAX_INSERT_RETRIES:
                    logger.warning(
                        "m13_regulatory_profile unique violation after %s retries",
                        _MAX_INSERT_RETRIES,
                    )
                    return None
                continue
            except Exception as exc:
                if _is_rls_denied(exc):
                    logger.error(
                        "m13_regulatory_profile RLS denied (check app.tenant_id / case): %s",
                        exc,
                    )
                else:
                    logger.warning("m13_regulatory_profile save failed: %s", exc)
                return None
        return None
