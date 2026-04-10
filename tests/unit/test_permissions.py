"""Tests unitaires — RBAC V5.1.0 permissions × rôles.

Canon V5.1.0 Section 5.2. Locking test 4 (INV-S01 permissions matrix).
"""

from __future__ import annotations

import pytest

from src.auth.permissions import (
    ROLE_PERMISSIONS,
    ROLES_V51,
    WRITE_PERMISSIONS,
    has_permission,
)


class TestRolesV51:
    def test_six_roles_defined(self):
        assert len(ROLES_V51) == 6
        expected = {
            "supply_chain",
            "finance",
            "technical",
            "budget_holder",
            "observer",
            "admin",
        }
        assert ROLES_V51 == expected

    def test_all_roles_have_permission_entry(self):
        for role in ROLES_V51:
            assert role in ROLE_PERMISSIONS, f"Rôle '{role}' absent de ROLE_PERMISSIONS"


class TestPermissionsMatrix:
    """Vérifie la matrice Canon Section 5.2."""

    @pytest.mark.parametrize(
        "role",
        ["supply_chain", "finance", "technical", "budget_holder", "observer", "admin"],
    )
    def test_workspace_read_all_roles(self, role):
        assert has_permission(role, "workspace.read")

    @pytest.mark.parametrize("role", ["supply_chain", "admin"])
    def test_workspace_manage_privileged(self, role):
        assert has_permission(role, "workspace.manage")

    @pytest.mark.parametrize(
        "role", ["finance", "technical", "budget_holder", "observer"]
    )
    def test_workspace_manage_denied(self, role):
        assert not has_permission(role, "workspace.manage")

    @pytest.mark.parametrize("role", ["supply_chain", "admin"])
    def test_committee_seal_privileged(self, role):
        assert has_permission(role, "committee.seal")

    @pytest.mark.parametrize(
        "role", ["finance", "technical", "budget_holder", "observer"]
    )
    def test_committee_seal_denied(self, role):
        assert not has_permission(role, "committee.seal")

    def test_observer_cannot_comment(self):
        assert not has_permission("observer", "committee.comment")

    def test_observer_cannot_query_agent(self):
        assert not has_permission("observer", "agent.query")

    def test_audit_read_admin_only(self):
        for role in ROLES_V51 - {"admin"}:
            assert not has_permission(role, "audit.read")
        assert has_permission("admin", "audit.read")

    def test_mql_internal_admin_only(self):
        for role in ROLES_V51 - {"admin"}:
            assert not has_permission(role, "mql.internal")
        assert has_permission("admin", "mql.internal")

    def test_system_admin_admin_only(self):
        for role in ROLES_V51 - {"admin"}:
            assert not has_permission(role, "system.admin")
        assert has_permission("admin", "system.admin")

    def test_admin_has_all_18_permissions(self):
        all_perms = {
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
        assert all_perms == ROLE_PERMISSIONS["admin"]

    def test_eighteen_permissions_total(self):
        all_perms = set()
        for perms in ROLE_PERMISSIONS.values():
            all_perms |= set(perms)
        assert len(all_perms) == 18


class TestWritePermissions:
    def test_write_permissions_set(self):
        expected = {
            "workspace.manage",
            "documents.upload",
            "documents.delete",
            "evaluation.write",
            "committee.comment",
            "committee.seal",
            "market.write",  # ajouté P2 (correction permissions budget_holder)
        }
        assert WRITE_PERMISSIONS == expected

    def test_read_permissions_not_in_write_set(self):
        for perm in ("workspace.read", "evaluation.read", "committee.read", "pv.read"):
            assert perm not in WRITE_PERMISSIONS


class TestHasPermissionEdgeCases:
    def test_unknown_role_returns_false(self):
        assert not has_permission("hacker", "workspace.read")

    def test_empty_permission_returns_false(self):
        assert not has_permission("supply_chain", "")

    def test_admin_system_admin_grants_all(self):
        assert has_permission("admin", "workspace.read")
        # admin has system.admin — so all checks pass (Canon behaviour)
        assert has_permission("admin", "some.unknown.perm") is True
