"""Chargement de faits cognitifs depuis la DB (BLOC5)."""

from __future__ import annotations

import logging
from typing import Any

from src.cognitive.cognitive_state import CognitiveFacts
from src.cognitive.confidence_envelope import (
    build_envelope_from_overall,
    regime_from_overall,
)
from src.db import db_execute_one

logger = logging.getLogger(__name__)


def safe_has_source_package(conn, workspace_id: str) -> bool:
    try:
        r = db_execute_one(
            conn,
            """
            SELECT EXISTS(
                SELECT 1 FROM source_package_documents WHERE workspace_id = :ws
            ) AS e
            """,
            {"ws": workspace_id},
        )
        return bool(r and r.get("e"))
    except Exception as exc:
        logger.debug("[cognitive] has_source_package fallback: %s", exc)
        return False


def bundle_stats(conn, workspace_id: str) -> tuple[int, bool]:
    """(bundle_count, bundles_all_qualified)."""

    try:
        r = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n,
                   COALESCE(BOOL_AND(qualification_status = 'qualified'), TRUE) AS all_q
            FROM supplier_bundles
            WHERE workspace_id = :ws
            """,
            {"ws": workspace_id},
        )
        if not r:
            return 0, True
        return int(r["n"]), bool(r["all_q"])
    except Exception as exc:
        logger.debug("[cognitive] bundle_stats fallback: %s", exc)
        r2 = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n,
                   COALESCE(BOOL_AND(bundle_status = 'complete'), TRUE) AS all_q
            FROM supplier_bundles
            WHERE workspace_id = :ws
            """,
            {"ws": workspace_id},
        )
        if not r2:
            return 0, True
        return int(r2["n"]), bool(r2["all_q"])


def evaluation_frame_complete(conn, workspace_id: str) -> bool:
    try:
        r = db_execute_one(
            conn,
            """
            SELECT scores_matrix
            FROM evaluation_documents
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"ws": workspace_id},
        )
        if not r:
            return False
        sm = r.get("scores_matrix") or {}
        return bool(sm)
    except Exception:
        return False


def load_cognitive_facts(conn, workspace_row: dict[str, Any]) -> CognitiveFacts:
    wid = str(workspace_row["id"])
    st = workspace_row.get("status") or "draft"
    has_sp = safe_has_source_package(conn, wid)
    n, all_q = bundle_stats(conn, wid)
    ef = evaluation_frame_complete(conn, wid)
    return CognitiveFacts(
        workspace_status=st,
        has_source_package=has_sp,
        bundle_count=n,
        bundles_all_qualified=all_q,
        evaluation_frame_complete=ef,
    )


def confidence_summary_for_workspace(conn, workspace_id: str) -> dict[str, Any]:
    """Agrège system_confidence des bundle_documents (min) pour l’enveloppe."""

    try:
        r = db_execute_one(
            conn,
            """
            SELECT MIN(system_confidence) AS mn
            FROM bundle_documents
            WHERE workspace_id = :ws
            """,
            {"ws": workspace_id},
        )
        overall = float(r["mn"]) if r and r["mn"] is not None else 1.0
    except Exception:
        overall = 1.0
    env = build_envelope_from_overall(overall)
    reg = regime_from_overall(env.overall)
    warn = None
    if reg == "yellow":
        warn = "Confiance globale sous le seuil vert (≥ 0.8)."
    elif reg == "red":
        warn = "Confiance bloquante — validation HITL requise."
    return {
        "overall": env.overall,
        "regime": reg,
        "display_warning": warn,
    }


def map_committee_session_row(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {
            "session_id": None,
            "status": "no_session",
            "opened_at": None,
            "sealed_at": None,
        }
    st = row.get("session_status") or "draft"
    if st == "active":
        api_status = "draft"
    else:
        api_status = st
    return {
        "session_id": str(row["id"]),
        "status": api_status,
        "opened_at": row.get("activated_at"),
        "sealed_at": row.get("sealed_at"),
    }
