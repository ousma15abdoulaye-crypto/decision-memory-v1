"""Scellement IRR — logique partagée PATCH workspace sealed et POST committee/seal.

Voir docs/adr/ADR-V51-WORKSPACE-SEAL-VS-COMMITTEE-PV.md (Option A).

Les appelants doivent avoir validé ``validate_transition`` vers ``sealed`` lorsque applicable.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from fastapi import status as http_status

from src.db import db_execute, db_execute_one, db_fetchall
from src.services.pv_builder import build_pv_snapshot
from src.services.seal_checks import run_all_seal_checks
from src.utils.json_utils import safe_json_dumps

logger = logging.getLogger(__name__)

_COMMITTEE_ROLES: frozenset[str] = frozenset(
    {
        "supply_chain",
        "finance",
        "budget_holder",
        "technical",
        "security",
        "pharma",
        "observer",
        "secretary",
    }
)

_LEGACY_ROLE_MAP: dict[str, str] = {
    "committee_chair": "supply_chain",
    "committee_member": "supply_chain",
    "procurement_lead": "supply_chain",
    "technical_reviewer": "technical",
    "finance_reviewer": "finance",
    "auditor": "admin",
}


def workspace_role_to_committee_role(ws_role: str) -> str:
    r = _LEGACY_ROLE_MAP.get(ws_role, ws_role)
    if r in _COMMITTEE_ROLES:
        return r
    if r == "admin":
        return "observer"
    return "observer"


def _open_committee_session_auto(
    conn: Any, workspace_id: str, tenant_id: str, user_id: int
) -> None:
    session_id = str(uuid.uuid4())
    db_execute(
        conn,
        """
        INSERT INTO committee_sessions
            (id, workspace_id, tenant_id, committee_type, min_members,
             session_status, activated_at)
        VALUES (:id, :ws, :tid, 'standard', 3, 'active', NOW())
        """,
        {"id": session_id, "ws": workspace_id, "tid": tenant_id},
    )
    db_execute(
        conn,
        """
        INSERT INTO committee_deliberation_events
            (session_id, workspace_id, tenant_id, actor_id, event_type, payload)
        VALUES (:sid, :ws, :tid, :uid, 'session_activated', :p)
        """,
        {
            "sid": session_id,
            "ws": workspace_id,
            "tid": tenant_id,
            "uid": user_id,
            "p": json.dumps({"committee_type": "standard", "auto_opened": True}),
        },
    )


def sync_committee_members_from_workspace(
    conn: Any, session_id: str, workspace_id: str, default_tenant_id: str
) -> None:
    rows = db_fetchall(
        conn,
        """
        SELECT DISTINCT ON (user_id) user_id, role, tenant_id
        FROM workspace_memberships
        WHERE workspace_id = CAST(:ws AS uuid) AND revoked_at IS NULL
        ORDER BY user_id, granted_at ASC
        """,
        {"ws": workspace_id},
    )
    for r in rows:
        uid = r.get("user_id")
        if uid is None:
            continue
        tid = str(r.get("tenant_id") or default_tenant_id)
        role_c = workspace_role_to_committee_role(str(r.get("role") or ""))
        member_id = str(uuid.uuid4())
        db_execute(
            conn,
            """
            INSERT INTO committee_session_members
                (id, session_id, workspace_id, tenant_id, user_id,
                 role_in_committee, is_voting)
            VALUES (:id, :sid, :ws, :tid, :uid, :role, TRUE)
            ON CONFLICT (session_id, user_id) DO UPDATE SET
                role_in_committee = EXCLUDED.role_in_committee,
                is_voting = EXCLUDED.is_voting,
                tenant_id = EXCLUDED.tenant_id
            """,
            {
                "id": member_id,
                "sid": session_id,
                "ws": workspace_id,
                "tid": tid,
                "uid": int(uid),
                "role": role_c,
            },
        )


def finalize_workspace_irr_seal(
    conn: Any,
    workspace_id: str,
    user_id: int,
    seal_comment: str | None,
    tenant_id_for_events: str,
    ws_row: dict[str, Any],
    event_via: str,
    *,
    auto_create_session: bool,
) -> dict[str, Any]:
    """Exécute scellement IRR + PV dans la transaction courante."""
    session = db_execute_one(
        conn,
        """
        SELECT id, session_status, tenant_id, seal_hash, sealed_at, pv_snapshot
        FROM committee_sessions
        WHERE workspace_id = :ws
        """,
        {"ws": workspace_id},
    )

    if session and str(session.get("session_status") or "") == "sealed":
        if str(ws_row.get("status") or "") != "sealed":
            sealed_at = session.get("sealed_at")
            if sealed_at is None:
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Session scellée sans sealed_at — données incohérentes.",
                )
            db_execute(
                conn,
                """
                UPDATE process_workspaces
                SET status = 'sealed',
                    sealed_at = COALESCE(sealed_at, :sealed_at)
                WHERE id = :wid
                """,
                {"sealed_at": sealed_at, "wid": workspace_id},
            )
            db_execute(
                conn,
                """
                INSERT INTO workspace_events
                    (workspace_id, tenant_id, event_type, actor_id, actor_type, payload)
                VALUES (:ws, :tid, 'WORKSPACE_STATUS_CHANGED', :uid, 'user', :p)
                """,
                {
                    "ws": workspace_id,
                    "tid": tenant_id_for_events,
                    "uid": user_id,
                    "p": json.dumps(
                        {
                            "from": str(ws_row.get("status")),
                            "to": "sealed",
                            "via": event_via + "_recovery",
                        }
                    ),
                },
            )
        return {
            "session_id": str(session["id"]),
            "seal_hash": str(session.get("seal_hash") or ""),
            "status": "sealed",
            "recovered": True,
        }

    if str(ws_row.get("status") or "") != "in_deliberation":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                "Le workspace doit être en statut in_deliberation avant le "
                "scellement IRR (guards BLOC5 — utiliser PATCH …/status)."
            ),
        )

    if session and str(session.get("session_status") or "") == "closed":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Session clôturée.",
        )

    check_result = run_all_seal_checks(conn, workspace_id)
    if not check_result.passed:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "seal_preconditions_failed",
                "message": "Pré-conditions de scellement non remplies.",
                "errors": check_result.errors,
                "warnings": check_result.warnings,
            },
        )

    if not session:
        if not auto_create_session:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Session non trouvée.",
            )
        _open_committee_session_auto(conn, workspace_id, tenant_id_for_events, user_id)
        session = db_execute_one(
            conn,
            """
            SELECT id, session_status, tenant_id, seal_hash, sealed_at, pv_snapshot
            FROM committee_sessions
            WHERE workspace_id = :ws
            """,
            {"ws": workspace_id},
        )

    if not session:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session comité introuvable après création.",
        )

    if str(session.get("session_status") or "") != "active":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Session comité dans un état inattendu: {session.get('session_status')}.",
        )

    sync_committee_members_from_workspace(
        conn, str(session["id"]), workspace_id, tenant_id_for_events
    )

    raw_tid = session.get("tenant_id")
    if raw_tid is None:
        raw_tid = ws_row.get("tenant_id")
    if not raw_tid:
        logger.error(
            "finalize_workspace_irr_seal: tenant_id introuvable session=%s workspace=%s",
            session["id"],
            workspace_id,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="tenant_id introuvable pour le journal de délibération",
        )
    tid_cde = str(raw_tid)

    pv_snapshot, seal_hash = build_pv_snapshot(
        conn=conn,
        workspace_id=workspace_id,
        session_id=str(session["id"]),
        user_id=user_id,
        seal_comment=seal_comment,
    )
    pv_json = safe_json_dumps(pv_snapshot, sort_keys=True)
    canonical_sealed_at = (pv_snapshot.get("decision") or {}).get("sealed_at")
    if not canonical_sealed_at:
        logger.error(
            "finalize_workspace_irr_seal: decision.sealed_at absent session=%s workspace=%s",
            session["id"],
            workspace_id,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Horodatage canonique de scellement introuvable dans le snapshot PV",
        )
    try:
        sealed_at = datetime.fromisoformat(
            str(canonical_sealed_at).replace("Z", "+00:00")
        ).astimezone(UTC)
    except ValueError as exc:
        logger.error(
            "finalize_workspace_irr_seal: decision.sealed_at invalide session=%s",
            session["id"],
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Horodatage canonique de scellement invalide dans le snapshot PV",
        ) from exc

    db_execute(
        conn,
        """
        UPDATE committee_sessions
        SET session_status = 'sealed',
            sealed_at = :sealed_at,
            sealed_by = :uid,
            seal_hash = :hash,
            pv_snapshot = :pv
        WHERE id = :sid
        """,
        {
            "sealed_at": sealed_at,
            "uid": user_id,
            "hash": seal_hash,
            "pv": pv_json,
            "sid": session["id"],
        },
    )

    db_execute(
        conn,
        """
        INSERT INTO committee_deliberation_events
            (session_id, workspace_id, tenant_id, actor_id, event_type, payload)
        VALUES (:sid, :ws, :tid, :actor, 'session_sealed', :p)
        """,
        {
            "sid": session["id"],
            "ws": workspace_id,
            "tid": tid_cde,
            "actor": user_id,
            "p": json.dumps({"seal_hash": seal_hash}),
        },
    )

    db_execute(
        conn,
        """
        UPDATE process_workspaces
        SET status = 'sealed',
            sealed_at = :sealed_at
        WHERE id = :wid
        """,
        {"sealed_at": sealed_at, "wid": workspace_id},
    )
    db_execute(
        conn,
        """
        INSERT INTO workspace_events
            (workspace_id, tenant_id, event_type, actor_id, actor_type, payload)
        VALUES (:ws, :tid, 'WORKSPACE_STATUS_CHANGED', :uid, 'user', :p)
        """,
        {
            "ws": workspace_id,
            "tid": tenant_id_for_events,
            "uid": user_id,
            "p": json.dumps(
                {"from": str(ws_row.get("status")), "to": "sealed", "via": event_via}
            ),
        },
    )

    return {
        "session_id": str(session["id"]),
        "seal_hash": seal_hash,
        "status": "sealed",
        "recovered": False,
    }
