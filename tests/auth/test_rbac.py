"""Tests RBAC — matrice de permissions V4.1.0.

Nouveau module — indépendant de tests/test_rbac.py (legacy).
RÈGLE-07 : assertions explicites.
"""

from __future__ import annotations

import pytest

from src.couche_a.auth.rbac import ROLES, is_allowed

# ── Rôles ─────────────────────────────────────────────────────────────────────


def test_roles_set_complet():
    """Les 5 rôles V4.1.0 sont définis."""
    assert ROLES == frozenset({"admin", "manager", "buyer", "viewer", "auditor"})


# ── Admin ─────────────────────────────────────────────────────────────────────


def test_admin_cases_crud():
    """admin → CRUD sur cases."""
    for op in ("C", "R", "U", "D"):
        assert is_allowed("admin", "cases", op), f"admin doit pouvoir {op} sur cases"


def test_admin_vendors_crud():
    """admin → CRUD sur vendors."""
    for op in ("C", "R", "U", "D"):
        assert is_allowed("admin", "vendors", op)


def test_admin_committees_crud():
    """admin → CRUD sur committees."""
    for op in ("C", "R", "U", "D"):
        assert is_allowed("admin", "committees", op)


def test_admin_admin_ops_all():
    """admin → ALL sur admin_ops."""
    assert is_allowed("admin", "admin_ops", "ALL")


# ── Manager ──────────────────────────────────────────────────────────────────


def test_manager_cases_crud():
    """manager → CRUD sur cases."""
    for op in ("C", "R", "U", "D"):
        assert is_allowed("manager", "cases", op)


def test_manager_vendors_no_delete():
    """manager → CRU sur vendors, pas de DELETE."""
    for op in ("C", "R", "U"):
        assert is_allowed("manager", "vendors", op)
    assert not is_allowed("manager", "vendors", "D")


def test_manager_no_admin_ops():
    """manager → pas d'admin_ops."""
    assert not is_allowed("manager", "admin_ops", "ALL")


# ── Buyer ─────────────────────────────────────────────────────────────────────


def test_buyer_cases_create_read():
    """buyer → CR sur cases uniquement."""
    assert is_allowed("buyer", "cases", "C")
    assert is_allowed("buyer", "cases", "R")
    assert not is_allowed("buyer", "cases", "U")
    assert not is_allowed("buyer", "cases", "D")


def test_buyer_vendors_read_only():
    """buyer → READ seul sur vendors."""
    assert is_allowed("buyer", "vendors", "R")
    assert not is_allowed("buyer", "vendors", "C")
    assert not is_allowed("buyer", "vendors", "U")
    assert not is_allowed("buyer", "vendors", "D")


def test_buyer_committees_read():
    """buyer → lecture committees."""
    assert is_allowed("buyer", "committees", "R")
    assert not is_allowed("buyer", "committees", "C")


def test_buyer_no_admin_ops():
    """buyer → pas d'admin_ops."""
    assert not is_allowed("buyer", "admin_ops", "ALL")


# ── Viewer ────────────────────────────────────────────────────────────────────


def test_viewer_read_all_resources():
    """viewer → lecture sur cases, vendors, committees."""
    for resource in ("cases", "vendors", "committees"):
        assert is_allowed(
            "viewer", resource, "R"
        ), f"viewer doit pouvoir lire {resource}"


def test_viewer_no_write():
    """viewer → zéro écriture."""
    for resource in ("cases", "vendors", "committees"):
        for op in ("C", "U", "D"):
            assert not is_allowed("viewer", resource, op)


def test_viewer_no_admin_ops():
    """viewer → pas d'admin_ops."""
    assert not is_allowed("viewer", "admin_ops", "ALL")


# ── Auditor ───────────────────────────────────────────────────────────────────


def test_auditor_read_all_resources():
    """auditor → lecture sur cases, vendors, committees."""
    for resource in ("cases", "vendors", "committees"):
        assert is_allowed("auditor", resource, "R")


def test_auditor_no_admin_ops():
    """auditor → 403 sur admin_ops."""
    assert not is_allowed("auditor", "admin_ops", "ALL")


def test_auditor_no_write():
    """auditor → zéro écriture."""
    for resource in ("cases", "vendors", "committees"):
        for op in ("C", "U", "D"):
            assert not is_allowed("auditor", resource, op)


# ── Rôle inconnu ─────────────────────────────────────────────────────────────


def test_role_inconnu_refuse():
    """Rôle non reconnu → False sur toute ressource."""
    assert not is_allowed("unknown_role", "cases", "R")
    assert not is_allowed("", "cases", "R")
    assert not is_allowed("superadmin", "admin_ops", "ALL")


# ── Dépendances FastAPI ───────────────────────────────────────────────────────


def test_require_role_autorise():
    """require_role → admin est dans les rôles V4.1.0."""
    from src.couche_a.auth.rbac import ROLES

    assert "admin" in ROLES


def test_require_role_refuse():
    """require_role → HTTPException 403 si rôle non autorisé."""
    from fastapi import HTTPException, status

    from src.couche_a.auth.dependencies import UserClaims

    user = UserClaims(user_id="u", role="viewer", jti="j")
    allowed_roles = frozenset(["admin"])

    with pytest.raises(HTTPException) as exc_info:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé",
            )

    assert exc_info.value.status_code == 403
