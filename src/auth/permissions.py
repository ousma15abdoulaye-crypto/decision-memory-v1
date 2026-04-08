"""RBAC V5.1.0 — 18 permissions × 6 rôles.

Source de vérité unique (Canon V5.1.0 Section 5.2).
Ne remplace pas src/couche_a/auth/rbac.py (M16 legacy) — coexistence jusqu'à V5.2.
"""

from __future__ import annotations

# 6 rôles V5.1.0
ROLES_V51: frozenset[str] = frozenset(
    {"supply_chain", "finance", "technical", "budget_holder", "observer", "admin"}
)

# Matrice complète : rôle → ensemble de permissions (Canon Section 5.2)
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "supply_chain": frozenset(
        {
            "workspace.manage",
            "workspace.read",
            "documents.upload",
            "documents.read",
            "documents.delete",
            "evaluation.write",
            "evaluation.read",
            "committee.comment",
            "committee.read",
            "committee.seal",
            "pv.export",
            "pv.read",
            "market.query",
            "market.write",
            "agent.query",
        }
    ),
    "finance": frozenset(
        {
            "workspace.read",
            "documents.upload",
            "documents.read",
            "evaluation.write",
            "evaluation.read",
            "committee.comment",
            "committee.read",
            "pv.export",
            "pv.read",
            "market.query",
            "agent.query",
        }
    ),
    "technical": frozenset(
        {
            "workspace.read",
            "documents.upload",
            "documents.read",
            "evaluation.write",
            "evaluation.read",
            "committee.comment",
            "committee.read",
            "pv.read",
            "market.query",
            "agent.query",
        }
    ),
    "budget_holder": frozenset(
        {
            "workspace.read",
            "documents.read",
            "evaluation.read",
            "committee.comment",
            "committee.read",
            "pv.export",
            "pv.read",
            "market.query",
        }
    ),
    "observer": frozenset(
        {
            "workspace.read",
            "documents.read",
            "evaluation.read",
            "committee.read",
            "pv.read",
        }
    ),
    "admin": frozenset(
        {
            "workspace.manage",
            "workspace.read",
            "documents.upload",
            "documents.read",
            "documents.delete",
            "evaluation.write",
            "evaluation.read",
            "committee.comment",
            "committee.read",
            "committee.seal",
            "pv.export",
            "pv.read",
            "market.query",
            "market.write",
            "agent.query",
            "audit.read",
            "mql.internal",
            "system.admin",
        }
    ),
}

# Permissions d'écriture — soumises à la vérification seal (Canon Section 5.3)
WRITE_PERMISSIONS: frozenset[str] = frozenset(
    {
        "workspace.manage",
        "documents.upload",
        "documents.delete",
        "evaluation.write",
        "committee.comment",
        "committee.seal",
    }
)


def has_permission(role: str, permission: str) -> bool:
    """Vérifie si un rôle V5.1 possède une permission.

    Args:
        role: Rôle du membre (doit être dans ROLES_V51).
        permission: Code de permission.

    Returns:
        True si le rôle possède la permission ou ``system.admin``.
    """
    perms = ROLE_PERMISSIONS.get(role, frozenset())
    return permission in perms or "system.admin" in perms
