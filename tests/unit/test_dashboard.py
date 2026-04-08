"""Locking test 12 — INV-F06 : Dashboard retourne TOUS les workspaces.

Canon V5.1.0 Section O0 + INV-F06.
Tests unitaires avec mocks DB (pas de DB live requise).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


def _make_user(tenant_id: str = "t-001") -> Any:
    user = MagicMock()
    user.tenant_id = tenant_id
    user.user_id = 42
    user.role = "admin"
    return user


def _make_ws_rows(n: int) -> list[dict[str, Any]]:
    statuses = ["draft", "in_analysis", "in_deliberation", "sealed"]
    rows = []
    for i in range(n):
        rows.append(
            {
                "id": f"ws-{i:03d}",
                "reference_code": f"REF-{i:03d}",
                "title": f"Workspace {i}",
                "process_type": "devis_simple",
                "status": statuses[i % len(statuses)],
                "estimated_value": 10000 + i * 1000,
                "currency": "XOF",
                "created_at": f"2026-01-{i + 1:02d}",
                "assembled_at": None,
                "sealed_at": None,
                "closed_at": None,
                "tenant_id": "t-001",
            }
        )
    return rows


class TestDashboardReturnsAllWorkspaces:
    """INV-F06 : le dashboard retourne TOUS les workspaces du tenant."""

    def test_returns_all_workspaces_no_limit(self):
        from src.api.routers.dashboard import get_dashboard

        ws_rows = _make_ws_rows(10)

        def fake_fetchall(conn, sql, params):
            return ws_rows

        def fake_load_facts(conn, ws_row):
            facts = MagicMock()
            facts.member_count = 4
            facts.has_source_package = True
            facts.bundle_count = 2
            facts.all_assessments_done = False
            facts.has_committee_session = False
            facts.is_sealed = False
            facts.has_pv = False
            return facts

        user = _make_user()
        fake_conn = MagicMock()

        with (
            patch("src.api.routers.dashboard.get_connection") as mock_conn,
            patch("src.api.routers.dashboard.db_fetchall", fake_fetchall),
            patch("src.api.routers.dashboard.load_cognitive_facts", fake_load_facts),
        ):
            mock_conn.return_value.__enter__ = MagicMock(return_value=fake_conn)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            result = get_dashboard(user=user)

        assert result["total"] == 10, "INV-F06 — doit retourner TOUS les workspaces"
        assert len(result["workspaces"]) == 10

    def test_each_workspace_has_cognitive_state(self):
        from src.api.routers.dashboard import get_dashboard

        ws_rows = _make_ws_rows(3)

        def fake_fetchall(conn, sql, params):
            return ws_rows

        def fake_load_facts(conn, ws_row):
            facts = MagicMock()
            facts.member_count = 4
            facts.has_source_package = True
            facts.bundle_count = 2
            facts.all_assessments_done = False
            facts.has_committee_session = False
            facts.is_sealed = False
            facts.has_pv = False
            return facts

        user = _make_user()
        fake_conn = MagicMock()

        with (
            patch("src.api.routers.dashboard.get_connection") as mock_conn,
            patch("src.api.routers.dashboard.db_fetchall", fake_fetchall),
            patch("src.api.routers.dashboard.load_cognitive_facts", fake_load_facts),
        ):
            mock_conn.return_value.__enter__ = MagicMock(return_value=fake_conn)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            result = get_dashboard(user=user)

        for ws in result["workspaces"]:
            assert "cognitive" in ws
            cog = ws["cognitive"]
            assert "state" in cog
            assert "confidence_regime" in cog
            assert "completeness" in cog

    def test_phase_stats_aggregated(self):
        from src.api.routers.dashboard import get_dashboard

        ws_rows = _make_ws_rows(8)

        def fake_fetchall(conn, sql, params):
            return ws_rows

        def fake_load_facts(conn, ws_row):
            facts = MagicMock()
            facts.member_count = 4
            facts.has_source_package = True
            facts.bundle_count = 2
            facts.all_assessments_done = False
            facts.has_committee_session = False
            facts.is_sealed = False
            facts.has_pv = False
            return facts

        user = _make_user()
        fake_conn = MagicMock()

        with (
            patch("src.api.routers.dashboard.get_connection") as mock_conn,
            patch("src.api.routers.dashboard.db_fetchall", fake_fetchall),
            patch("src.api.routers.dashboard.load_cognitive_facts", fake_load_facts),
        ):
            mock_conn.return_value.__enter__ = MagicMock(return_value=fake_conn)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            result = get_dashboard(user=user)

        assert "phase_stats" in result
        assert sum(result["phase_stats"].values()) == 8

    def test_sorted_by_urgency(self):
        from src.api.routers.dashboard import get_dashboard

        ws_rows = _make_ws_rows(4)

        def fake_fetchall(conn, sql, params):
            return ws_rows

        def fake_load_facts(conn, ws_row):
            facts = MagicMock()
            facts.member_count = 4
            facts.has_source_package = True
            facts.bundle_count = 2
            facts.all_assessments_done = False
            facts.has_committee_session = False
            facts.is_sealed = False
            facts.has_pv = False
            return facts

        user = _make_user()
        fake_conn = MagicMock()

        with (
            patch("src.api.routers.dashboard.get_connection") as mock_conn,
            patch("src.api.routers.dashboard.db_fetchall", fake_fetchall),
            patch("src.api.routers.dashboard.load_cognitive_facts", fake_load_facts),
        ):
            mock_conn.return_value.__enter__ = MagicMock(return_value=fake_conn)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            result = get_dashboard(user=user)

        regimes = [w["cognitive"]["confidence_regime"] for w in result["workspaces"]]
        urgency_vals = [{"red": 0, "yellow": 1, "green": 2}.get(r, 99) for r in regimes]
        assert urgency_vals == sorted(
            urgency_vals
        ), "Workspaces doivent être triés par urgence"

    def test_no_forbidden_keys_in_response(self):
        from src.api.routers.dashboard import get_dashboard

        ws_rows = _make_ws_rows(2)

        def fake_fetchall(conn, sql, params):
            return ws_rows

        def fake_load_facts(conn, ws_row):
            facts = MagicMock()
            facts.member_count = 4
            facts.has_source_package = True
            facts.bundle_count = 2
            facts.all_assessments_done = False
            facts.has_committee_session = False
            facts.is_sealed = False
            facts.has_pv = False
            return facts

        user = _make_user()
        fake_conn = MagicMock()

        with (
            patch("src.api.routers.dashboard.get_connection") as mock_conn,
            patch("src.api.routers.dashboard.db_fetchall", fake_fetchall),
            patch("src.api.routers.dashboard.load_cognitive_facts", fake_load_facts),
        ):
            mock_conn.return_value.__enter__ = MagicMock(return_value=fake_conn)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            result = get_dashboard(user=user)

        import json

        raw = json.dumps(result).lower()
        for forbidden in (
            "winner",
            "rank",
            "recommendation",
            "selected_vendor",
            "best_offer",
        ):
            assert (
                forbidden not in raw
            ), f"INV-W06 — champ interdit '{forbidden}' dans le dashboard"
