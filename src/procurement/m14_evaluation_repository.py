"""Persistance JSONB — table evaluation_documents (migration 056).

ADR-M14-001. Versionnement (case_id, version). RLS tenant_scoped via cases.
"""

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


class M14EvaluationRepository:
    """CRUD sur evaluation_documents (migration 056)."""

    def save_evaluation(
        self,
        *,
        case_id: str,
        payload: dict[str, Any],
        committee_id: str | None = None,
        version: int | None = None,
    ) -> str | None:
        """Insère un nouveau draft. Retourne l'id UUID, ou None si erreur.

        ``committee_id`` est NOT NULL en DB, mais M14 le positionne à un UUID
        sentinel si non fourni (le comité humain met à jour après scellement).
        """
        sentinel_committee = "00000000-0000-0000-0000-000000000000"
        cid = committee_id or sentinel_committee

        for attempt in range(_MAX_INSERT_RETRIES):
            try:
                with get_connection() as conn:
                    conn.execute(
                        "SELECT COALESCE(MAX(version), 0) + 1 AS v "
                        "FROM public.evaluation_documents WHERE case_id = :cid",
                        {"cid": case_id},
                    )
                    row = conn.fetchone()
                    ver = int(row["v"]) if row and row.get("v") is not None else 1
                    if version is not None:
                        ver = version
                    conn.execute(
                        """
                        INSERT INTO public.evaluation_documents
                        (case_id, committee_id, version, scores_matrix, status)
                        VALUES (:case_id, :committee_id::uuid, :ver, :payload, 'draft')
                        RETURNING id::text AS id
                        """,
                        {
                            "case_id": case_id,
                            "committee_id": cid,
                            "ver": ver,
                            "payload": Json(payload),
                        },
                    )
                    out = conn.fetchone()
                    return str(out["id"]) if out else None
            except psycopg.errors.UniqueViolation:
                if attempt + 1 >= _MAX_INSERT_RETRIES:
                    logger.warning(
                        "evaluation_documents unique violation after %s retries",
                        _MAX_INSERT_RETRIES,
                    )
                    return None
                continue
            except Exception as exc:
                if _is_rls_denied(exc):
                    logger.error(
                        "evaluation_documents RLS denied (check app.tenant_id / case): %s",
                        exc,
                    )
                else:
                    logger.warning("evaluation_documents save failed: %s", exc)
                return None
        return None

    def get_latest(self, *, case_id: str) -> dict[str, Any] | None:
        """Récupère le dernier résultat d'évaluation pour un case."""
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    SELECT id::text AS id, case_id, version,
                           scores_matrix, justifications, status,
                           created_at
                    FROM public.evaluation_documents
                    WHERE case_id = :case_id
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    {"case_id": case_id},
                )
                row = conn.fetchone()
                return dict(row) if row else None
        except Exception as exc:
            if _is_rls_denied(exc):
                logger.error("evaluation_documents get_latest RLS denied: %s", exc)
            else:
                logger.warning("evaluation_documents get_latest failed: %s", exc)
            return None
