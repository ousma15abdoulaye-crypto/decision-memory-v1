"""Persistance JSONB — table evaluation_documents (migration 056+).

ADR-M14-001. Post-migration 074 : ``case_id`` supprimé — écriture via ``workspace_id``
résolu depuis ``process_workspaces.legacy_case_id`` ou ``process_workspaces.id``.
RLS tenant_scoped via cases (chemins legacy) / workspace.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
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

    def _resolve_committee_id(self, case_id: str) -> str | None:
        """Lookup le premier committee_id rattaché au case. None si absent."""
        try:
            with get_connection() as conn:
                conn.execute(
                    "SELECT committee_id::text AS cid FROM public.committees "
                    "WHERE case_id = :case_id LIMIT 1",
                    {"case_id": case_id},
                )
                row = conn.fetchone()
                return str(row["cid"]) if row else None
        except Exception as exc:
            logger.warning("committee_id lookup failed for case %s: %s", case_id, exc)
            return None

    def _resolve_workspace_id_for_case(self, case_id: str) -> str | None:
        """Résout process_workspaces.id depuis legacy_case_id ou UUID workspace."""
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    SELECT id::text AS wid FROM public.process_workspaces
                    WHERE legacy_case_id = :cid
                    LIMIT 1
                    """,
                    {"cid": case_id},
                )
                row = conn.fetchone()
                if row and row.get("wid"):
                    return str(row["wid"])
            try:
                uuid_mod.UUID(case_id)
            except ValueError:
                return None
            with get_connection() as conn:
                conn.execute(
                    """
                    SELECT id::text AS wid FROM public.process_workspaces
                    WHERE id = CAST(:cid AS uuid)
                    LIMIT 1
                    """,
                    {"cid": case_id},
                )
                row = conn.fetchone()
                return str(row["wid"]) if row and row.get("wid") else None
        except Exception as exc:
            logger.warning(
                "workspace_id resolve failed for case_id=%s: %s", case_id, exc
            )
            return None

    def save_evaluation(
        self,
        *,
        case_id: str,
        payload: dict[str, Any],
        committee_id: str | None = None,
        version: int | None = None,
    ) -> str | None:
        """Insère un nouveau draft. Retourne l'id UUID, ou None si erreur.

        ``committee_id`` est NOT NULL + FK en DB. Si non fourni, le repository
        résout le premier comité rattaché au case (table ``committees``).
        ``workspace_id`` est résolu via ``process_workspaces`` (legacy_case_id).
        """
        workspace_id = self._resolve_workspace_id_for_case(case_id)
        if workspace_id is None:
            logger.warning(
                "evaluation_documents save skipped: no workspace for case_id=%s",
                case_id,
            )
            return None

        cid = committee_id or self._resolve_committee_id(case_id)
        if cid is None:
            logger.warning(
                "evaluation_documents save skipped: no committee found for case %s",
                case_id,
            )
            return None

        for attempt in range(_MAX_INSERT_RETRIES):
            try:
                with get_connection() as conn:
                    conn.execute(
                        "SELECT COALESCE(MAX(version), 0) + 1 AS v "
                        "FROM public.evaluation_documents "
                        "WHERE workspace_id = CAST(:wid AS uuid)",
                        {"wid": workspace_id},
                    )
                    row = conn.fetchone()
                    ver = int(row["v"]) if row and row.get("v") is not None else 1
                    if version is not None:
                        ver = version
                    conn.execute(
                        """
                        INSERT INTO public.evaluation_documents
                        (workspace_id, committee_id, version, scores_matrix, status)
                        VALUES (
                            CAST(:workspace_id AS uuid),
                            CAST(:committee_id AS uuid),
                            :ver,
                            :payload,
                            'draft'
                        )
                        RETURNING id::text AS id
                        """,
                        {
                            "workspace_id": workspace_id,
                            "committee_id": cid,
                            "ver": ver,
                            "payload": Json(payload),
                        },
                    )
                    out = conn.fetchone()
                    return str(out["id"]) if out else None
            except psycopg.errors.UniqueViolation:
                if version is not None or attempt + 1 >= _MAX_INSERT_RETRIES:
                    logger.warning(
                        "evaluation_documents unique violation (version=%s, attempt=%s/%s)",
                        version,
                        attempt + 1,
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
        """Récupère le dernier résultat d'évaluation pour un case (clé API).

        ``case_id`` identifie le dossier logique ; la ligne DB est résolue via
        ``workspace_id``.
        """
        workspace_id = self._resolve_workspace_id_for_case(case_id)
        if workspace_id is None:
            return None
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    SELECT id::text AS id, version,
                           scores_matrix, justifications, status,
                           created_at
                    FROM public.evaluation_documents
                    WHERE workspace_id = CAST(:wid AS uuid)
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    {"wid": workspace_id},
                )
                row = conn.fetchone()
                if row is None:
                    return None
                result = dict(row)
                result["case_id"] = case_id
                ca = result.get("created_at")
                if ca is not None and not isinstance(ca, str):
                    result["created_at"] = (
                        ca.isoformat() if hasattr(ca, "isoformat") else str(ca)
                    )
                if result.get("scores_matrix") is None:
                    result["scores_matrix"] = {}
                if result.get("justifications") is None:
                    result["justifications"] = {}
                return result
        except Exception as exc:
            if _is_rls_denied(exc):
                logger.error("evaluation_documents get_latest RLS denied: %s", exc)
            else:
                logger.warning("evaluation_documents get_latest failed: %s", exc)
            return None

    def save_m14_audit(self, *, case_id: str, report: Any) -> None:
        """Écrit score_history et elimination_log (migration 059+). Append-only.

        Colonnes post-074 : ``workspace_id`` (plus de ``case_id`` sur ces tables).
        """
        workspace_id = self._resolve_workspace_id_for_case(case_id)
        if workspace_id is None:
            logger.warning(
                "save_m14_audit skipped: no workspace for case_id=%s", case_id
            )
            return

        data = (
            report.model_dump(mode="json") if hasattr(report, "model_dump") else report
        )
        offers = data.get("offer_evaluations") or []
        try:
            with get_connection() as conn:
                for offer in offers:
                    if not isinstance(offer, dict):
                        continue
                    oid = str(offer.get("offer_document_id") or "")
                    if not oid:
                        continue
                    ts = offer.get("technical_score") or {}
                    for c in ts.get("criteria_scores") or []:
                        if not isinstance(c, dict):
                            continue
                        ck = str(c.get("criteria_name") or "unknown")
                        conn.execute(
                            """
                            INSERT INTO public.score_history (
                                workspace_id, offer_document_id, criterion_key,
                                score_value, max_score, confidence, evidence, scored_by
                            ) VALUES (
                                CAST(:wid AS uuid), :oid, :ck,
                                :sv, :mx, :conf, :ev, 'system:m14'
                            )
                            """,
                            {
                                "wid": workspace_id,
                                "oid": oid,
                                "ck": ck,
                                "sv": c.get("awarded_score"),
                                "mx": c.get("max_score"),
                                "conf": float(c.get("confidence") or 0.6),
                                "ev": (c.get("justification") or "")[:8000],
                            },
                        )
                    for ev in offer.get("eligibility_results") or []:
                        if not isinstance(ev, dict):
                            continue
                        if not ev.get("is_eliminatory"):
                            continue
                        if ev.get("result") != "FAIL":
                            continue
                        reason = (
                            "; ".join(ev.get("evidence") or []) or "eliminatory_fail"
                        )
                        conn.execute(
                            """
                            INSERT INTO public.elimination_log (
                                workspace_id, offer_document_id,
                                check_id, check_name, reason
                            ) VALUES (
                                CAST(:wid AS uuid), :oid, :cid, :cname, :reason
                            )
                            """,
                            {
                                "wid": workspace_id,
                                "oid": oid,
                                "cid": str(ev.get("check_id") or ""),
                                "cname": str(ev.get("check_name") or ""),
                                "reason": reason[:8000],
                            },
                        )
        except Exception as exc:
            err = str(exc).lower()
            if "undefinedtable" in err or "does not exist" in err:
                logger.warning(
                    "save_m14_audit skipped (tables missing — run migration 059): %s",
                    exc,
                )
            elif _is_rls_denied(exc):
                logger.error("save_m14_audit RLS denied: %s", exc)
            else:
                logger.warning("save_m14_audit failed: %s", exc)
