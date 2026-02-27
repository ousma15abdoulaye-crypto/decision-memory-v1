"""RBAC — matrice de permissions V4.1.0.

5 rôles définis dans ADR-M1-002.
SOD comité (sourcing lead ≠ membre votant) : réservé M16B.
audit_log permissions : réservé M1B.
"""

from __future__ import annotations

ROLES: frozenset[str] = frozenset({"admin", "manager", "buyer", "viewer", "auditor"})

# Matrice de permissions
# resource → set d'opérations autorisées
# "ALL" dans admin_ops = accès total aux opérations d'administration
PERMISSIONS: dict[str, dict[str, set[str]]] = {
    "admin": {
        "cases": {"C", "R", "U", "D"},
        "vendors": {"C", "R", "U", "D"},
        "committees": {"C", "R", "U", "D"},
        "admin_ops": {"ALL"},
    },
    "manager": {
        "cases": {"C", "R", "U", "D"},
        "vendors": {"C", "R", "U"},
        "committees": {"C", "R", "U", "D"},
        "admin_ops": set(),
    },
    "buyer": {
        "cases": {"C", "R"},
        "vendors": {"R"},
        "committees": {"R"},
        "admin_ops": set(),
    },
    "viewer": {
        "cases": {"R"},
        "vendors": {"R"},
        "committees": {"R"},
        "admin_ops": set(),
    },
    "auditor": {
        "cases": {"R"},
        "vendors": {"R"},
        "committees": {"R"},
        "admin_ops": set(),
    },
}


def is_allowed(role: str, resource: str, operation: str) -> bool:
    """Vérifie si un rôle est autorisé à effectuer une opération sur une ressource.

    Args:
        role: rôle de l'utilisateur (doit être dans ROLES)
        resource: ressource cible ('cases', 'vendors', 'committees', 'admin_ops')
        operation: opération ('C', 'R', 'U', 'D', 'ALL')

    Returns:
        True si autorisé, False sinon.
    """
    if role not in ROLES:
        return False
    perms = PERMISSIONS.get(role, {})
    resource_perms = perms.get(resource, set())
    return "ALL" in resource_perms or operation in resource_perms
