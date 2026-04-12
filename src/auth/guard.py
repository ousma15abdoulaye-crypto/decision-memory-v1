"""Guard unifié DMS V5.2.

3 vérifications. 1 fonction. Toutes les routes.
Aucune autre vérification de permission ne doit exister ailleurs.

Connexion attendue : AsyncpgAdapter (src/db/async_pool.py) ou tout objet
exposant async fetch_one(sql: str, params: dict) et fetch_all().

COMPATIBILITÉ V4.x → V5.2 (P2.1) :
  workspace_memberships stocke encore des rôles V4.x (committee_chair, etc.)
  hérités du système Couche A. _LEGACY_ROLE_MAP les projette sur les rôles
  V5.2 pour que ROLE_PERMISSIONS puisse évaluer les permissions correctement.
  La migration complète des rôles en base est prévue en P3.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException

from src.core.config import get_settings
from src.couche_a.auth.pilot_access import is_pilot_terrain_user_id

logger = logging.getLogger(__name__)

# Permissions qui déclenchent la vérification de scellement (check 3).
# market.write ajouté en V5.2 (absent de l'ancienne liste workspace_access_service).
WRITE_PERMISSIONS: frozenset[str] = frozenset(
    {
        "workspace.manage",
        "documents.upload",
        "documents.delete",
        "evaluation.write",
        "committee.comment",
        "committee.seal",
        "market.write",
    }
)

# Statuts workspace qui interdisent toute écriture.
SEALED_STATUSES: frozenset[str] = frozenset({"sealed", "closed", "cancelled"})

# Mapping rôles V4.x (workspace_memberships legacy) → rôles V5.2 (ROLE_PERMISSIONS).
# committee_chair / committee_member / procurement_lead → supply_chain
# (rôles les plus larges de chaque famille ; projection conservatrice).
# observer reste observer. auditor → admin (audit.read inclus).
_LEGACY_ROLE_MAP: dict[str, str] = {
    "committee_chair": "supply_chain",
    "committee_member": "supply_chain",
    "procurement_lead": "supply_chain",
    "technical_reviewer": "technical",
    "finance_reviewer": "finance",
    "auditor": "admin",
}


async def guard(
    db,
    user: dict,
    workspace_id: UUID,
    permission: str,
) -> dict:
    """Point unique d'autorisation DMS.

    Vérifie dans cet ordre :
    1. Membership   — l'utilisateur est membre actif du workspace
                      (revoked_at IS NULL obligatoire).
    2. Permission RBAC — son rôle possède la permission demandée.
                      system.admin bypass toutes les permissions.
    3. Seal protection — pas d'écriture sur workspace clos / scellé.

    Args:
        db:           AsyncpgAdapter (ou tout adaptateur exposant fetch_one).
        user:         Dictionnaire des claims JWT ; doit contenir "id" (int).
                      Clé optionnelle ``role`` (JWT legacy) requise pour le fallback
                      ``WORKSPACE_ACCESS_JWT_FALLBACK`` sans membership.
        workspace_id: UUID du workspace cible.
        permission:   Code de permission métier (ex : "evaluation.write").

    Returns:
        dict membership row (contient au minimum "role").

    Raises:
        HTTPException 403: Non membre, permission refusée.
        HTTPException 409: Écriture tentée sur workspace clos.
    """
    try:
        uid = int(user.get("id"))
    except (TypeError, ValueError):
        uid = -1
    if uid >= 0 and is_pilot_terrain_user_id(uid):
        logger.warning(
            "guard PILOT_TERRAIN_BYPASS user_id=%s workspace_id=%s permission=%s",
            uid,
            workspace_id,
            permission,
        )
        return {"role": "admin"}

    # ── 1. Membership ─────────────────────────────────────────────────────
    # revoked_at IS NULL : exclut les membres révoqués (sécurité — spec oversight).
    member = await db.fetch_one(
        "SELECT role FROM workspace_memberships "
        "WHERE workspace_id = :ws AND user_id = :uid AND revoked_at IS NULL "
        "ORDER BY granted_at ASC LIMIT 1",
        {"ws": str(workspace_id), "uid": user["id"]},
    )
    if not member:
        # Pilote terrain : même logique que ``require_workspace_access`` — pas de ligne
        # membership mais JWT legacy mappé V5.2 avec la permission métier demandée.
        # Les écritures sensibles (WRITE_PERMISSIONS) sont refusées sur ce chemin :
        # le pilote ne remplace pas ``user_tenant_roles`` / membership pour M16 seal, etc.
        if get_settings().WORKSPACE_ACCESS_JWT_FALLBACK:
            from src.auth.permissions import ROLE_PERMISSIONS
            from src.couche_a.auth.rbac import ROLES as JWT_LEGACY_ROLES
            from src.couche_a.auth.workspace_access import legacy_jwt_to_v52_role

            jwt_role = (user.get("role") or "").strip()
            if jwt_role in JWT_LEGACY_ROLES:
                v52 = legacy_jwt_to_v52_role(jwt_role)
                if v52:
                    role_perms_fb = ROLE_PERMISSIONS.get(v52, frozenset())
                    can = "system.admin" in role_perms_fb or permission in role_perms_fb
                    if can and permission in WRITE_PERMISSIONS:
                        logger.warning(
                            "guard JWT_FALLBACK DENY_WRITE user_id=%s workspace_id=%s "
                            "permission=%s jwt_role=%s — membership DB requis pour écriture",
                            user["id"],
                            workspace_id,
                            permission,
                            jwt_role,
                        )
                    elif can:
                        logger.warning(
                            "guard JWT_FALLBACK user_id=%s workspace_id=%s permission=%s "
                            "jwt_role=%s v52=%s",
                            user["id"],
                            workspace_id,
                            permission,
                            jwt_role,
                            v52,
                        )
                        member = {"role": v52}

        if not member:
            raise HTTPException(
                status_code=403,
                detail="Vous n'êtes pas membre de ce workspace.",
            )

    # ── 2. Permission RBAC ────────────────────────────────────────────────
    role = member["role"]

    # Import local pour éviter circular import (guard ← permissions ← guard).
    from src.auth.permissions import ROLE_PERMISSIONS

    # Compatibilité V4.x : projeter le rôle legacy sur son équivalent V5.2
    # si nécessaire (workspace_memberships peut contenir committee_chair etc.).
    effective_role = _LEGACY_ROLE_MAP.get(role, role)
    role_perms = ROLE_PERMISSIONS.get(effective_role, frozenset())

    # system.admin bypass toutes les permissions métier.
    if "system.admin" not in role_perms and permission not in role_perms:
        raise HTTPException(
            status_code=403,
            detail=f"Rôle '{role}' (→{effective_role}) n'a pas la permission '{permission}'.",
        )

    # ── 3. Seal protection ────────────────────────────────────────────────
    if permission in WRITE_PERMISSIONS:
        ws = await db.fetch_one(
            "SELECT status FROM process_workspaces WHERE id = :ws",
            {"ws": str(workspace_id)},
        )
        if ws and ws["status"] in SEALED_STATUSES:
            raise HTTPException(
                status_code=409,
                detail="Workspace clos. Aucune modification possible.",
            )

    return dict(member)
