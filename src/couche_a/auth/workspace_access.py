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

from src.auth.permissions import has_permission
from src.core.config import get_settings
from src.couche_a.auth.dependencies import UserClaims
from src.couche_a.auth.pilot_access import is_pilot_terrain_user_claims
from src.couche_a.auth.rbac import ROLES as JWT_LEGACY_ROLES
from src.db import db_execute_one, get_connection
from src.services.workspace_access_service import WorkspaceAccessService

logger = logging.getLogger(__name__)

# JWT Couche A (``rbac.ROLES``) → rôle Canon V5.2 pour ``has_permission(..., "workspace.read")``.
# Tous les rôles legacy connexes ont au moins ``workspace.read`` en projection V5.2.
_LEGACY_JWT_TO_V52_FOR_WORKSPACE_READ: dict[str, str] = {
    "admin": "admin",
    "manager": "supply_chain",
    "buyer": "supply_chain",
    "viewer": "observer",
    "auditor": "admin",
}


def legacy_jwt_to_v52_role(jwt_role: str) -> str | None:
    """Projette un rôle JWT legacy sur le libellé V5.2 utilisé par ``ROLE_PERMISSIONS``."""
    return _LEGACY_JWT_TO_V52_FOR_WORKSPACE_READ.get((jwt_role or "").strip()) or None


def legacy_jwt_role_allows_workspace_read(jwt_role: str) -> bool:
    """True si le rôle JWT legacy est mappé sur un rôle V5.2 avec ``workspace.read``."""
    v52 = legacy_jwt_to_v52_role(jwt_role)
    if not v52:
        return False
    return has_permission(v52, "workspace.read")


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

    if is_pilot_terrain_user_claims(user):
        logger.warning(
            "workspace.access PILOT_TERRAIN_BYPASS user_id=%s workspace_id=%s",
            user.user_id,
            workspace_id,
        )
        return

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

    # Mode pilote / terrain : accès lecture si JWT legacy + matrice V5.2 (sans membership DB).
    # Désactivé par défaut — activer ``WORKSPACE_ACCESS_JWT_FALLBACK`` explicitement (Railway).
    if get_settings().WORKSPACE_ACCESS_JWT_FALLBACK:
        if user.role in JWT_LEGACY_ROLES and legacy_jwt_role_allows_workspace_read(
            user.role
        ):
            logger.warning(
                "workspace.access JWT_FALLBACK user_id=%s workspace_id=%s role=%s "
                "(WORKSPACE_ACCESS_JWT_FALLBACK=true — désactiver quand memberships prod OK)",
                user.user_id,
                workspace_id,
                user.role,
            )
            return

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

    if is_pilot_terrain_user_claims(user):
        logger.warning(
            "require_rbac_permission PILOT_TERRAIN_BYPASS user_id=%s permission=%s",
            user.user_id,
            permission,
        )
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
    if is_pilot_terrain_user_claims(user):
        logger.warning(
            "require_workspace_comment_permission PILOT_TERRAIN_BYPASS user_id=%s "
            "workspace_id=%s",
            user.user_id,
            workspace_id,
        )
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
    if is_pilot_terrain_user_claims(user):
        logger.warning(
            "require_workspace_permission PILOT_TERRAIN_BYPASS user_id=%s "
            "workspace_id=%s permission=%s",
            user.user_id,
            workspace_id,
            permission,
        )
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
