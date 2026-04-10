"""RBAC V5.2 — 18 permissions × 6 rôles.

Source de vérité unique (Canon V5.1.0 Section 5.2, corrigé V5.2).
Ne remplace pas src/couche_a/auth/rbac.py (M16 legacy) — coexistence jusqu'à V5.2.

CORRECTIONS V5.2 (P1.3b) :
  - technical   : agent.query retiré (évaluateur technique, pas d'IA agent) → 9 perms
  - budget_holder: agent.query ajouté (autorité budgétaire / DGMP) → 9 perms
  - WRITE_PERMISSIONS : market.write ajouté (alignement sur guard.py V5.2)
"""

from __future__ import annotations

# 6 rôles V5.2
ROLES_V51: frozenset[str] = frozenset(
    {"supply_chain", "finance", "technical", "budget_holder", "observer", "admin"}
)

# Matrice complète : rôle → ensemble de permissions (Canon Section 5.2)
# Comptage V5.2 :
#   supply_chain : 15   finance : 11   technical : 9
#   budget_holder : 9   observer : 5   admin : 18
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "supply_chain": frozenset(
        {
            "workspace.manage",  # 1
            "workspace.read",  # 2
            "documents.upload",  # 3
            "documents.read",  # 4
            "documents.delete",  # 5
            "evaluation.write",  # 6
            "evaluation.read",  # 7
            "committee.comment",  # 8
            "committee.read",  # 9
            "committee.seal",  # 10
            "pv.export",  # 11
            "pv.read",  # 12
            "market.query",  # 13
            "market.write",  # 14
            "agent.query",  # 15
        }
    ),
    "finance": frozenset(
        {
            "workspace.read",  # 1
            "documents.upload",  # 2
            "documents.read",  # 3
            "evaluation.write",  # 4
            "evaluation.read",  # 5
            "committee.comment",  # 6
            "committee.read",  # 7
            "pv.export",  # 8
            "pv.read",  # 9
            "market.query",  # 10
            "agent.query",  # 11
        }
    ),
    "technical": frozenset(
        {
            "workspace.read",  # 1
            "documents.upload",  # 2
            "documents.read",  # 3
            "evaluation.write",  # 4
            "evaluation.read",  # 5
            "committee.comment",  # 6
            "committee.read",  # 7
            "pv.read",  # 8
            "market.query",  # 9
            # agent.query retiré en V5.2 — évaluateurs techniques hors périmètre IA
        }
    ),
    "budget_holder": frozenset(
        {
            "workspace.read",  # 1
            "documents.read",  # 2
            "evaluation.read",  # 3
            "committee.comment",  # 4
            "committee.read",  # 5
            "pv.export",  # 6
            "pv.read",  # 7
            "market.query",  # 8
            "agent.query",  # 9 — ajouté V5.2 : autorité budgétaire / DGMP
        }
    ),
    "observer": frozenset(
        {
            "workspace.read",  # 1
            "documents.read",  # 2
            "evaluation.read",  # 3
            "committee.read",  # 4
            "pv.read",  # 5
            # Aucune permission d'écriture (Canon §5.2 invariant)
        }
    ),
    "admin": frozenset(
        {
            "workspace.manage",  # 1
            "workspace.read",  # 2
            "documents.upload",  # 3
            "documents.read",  # 4
            "documents.delete",  # 5
            "evaluation.write",  # 6
            "evaluation.read",  # 7
            "committee.comment",  # 8
            "committee.read",  # 9
            "committee.seal",  # 10
            "pv.export",  # 11
            "pv.read",  # 12
            "market.query",  # 13
            "market.write",  # 14
            "agent.query",  # 15
            "audit.read",  # 16
            "mql.internal",  # 17
            "system.admin",  # 18
        }
    ),
}

# Permissions d'écriture — soumises à la vérification seal (Canon Section 5.3).
# market.write ajouté en V5.2 — alignement sur guard.py WRITE_PERMISSIONS.
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


def has_permission(role: str, permission: str) -> bool:
    """Vérifie si un rôle V5.2 possède une permission.

    Args:
        role: Rôle du membre (doit être dans ROLES_V51).
        permission: Code de permission.

    Returns:
        True si le rôle possède la permission ou ``system.admin``.
    """
    perms = ROLE_PERMISSIONS.get(role, frozenset())
    return permission in perms or "system.admin" in perms
