"""Dashboard multi-workspace — Canon V5.1.0 O0.

GET /api/dashboard — vue pilotage de tous les workspaces de l'utilisateur.
- compute_cognitive_state par workspace
- Tri par urgence (health red > amber > green, needs_action, deadline)
- Stats agrégées par phase
- INV-F06 : retourne TOUS les workspaces du tenant (frontend refresh 30s)
- INV-W06 : aucun champ interdit (winner/rank/recommendation)
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status

from src.api.cognitive_helpers import load_cognitive_facts
from src.cognitive.cognitive_state import (
    compute_cognitive_state_result,
)
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.db import db_fetchall, get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard-v51"])

_URGENCY_ORDER = {
    "red": 0,
    "yellow": 1,
    "green": 2,
}


@router.get("")
def get_dashboard(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> dict[str, Any]:
    """Vue pilotage multi-workspace (Canon O0 — INV-F06).

    Retourne tous les workspaces du tenant courant enrichis de
    l'état cognitif, triés par urgence.
    """
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )

    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT id, reference_code, title, process_type, status,
                   estimated_value, currency, created_at, assembled_at,
                   sealed_at, closed_at
            FROM process_workspaces
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
            """,
            {"tid": tenant_id},
        )

        workspaces = []
        phase_stats: Counter[str] = Counter()

        for ws_row in rows:
            ws_id = str(ws_row.get("id") or "")
            status = str(ws_row.get("status") or "draft")
            phase_stats[status] += 1

            try:
                facts = load_cognitive_facts(conn, ws_row)
                cog = compute_cognitive_state_result(facts)
                cognitive = {
                    "state": cog.state,
                    "label_fr": cog.label_fr,
                    "phase": cog.phase,
                    "completeness": cog.completeness,
                    "can_advance": cog.can_advance,
                    "advance_blockers": list(cog.advance_blockers),
                    "available_actions": sorted(cog.available_actions),
                    "confidence_regime": cog.confidence_regime,
                }
            except Exception as exc:
                logger.warning(
                    "Dashboard: cognitive state failed ws=%s : %s", ws_id, exc
                )
                cognitive = {
                    "state": "E0",
                    "label_fr": "Erreur calcul",
                    "phase": "unknown",
                    "completeness": 0.0,
                    "can_advance": False,
                    "advance_blockers": [str(exc)],
                    "available_actions": [],
                    "confidence_regime": "red",
                }

            workspaces.append(
                {
                    "id": ws_id,
                    "reference_code": ws_row.get("reference_code"),
                    "title": ws_row.get("title"),
                    "process_type": ws_row.get("process_type"),
                    "status": status,
                    "estimated_value": ws_row.get("estimated_value"),
                    "currency": ws_row.get("currency"),
                    "created_at": str(ws_row.get("created_at") or ""),
                    "sealed_at": str(ws_row.get("sealed_at") or ""),
                    "cognitive": cognitive,
                }
            )

        workspaces.sort(
            key=lambda w: (
                _URGENCY_ORDER.get(w["cognitive"]["confidence_regime"], 99),
                not w["cognitive"]["can_advance"],
                w["cognitive"]["completeness"],
            )
        )

    return {
        "workspaces": workspaces,
        "total": len(workspaces),
        "phase_stats": dict(phase_stats),
    }
