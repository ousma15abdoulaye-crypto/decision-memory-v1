"""Contrôle d'accès workspace par rôle métier (membership + matrice de permissions).

Utilise la table ``workspace_memberships`` (migration 069) et les rôles texte
alignés sur le backfill migration 092. Pas d'ORM — requêtes via ``get_connection``.
"""

from __future__ import annotations

import logging
import uuid
from enum import StrEnum

from src.db import db_fetchall, get_connection

logger = logging.getLogger(__name__)


class WorkspaceRole(StrEnum):
    COMMITTEE_CHAIR = "committee_chair"
    COMMITTEE_MEMBER = "committee_member"
    PROCUREMENT_LEAD = "procurement_lead"
    TECHNICAL_REVIEWER = "technical_reviewer"
    FINANCE_REVIEWER = "finance_reviewer"
    OBSERVER = "observer"
    AUDITOR = "auditor"


def _parse_uuid_param(label: str, value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value).strip())
    except ValueError:
        logger.debug("%s non-UUID (%r) — refus contrôle accès", label, value)
        return None


WORKSPACE_PERMISSIONS: dict[WorkspaceRole, frozenset[str]] = {
    WorkspaceRole.COMMITTEE_CHAIR: frozenset(
        {
            "matrix.read",
            "matrix.comment",
            "deliberation.read",
            "deliberation.write",
            "deliberation.validate",
            "pv.read",
            "pv.seal",
            "financial.read",
            "clarification.raise",
            "clarification.resolve",
            "member.invite",
        }
    ),
    WorkspaceRole.COMMITTEE_MEMBER: frozenset(
        {
            "matrix.read",
            "matrix.comment",
            "deliberation.read",
            "deliberation.write",
            "deliberation.validate",
            "pv.read",
            "financial.read",
            "clarification.raise",
        }
    ),
    WorkspaceRole.PROCUREMENT_LEAD: frozenset(
        {
            "matrix.read",
            "deliberation.read",
            "pv.read",
            "financial.read",
            "workspace.manage",
            "member.invite",
            "member.revoke",
            "phase.advance",
        }
    ),
    WorkspaceRole.TECHNICAL_REVIEWER: frozenset(
        {
            "matrix.read",
            "deliberation.read",
            "deliberation.write",
            "clarification.raise",
        }
    ),
    WorkspaceRole.FINANCE_REVIEWER: frozenset(
        {
            "matrix.read",
            "financial.read",
            "financial.comment",
            "deliberation.read",
            "deliberation.write",
            "clarification.raise",
        }
    ),
    WorkspaceRole.OBSERVER: frozenset(
        {
            "matrix.read",
            "deliberation.read",
            "pv.read",
            "financial.read",
        }
    ),
    WorkspaceRole.AUDITOR: frozenset(
        {
            "matrix.read",
            "deliberation.read",
            "pv.read",
            "financial.read",
            "audit.full",
        }
    ),
}


class WorkspaceAccessService:
    """Vérifie une permission via ``workspace_memberships``."""

    @staticmethod
    def check_permission(
        workspace_id: str,
        user_id: int,
        permission: str,
        tenant_id: str,
    ) -> bool:
        """Retourne ``True`` si une ligne membership active accorde ``permission``.

        Ne lève pas d'exception si aucune ligne : retour ``False``.
        Bloque ``deliberation.validate`` et ``pv.seal`` si ``coi_declared`` est vrai
        (colonnes ajoutées en 092).

        ``tenant_id`` / ``workspace_id`` invalides (non-UUID) : ``False`` sans requête
        SQL (évite erreur ``CAST`` côté Postgres).
        """
        ws_u = _parse_uuid_param("workspace_id", workspace_id)
        tid_u = _parse_uuid_param("tenant_id", tenant_id)
        if ws_u is None or tid_u is None:
            return False

        with get_connection() as conn:
            rows = db_fetchall(
                conn,
                """
                SELECT wm.role, COALESCE(wm.coi_declared, FALSE) AS coi_declared
                FROM workspace_memberships wm
                JOIN process_workspaces w ON w.id = wm.workspace_id
                WHERE wm.workspace_id = CAST(:ws AS uuid)
                  AND wm.user_id = :uid
                  AND wm.revoked_at IS NULL
                  AND w.tenant_id = CAST(:tid AS uuid)
                """,
                {"ws": str(ws_u), "uid": user_id, "tid": str(tid_u)},
            )

        if not rows:
            return False

        blocked_under_coi = permission in (
            "deliberation.validate",
            "pv.seal",
        )

        for row in rows:
            role_str = str(row.get("role") or "")
            try:
                wr = WorkspaceRole(role_str)
            except ValueError:
                logger.debug("Rôle workspace inconnu %r — ignoré", role_str)
                continue

            perms = WORKSPACE_PERMISSIONS.get(wr, frozenset())
            if permission not in perms:
                continue

            coi = bool(row.get("coi_declared"))
            if coi and blocked_under_coi:
                continue

            return True

        return False
