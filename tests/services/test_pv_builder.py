from __future__ import annotations

from datetime import UTC, datetime

from src.services import pv_builder
from src.services.document_service import _canonical_hash


def test_pv_builder_has_9_blocks_and_kill_list_absent(monkeypatch) -> None:
    def fake_one(_conn, sql: str, _params):
        if "FROM process_workspaces" in sql:
            return {
                "id": "ws-1",
                "reference_code": "REF-1",
                "title": "Test",
                "process_type": "devis_simple",
                "zone": "MLI",
                "zone_id": "MLI-MOPTI",
                "category": "med",
                "estimated_value": 1000,
                "currency": "XOF",
                "humanitarian_context": True,
                "tenant_id": "tenant-1",
                "status": "in_deliberation",
            }
        if "FROM committee_sessions" in sql:
            return {
                "id": "sid-1",
                "workspace_id": "ws-1",
                "tenant_id": "tenant-1",
                "session_status": "active",
                "min_members": 3,
            }
        if "FROM evaluation_documents" in sql:
            return {
                "scores_matrix": {
                    "bundle-1": {
                        "quality": {"score": 8, "value": 8},
                        "winner": "forbidden",
                    }
                }
            }
        return None

    def fake_all(_conn, sql: str, _params):
        if "committee_session_members" in sql:
            return [
                {
                    "id": "m1",
                    "user_id": 10,
                    "role_in_committee": "finance",
                    "is_voting": True,
                    "joined_at": None,
                }
            ]
        if "committee_deliberation_events" in sql:
            return []
        if "FROM dao_criteria" in sql:
            return []
        if "FROM supplier_bundles" in sql:
            return [
                {
                    "id": "bundle-1",
                    "vendor_name_raw": "Vendor A",
                    "bundle_status": "complete",
                    "completeness_score": 0.95,
                    "qualification_status": "qualified",
                    "assembled_at": None,
                }
            ]
        if "GROUP BY bundle_id" in sql:
            return [{"bundle_id": "bundle-1", "mn": 0.8}]
        if "FROM vendor_market_signals" in sql:
            return []
        if "FROM market_signals_v2" in sql:
            return []
        if "FROM source_package_documents" in sql:
            return []
        return []

    monkeypatch.setattr(pv_builder, "db_execute_one", fake_one)
    monkeypatch.setattr(pv_builder, "db_fetchall", fake_all)

    snapshot, seal_hash = pv_builder.build_pv_snapshot(
        conn=object(),
        workspace_id="ws-1",
        session_id="sid-1",
        user_id=10,
        seal_comment="ok",
    )
    for key in (
        "format_version",
        "dms_version",
        "generated_at",
        "process",
        "committee",
        "deliberation",
        "evaluation",
        "market_signals",
        "source_package",
        "decision",
        "meta",
        "seal",
    ):
        assert key in snapshot
    assert snapshot["meta"]["snapshot_schema_version"]
    assert snapshot["meta"]["generated_from_session_id"] == "sid-1"
    assert len(seal_hash) == 64
    assert _canonical_hash(snapshot) == seal_hash
    assert "winner" not in snapshot["evaluation"]["scores_matrix"]["bundle-1"]
    assert "weighted_scores" not in str(snapshot).lower()


def _base_fake_one():
    """Shared workspace + session + evaluation stubs for PV snapshot tests."""

    def fake_one(_conn, sql: str, _params):
        if "FROM process_workspaces" in sql:
            return {
                "id": "ws-1",
                "reference_code": "REF-1",
                "title": "Test",
                "process_type": "devis_simple",
                "zone": "MLI",
                "zone_id": "MLI-MOPTI",
                "category": "med",
                "estimated_value": 1000,
                "currency": "XOF",
                "humanitarian_context": True,
                "tenant_id": "tenant-1",
                "status": "in_deliberation",
            }
        if "FROM committee_sessions" in sql:
            return {
                "id": "sid-1",
                "workspace_id": "ws-1",
                "tenant_id": "tenant-1",
                "session_status": "active",
                "min_members": 3,
            }
        if "FROM evaluation_documents" in sql:
            return {
                "scores_matrix": {
                    "bundle-1": {
                        "quality": {"score": 8, "value": 8},
                        "winner": "forbidden",
                    }
                }
            }
        return None

    return fake_one


def _pv_fetchall_common(_conn, sql: str, _params):
    """Retourne une liste si la requête est gérée ; sinon None (délégation VMS/MSv2)."""

    if "committee_session_members" in sql:
        return [
            {
                "id": "m1",
                "user_id": 10,
                "role_in_committee": "finance",
                "is_voting": True,
                "joined_at": None,
            }
        ]
    if "committee_deliberation_events" in sql:
        return []
    if "FROM dao_criteria" in sql:
        return []
    if "FROM supplier_bundles" in sql:
        return [
            {
                "id": "bundle-1",
                "vendor_name_raw": "Vendor A",
                "bundle_status": "complete",
                "completeness_score": 0.95,
                "qualification_status": "qualified",
                "assembled_at": None,
            }
        ]
    if "GROUP BY bundle_id" in sql:
        return [{"bundle_id": "bundle-1", "mn": 0.8}]
    if "FROM source_package_documents" in sql:
        return []
    return None


def test_pv_builder_msv2_fallback_source_type_and_mapping(monkeypatch) -> None:
    """VMS vide + zone_id → lignes MSv2 avec source_type msv2_fallback."""

    ts = datetime(2026, 4, 6, 12, 0, 0, tzinfo=UTC)

    def fake_all(_conn, sql: str, _params):
        out = _pv_fetchall_common(_conn, sql, _params)
        if out is not None:
            return out
        if "FROM vendor_market_signals" in sql:
            return []
        if "FROM market_signals_v2" in sql:
            return [
                {
                    "alert_level": "WARNING",
                    "residual_pct": 12.5,
                    "item_id": "ITEM-1",
                    "zone_id": "MLI-MOPTI",
                    "price_avg": 100.0,
                    "signal_quality": "moderate",
                    "updated_at": ts,
                    "created_at": ts,
                }
            ]
        return []

    monkeypatch.setattr(pv_builder, "db_execute_one", _base_fake_one())
    monkeypatch.setattr(pv_builder, "db_fetchall", fake_all)

    snapshot, _ = pv_builder.build_pv_snapshot(
        conn=object(),
        workspace_id="ws-1",
        session_id="sid-1",
        user_id=10,
        seal_comment="ok",
    )
    assert len(snapshot["market_signals"]) == 1
    m = snapshot["market_signals"][0]
    assert m["source_type"] == "msv2_fallback"
    assert m["signal_type"] == "WARNING"
    assert m["relevance_score"] == 12.5
    assert m["data_points"]["item_id"] == "ITEM-1"
    assert m["data_points"]["zone_id"] == "MLI-MOPTI"
    assert m["surfaced_at"] == ts.isoformat()


def test_pv_builder_vendor_market_signals_sets_source_type_vms(monkeypatch) -> None:
    """VMS non vide → source_type vms (pas d’appel MSv2 nécessaire dans ce stub)."""

    ts = datetime(2026, 4, 6, 14, 0, 0, tzinfo=UTC)
    vms_row = {
        "signal_type": "price_anchor_update",
        "payload": {"relevance_score": 0.85, "note": "x"},
        "generated_at": ts,
    }

    def fake_all(_conn, sql: str, _params):
        out = _pv_fetchall_common(_conn, sql, _params)
        if out is not None:
            return out
        if "FROM vendor_market_signals" in sql:
            return [vms_row]
        if "FROM market_signals_v2" in sql:
            raise AssertionError("MSv2 must not be queried when VMS has rows")
        return []

    monkeypatch.setattr(pv_builder, "db_execute_one", _base_fake_one())
    monkeypatch.setattr(pv_builder, "db_fetchall", fake_all)

    snapshot, _ = pv_builder.build_pv_snapshot(
        conn=object(),
        workspace_id="ws-1",
        session_id="sid-1",
        user_id=10,
        seal_comment="ok",
    )
    assert len(snapshot["market_signals"]) == 1
    m = snapshot["market_signals"][0]
    assert m["source_type"] == "vms"
    assert m["signal_type"] == "price_anchor_update"
    assert m["relevance_score"] == 0.85
    assert m["surfaced_at"] == ts.isoformat()
