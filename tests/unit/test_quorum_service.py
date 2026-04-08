"""Tests unitaires — quorum service INV-W01 V5.1.0."""

from __future__ import annotations

from src.services.quorum_service import (
    CRITICAL_ROLES,
    QUORUM_MINIMUM_MEMBERS,
    QuorumResult,
    check_quorum,
)


def _members(*roles: str) -> list[dict]:
    return [{"role": r} for r in roles]


class TestQuorumMinimum:
    def test_four_members_with_critical_roles_met(self):
        members = _members("supply_chain", "finance", "technical", "budget_holder")
        result = check_quorum(members)
        assert result.met is True
        assert len(result.blockers) == 0

    def test_three_members_not_met(self):
        members = _members("supply_chain", "finance", "technical")
        result = check_quorum(members)
        assert result.met is False
        assert any("Quorum insuffisant" in b for b in result.blockers)

    def test_minimum_is_four(self):
        assert QUORUM_MINIMUM_MEMBERS == 4

    def test_four_critical_roles_defined(self):
        assert "supply_chain" in CRITICAL_ROLES
        assert "finance" in CRITICAL_ROLES
        assert "technical" in CRITICAL_ROLES


class TestCriticalRolesRequired:
    def test_missing_supply_chain_blocks(self):
        members = _members("finance", "technical", "budget_holder", "admin")
        result = check_quorum(members)
        assert result.met is False
        assert "supply_chain" in result.missing_critical_roles

    def test_missing_finance_blocks(self):
        members = _members("supply_chain", "technical", "budget_holder", "admin")
        result = check_quorum(members)
        assert result.met is False
        assert "finance" in result.missing_critical_roles

    def test_missing_technical_blocks(self):
        members = _members("supply_chain", "finance", "budget_holder", "admin")
        result = check_quorum(members)
        assert result.met is False
        assert "technical" in result.missing_critical_roles

    def test_all_critical_roles_present(self):
        members = _members("supply_chain", "finance", "technical", "budget_holder")
        result = check_quorum(members)
        assert result.critical_roles_present >= CRITICAL_ROLES
        assert len(result.missing_critical_roles) == 0


class TestObserverExclusion:
    def test_observer_not_counted_in_quorum(self):
        members = _members("supply_chain", "finance", "technical", "observer")
        result = check_quorum(members)
        assert result.met is False
        assert result.member_count == 3

    def test_five_observers_not_met(self):
        members = _members(*["observer"] * 5)
        result = check_quorum(members)
        assert result.met is False


class TestQuorumResult:
    def test_returns_quorum_result(self):
        result = check_quorum(
            _members("supply_chain", "finance", "technical", "budget_holder")
        )
        assert isinstance(result, QuorumResult)

    def test_blockers_in_french(self):
        result = check_quorum(_members("observer"))
        for b in result.blockers:
            assert isinstance(b, str)
            assert len(b) > 0

    def test_exact_minimum_met(self):
        members = _members("supply_chain", "finance", "technical", "budget_holder")
        assert len(members) == QUORUM_MINIMUM_MEMBERS
        result = check_quorum(members)
        assert result.met is True

    def test_five_members_met(self):
        members = _members(
            "supply_chain", "finance", "technical", "budget_holder", "admin"
        )
        result = check_quorum(members)
        assert result.met is True

    def test_empty_members_not_met(self):
        result = check_quorum([])
        assert result.met is False
        assert result.member_count == 0
