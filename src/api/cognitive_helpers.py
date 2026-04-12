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
from src.services.evaluation_document_query import (
    LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE,
    fetch_latest_evaluation_document_for_workspace,
)

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
        r = fetch_latest_evaluation_document_for_workspace(
            conn,
            workspace_id,
            columns="scores_matrix",
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
        overall = float(r["mn"]) if r and r["mn"] is not None else 0.0
    except Exception as exc:
        logger.debug("[cognitive] confidence_summary_for_workspace fallback: %s", exc)
        overall = 0.0
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


async def async_load_cognitive_facts(db: Any, workspace_row: Any) -> CognitiveFacts:
    """Version async de load_cognitive_facts — pour AsyncpgAdapter.

    Utilisée par workspace_status_handler (agent) qui opère sur le pool
    asyncpg. Les appels sync db_execute_one() seraient incompatibles avec
    AsyncpgAdapter (execute/fetchone sync absents).
    """
    wid = str(workspace_row["id"])
    st = workspace_row.get("status") or "draft"

    # has_source_package
    try:
        r = await db.fetch_val(
            "SELECT EXISTS(SELECT 1 FROM source_package_documents "
            "WHERE workspace_id = :ws) AS e",
            {"ws": wid},
        )
        has_sp = bool(r)
    except Exception as exc:
        logger.debug("[cognitive-async] has_source_package fallback: %s", exc)
        has_sp = False

    # bundle_stats
    try:
        r = await db.fetch_one(
            "SELECT COUNT(*)::int AS n, "
            "COALESCE(BOOL_AND(qualification_status = 'qualified'), TRUE) AS all_q "
            "FROM supplier_bundles WHERE workspace_id = :ws",
            {"ws": wid},
        )
        if not r:
            n, all_q = 0, True
        else:
            n, all_q = int(r["n"]), bool(r["all_q"])
    except Exception as exc:
        logger.debug("[cognitive-async] bundle_stats fallback: %s", exc)
        try:
            r = await db.fetch_one(
                "SELECT COUNT(*)::int AS n, "
                "COALESCE(BOOL_AND(bundle_status = 'complete'), TRUE) AS all_q "
                "FROM supplier_bundles WHERE workspace_id = :ws",
                {"ws": wid},
            )
            n, all_q = (int(r["n"]), bool(r["all_q"])) if r else (0, True)
        except Exception:
            n, all_q = 0, True

    # evaluation_frame_complete
    try:
        r = await db.fetch_one(
            "SELECT scores_matrix FROM evaluation_documents "
            "WHERE workspace_id = CAST(:ws AS uuid) "
            f"{LATEST_EVALUATION_DOCUMENT_ORDER_CLAUSE} LIMIT 1",
            {"ws": wid},
        )
        ef = bool(r and r.get("scores_matrix"))
    except Exception:
        ef = False

    return CognitiveFacts(
        workspace_status=st,
        has_source_package=has_sp,
        bundle_count=n,
        bundles_all_qualified=all_q,
        evaluation_frame_complete=ef,
    )


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
