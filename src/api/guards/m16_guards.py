"""
Guards M16 — RBAC + état cognitif (E0–E6) avant logique métier.

Utilise ``compute_cognitive_state`` (chaînes 'E0'…'E6') et ``load_cognitive_facts``.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import HTTPException, status

from src.api.cognitive_helpers import load_cognitive_facts
from src.cognitive.cognitive_state import compute_cognitive_state
from src.couche_a.auth.dependencies import UserClaims
from src.couche_a.auth.pilot_access import is_pilot_terrain_user_claims
from src.couche_a.auth.workspace_access import (
    require_rbac_permission,
    require_workspace_access,
)
from src.db import db_execute_one, get_connection

logger = logging.getLogger(__name__)

StateId = Literal["E0", "E1", "E2", "E3", "E4", "E5", "E6"]

_STATE_ORDER: dict[str, int] = {
    "E0": 0,
    "E1": 1,
    "E2": 2,
    "E3": 3,
    "E4": 4,
    "E5": 5,
    "E6": 6,
}


def _order(state: str) -> int:
    return _STATE_ORDER.get(state, 0)


def m16_guard(
    workspace_id: str,
    user: UserClaims,
    *,
    min_cognitive: StateId = "E3",
    permission: str | None = None,
    block_write_if_sealed: bool = False,
) -> None:
    """Vérifie accès workspace, permission optionnelle, seuil cognitif, scellement."""
    if is_pilot_terrain_user_claims(user):
        logger.warning(
            "m16_guard PILOT_TERRAIN_BYPASS user_id=%s workspace_id=%s",
            user.user_id,
            workspace_id,
        )
        return

    require_workspace_access(workspace_id, user)
    if permission:
        require_rbac_permission(user, permission)

    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            "SELECT * FROM process_workspaces WHERE id = CAST(:id AS uuid)",
            {"id": workspace_id},
        )
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace introuvable",
            )
        facts = load_cognitive_facts(conn, ws)
        cognitive = compute_cognitive_state(facts)

        if _order(cognitive) < _order(min_cognitive):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "cognitive_state_insufficient",
                    "current_state": cognitive,
                    "minimum_state": min_cognitive,
                    "message": (
                        f"État cognitif insuffisant: {cognitive!r}, "
                        f"minimum requis {min_cognitive!r}."
                    ),
                },
            )

        if block_write_if_sealed and cognitive == "E6":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "workspace_sealed",
                    "message": "Workspace scellé — écriture interdite.",
                },
            )
