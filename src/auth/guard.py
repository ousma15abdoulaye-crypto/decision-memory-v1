"""Guard unifié V5.1.0 — 3 vérifications, 1 fonction, toutes les routes.

Canon V5.1.0 Section 5.3.
Adaptation codebase : user reçoit UserClaims (pas dict) ;
                      DB est une connexion asyncpg (pas databases.Database) ;
                      params asyncpg = $1 $2 (pas :name).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from src.auth.permissions import ROLE_PERMISSIONS, WRITE_PERMISSIONS
from src.couche_a.auth.dependencies import UserClaims


async def guard(
    conn,
    user: UserClaims,
    workspace_id: UUID | str,
    permission: str,
) -> str:
    """Vérifie membership, permission RBAC et protection seal.

    3 vérifications. 1 fonction. Toutes les routes (INV-S02).

    Args:
        conn: Connexion asyncpg acquise via acquire_with_rls().
        user: Claims JWT de l'utilisateur courant.
        workspace_id: UUID du workspace cible.
        permission: Permission requise (ex: 'evaluation.write').

    Returns:
        Rôle du membre dans le workspace.

    Raises:
        HTTPException 403: Membership absent ou permission insuffisante.
        HTTPException 409: Écriture tentée sur workspace clos.
    """
    ws_id = str(workspace_id)
    uid = int(user.user_id)

    # 1. Membership
    member = await conn.fetchrow(
        "SELECT role FROM workspace_memberships "
        "WHERE workspace_id = $1 AND user_id = $2 AND revoked_at IS NULL",
        ws_id,
        uid,
    )
    if not member:
        raise HTTPException(403, "Vous n'êtes pas membre de ce workspace.")

    role = member["role"]

    # 2. Permission RBAC
    role_perms = ROLE_PERMISSIONS.get(role, frozenset())
    if permission not in role_perms and "system.admin" not in role_perms:
        raise HTTPException(403, f"Rôle '{role}' n'a pas la permission '{permission}'.")

    # 3. Seal protection — bloque les mutations sur workspace clos
    if permission in WRITE_PERMISSIONS:
        ws = await conn.fetchrow(
            "SELECT status FROM process_workspaces WHERE id = $1",
            ws_id,
        )
        if ws and ws["status"] in ("sealed", "closed", "cancelled"):
            raise HTTPException(409, "Workspace clos. Aucune modification possible.")

    return role
