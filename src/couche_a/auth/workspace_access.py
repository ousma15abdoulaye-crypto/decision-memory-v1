"""Contrôle d'accès workspace — remplace case_access.py (V4.2.0).

Vérifie l'appartenance d'un utilisateur à un workspace via :
  - ``WorkspaceAccessService`` (membership + matrice permissions, ex. ``matrix.read``)
  - membership explicite (ligne ``workspace_memberships`` sans filtre rôle)
  - ``user_tenant_roles`` + RBAC (permission ``workspace.read``)
  - rôle JWT admin (bypass tracé en log)

Référence : docs/freeze/DMS_V4.2.0_RBAC.md — RÈGLE-W01
users.id = INTEGER (migration 004).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from src.couche_a.auth.dependencies import UserClaims
from src.db import db_execute_one, get_connection
from src.services.workspace_access_service import WorkspaceAccessService

logger = logging.getLogger(__name__)


def _tenant_id_str(value: object) -> str:
    """Normalise tenant_id DB (uuid.UUID, str) pour comparaison avec UserClaims.tenant_id."""
    if value is None:
        return ""
    return str(value)


def require_workspace_access(workspace_id: str, user: UserClaims) -> None:
    """Vérifie que l'utilisateur a accès au workspace.

    Lève HTTPException 403 si accès refusé, 404 si workspace absent.

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

    if user.role == "admin":
        logger.info(
            "workspace.access admin bypass user_id=%s workspace_id=%s",
            user.user_id,
            workspace_id,
        )
        return

    if user.tenant_id and _tenant_id_str(ws.get("tenant_id")) != _tenant_id_str(
        user.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé — workspace appartient à un autre tenant.",
        )

    user_id = int(user.user_id)
    tid = _tenant_id_str(user.tenant_id)
    if tid and WorkspaceAccessService.check_permission(
        workspace_id, user_id, "matrix.read", tid
    ):
        return

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


def require_rbac_permission(user: UserClaims, permission: str) -> None:
    """Vérifie une permission RBAC tenant (à appeler après ``require_workspace_access``).

    Args:
        user: Claims JWT.
        permission: Code de permission (ex: 'workspace.close', 'bundle.upload').
    """
    if user.role == "admin":
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


def require_workspace_comment_permission(workspace_id: str, user: UserClaims) -> None:
    """Autorise POST commentaire CDE (Canon O8) si membership accorde au moins une des permissions.

    ``matrix.comment`` (comité) ou ``deliberation.write`` (rôles rédacteurs).
    Admin JWT : bypass loggé via ``require_workspace_access``.
    """
    require_workspace_access(workspace_id, user)
    if user.role == "admin":
        return
    user_id = int(user.user_id)
    tid = user.tenant_id
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )
    tid_s = str(tid)
    if WorkspaceAccessService.check_permission(
        workspace_id, user_id, "matrix.comment", tid_s
    ):
        return
    if WorkspaceAccessService.check_permission(
        workspace_id, user_id, "deliberation.write", tid_s
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès refusé — matrix.comment ou deliberation.write requis pour commenter.",
    )


def require_workspace_permission(
    workspace_id: str,
    user: UserClaims,
    permission: str,
) -> None:
    """Vérifie une permission métier via ``workspace_memberships`` (Canon §5.3).

    Après ``require_workspace_access`` (tenant + accès lecture ou membership).
    Les admins JWT sont déjà autorisés par ``require_workspace_access``.

    Args:
        workspace_id: UUID du workspace.
        user: Claims JWT.
        permission: Code permission métier (ex: ``committee.manage``, ``bundle.upload``).
    """
    require_workspace_access(workspace_id, user)
    if user.role == "admin":
        return
    tid = user.tenant_id
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id manquant dans le JWT.",
        )
    if not WorkspaceAccessService.check_permission(
        workspace_id,
        int(user.user_id),
        permission,
        str(tid),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Accès refusé — permission workspace {permission!r} requise.",
        )
