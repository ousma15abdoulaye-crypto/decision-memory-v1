"""Contrôle d'accès workspace — remplace case_access.py (V4.2.0).

Vérifie l'appartenance d'un utilisateur à un workspace via :
  - workspace_memberships (membership explicite)
  - user_tenant_roles + RBAC (permission workspace.read)
  - admin flag (superuser)

Référence : docs/freeze/DMS_V4.2.0_RBAC.md — RÈGLE-W01
users.id = INTEGER (migration 004).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from src.couche_a.auth.dependencies import UserClaims
from src.db import db_execute_one, get_connection

logger = logging.getLogger(__name__)


def require_workspace_access(workspace_id: str, user: UserClaims) -> None:
    """Vérifie que l'utilisateur a accès au workspace.

    Lève HTTPException 403 si accès refusé, 404 si workspace absent.

    Logique :
      1. Workspace existe ET appartient au même tenant que l'utilisateur.
      2. Utilisateur est superuser OU membre workspace OU a permission workspace.read.

    Args:
        workspace_id: UUID du workspace à vérifier.
        user: Claims JWT de l'utilisateur courant.
    """
    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            """
            SELECT id, tenant_id, status
            FROM process_workspaces
            WHERE id = :ws_id
            """,
            {"ws_id": workspace_id},
        )

    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id!r} non trouvé.",
        )

    if user.is_superuser:
        return

    if user.tenant_id and ws.get("tenant_id") != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé — workspace appartient à un autre tenant.",
        )

    user_id = int(user.user_id)
    with get_connection() as conn:
        membership = db_execute_one(
            conn,
            """
            SELECT id FROM workspace_memberships
            WHERE workspace_id = :ws_id
              AND user_id = :uid
              AND revoked_at IS NULL
            """,
            {"ws_id": workspace_id, "uid": user_id},
        )

        if membership:
            return

        rbac_perm = db_execute_one(
            conn,
            """
            SELECT utr.id
            FROM user_tenant_roles utr
            JOIN rbac_role_permissions rrp ON rrp.role_id = utr.role_id
            JOIN rbac_permissions rp ON rp.id = rrp.permission_id
            WHERE utr.user_id = :uid
              AND utr.revoked_at IS NULL
              AND rp.code = 'workspace.read'
            LIMIT 1
            """,
            {"uid": user_id},
        )

        if rbac_perm:
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès refusé — workspace.read requis.",
    )


def require_workspace_permission(
    workspace_id: str,
    user: UserClaims,
    permission: str,
) -> None:
    """Vérifie une permission RBAC spécifique pour un workspace.

    Args:
        workspace_id: UUID du workspace.
        user: Claims JWT.
        permission: Code de permission (ex: 'workspace.close', 'bundle.upload').
    """
    require_workspace_access(workspace_id, user)

    if user.is_superuser:
        return

    user_id = int(user.user_id)
    with get_connection() as conn:
        perm_check = db_execute_one(
            conn,
            """
            SELECT utr.id
            FROM user_tenant_roles utr
            JOIN rbac_role_permissions rrp ON rrp.role_id = utr.role_id
            JOIN rbac_permissions rp ON rp.id = rrp.permission_id
            WHERE utr.user_id = :uid
              AND utr.revoked_at IS NULL
              AND rp.code = :perm
            LIMIT 1
            """,
            {"uid": user_id, "perm": permission},
        )

    if not perm_check:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Accès refusé — permission {permission!r} requise.",
        )
