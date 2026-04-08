"""Matrice workspace_memberships × permissions métier (Canon V5.1 §5.3 adapté)."""

from __future__ import annotations

import pytest

from src.services.workspace_access_service import (
    WORKSPACE_PERMISSIONS,
    WORKSPACE_WRITE_PERMISSIONS,
    WorkspaceRole,
    _permission_granted_by_rows,
)


def test_committee_chair_has_committee_manage_and_agent_query() -> None:
    perms = WORKSPACE_PERMISSIONS[WorkspaceRole.COMMITTEE_CHAIR]
    assert "committee.manage" in perms
    assert "agent.query" in perms
    assert "pv.seal" in perms


def test_procurement_lead_has_bundle_upload_and_committee_manage() -> None:
    perms = WORKSPACE_PERMISSIONS[WorkspaceRole.PROCUREMENT_LEAD]
    assert "bundle.upload" in perms
    assert "committee.manage" in perms
    assert "member.invite" in perms


def test_committee_member_has_bundle_upload_not_committee_manage() -> None:
    perms = WORKSPACE_PERMISSIONS[WorkspaceRole.COMMITTEE_MEMBER]
    assert "bundle.upload" in perms
    assert "committee.manage" not in perms


def test_coi_blocks_pv_seal() -> None:
    rows = [
        {"role": "committee_chair", "coi_declared": True},
    ]
    assert _permission_granted_by_rows(rows, "pv.seal") is False
    assert _permission_granted_by_rows(rows, "matrix.read") is True


def test_workspace_write_permissions_covers_mutations() -> None:
    assert "committee.manage" in WORKSPACE_WRITE_PERMISSIONS
    assert "bundle.upload" in WORKSPACE_WRITE_PERMISSIONS


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        ("committee_chair", "committee.manage", True),
        ("observer", "committee.manage", False),
        ("procurement_lead", "phase.advance", True),
        ("committee_member", "phase.advance", False),
    ],
)
def test_permission_granted_by_rows(role: str, permission: str, expected: bool) -> None:
    rows = [{"role": role, "coi_declared": False}]
    assert _permission_granted_by_rows(rows, permission) is expected
