"""Mapping JWT legacy → accès lecture workspace (mode terrain)."""

from src.couche_a.auth.workspace_access import legacy_jwt_role_allows_workspace_read


def test_legacy_jwt_all_rbac_roles_allow_workspace_read():
    for role in ("admin", "manager", "buyer", "viewer", "auditor"):
        assert legacy_jwt_role_allows_workspace_read(role), role


def test_legacy_jwt_unknown_role_denied():
    assert not legacy_jwt_role_allows_workspace_read("supply_chain")
    assert not legacy_jwt_role_allows_workspace_read("")
    assert not legacy_jwt_role_allows_workspace_read("hacker")
