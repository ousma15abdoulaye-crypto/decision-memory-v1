"""Guard unifié V5.1.0 — 3 vérifications, 1 fonction, toutes les routes.

Canon V5.1.0 Section 5.3 (membership workspace + permission métier + seal).
Connexion asyncpg avec RLS (``acquire_with_rls``).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from src.couche_a.auth.dependencies import UserClaims
from src.services.workspace_access_service import (
    WORKSPACE_WRITE_PERMISSIONS,
    check_workspace_permission_async,
)


async def guard(
    conn,
    user: UserClaims,
    workspace_id: UUID | str,
    permission: str,
) -> str:
    """Vérifie membership, permission workspace et protection seal.

    Args:
        conn: Connexion asyncpg acquise via acquire_with_rls().
        user: Claims JWT de l'utilisateur courant.
        workspace_id: UUID du workspace cible.
        permission: Permission métier (ex: 'agent.query', 'committee.manage').

    Returns:
        Premier rôle workspace trouvé (chaîne DB).

    Raises:
        HTTPException 400: tenant_id JWT manquant.
        HTTPException 403: Non membre ou permission refusée.
        HTTPException 409: Écriture sur workspace scellé / clos.
    """
    ws_id = str(workspace_id)
    uid = int(user.user_id)

    if not user.tenant_id:
        raise HTTPException(400, "tenant_id manquant dans le JWT.")

    tid = str(user.tenant_id)
    allowed = await check_workspace_permission_async(conn, ws_id, uid, permission, tid)
    if not allowed:
        raise HTTPException(
            403,
            f"Permission workspace '{permission}' refusée ou membership absent.",
        )

    member = await conn.fetchrow(
        "SELECT role FROM workspace_memberships "
        "WHERE workspace_id = $1::uuid AND user_id = $2 AND revoked_at IS NULL "
        "ORDER BY granted_at ASC LIMIT 1",
        ws_id,
        uid,
    )
    role = str(member["role"]) if member else "unknown"

    if permission in WORKSPACE_WRITE_PERMISSIONS:
        ws = await conn.fetchrow(
            "SELECT status FROM process_workspaces WHERE id = $1::uuid",
            ws_id,
        )
        if ws and ws["status"] in ("sealed", "closed", "cancelled"):
            raise HTTPException(409, "Workspace clos. Aucune modification possible.")

    return role
