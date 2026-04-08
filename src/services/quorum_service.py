"""Service quorum V5.1.0 — INV-W01.

INV-W01 : Quorum ≥ 4 membres dont ≥ 1 votant par rôle critique pour scellement.
Canon V5.1.0 Section O4.

Rôles critiques votants : supply_chain, finance, technical.
Observer est exclu du calcul de quorum (lecture seule).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Rôles votants minimum requis pour le quorum (INV-W01)
QUORUM_MINIMUM_MEMBERS = 4
CRITICAL_ROLES: frozenset[str] = frozenset({"supply_chain", "finance", "technical"})


@dataclass(frozen=True)
class QuorumResult:
    """Résultat du contrôle de quorum avant scellement."""

    met: bool
    member_count: int
    critical_roles_present: frozenset[str]
    missing_critical_roles: frozenset[str]
    blockers: list[str] = field(default_factory=list)


def check_quorum(members: list[dict]) -> QuorumResult:
    """Vérifie le quorum INV-W01 à partir d'une liste de membres workspace.

    Args:
        members: Liste de dicts avec clé 'role'. Chaque dict représente
                 un membre actif (revoked_at IS NULL).

    Returns:
        QuorumResult indiquant si le quorum est atteint et pourquoi.
    """
    active = [m for m in members if m.get("role") != "observer"]
    count = len(active)
    present_roles = frozenset(
        m["role"] for m in active if m.get("role") in CRITICAL_ROLES
    )
    missing = CRITICAL_ROLES - present_roles

    blockers: list[str] = []
    if count < QUORUM_MINIMUM_MEMBERS:
        blockers.append(
            f"Quorum insuffisant : {count} membre(s) actif(s), "
            f"{QUORUM_MINIMUM_MEMBERS} requis (INV-W01)."
        )
    for role in sorted(missing):
        blockers.append(f"Rôle critique absent du comité : {role} (INV-W01).")

    return QuorumResult(
        met=len(blockers) == 0,
        member_count=count,
        critical_roles_present=present_roles,
        missing_critical_roles=missing,
        blockers=blockers,
    )
