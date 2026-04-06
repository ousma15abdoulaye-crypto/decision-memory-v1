from __future__ import annotations

from src.services import pv_builder


def test_pv_builder_has_9_blocks_and_kill_list_absent(monkeypatch) -> None:
    def fake_one(_conn, sql: str, _params):
        if "FROM process_workspaces" in sql:
            return {
                "id": "ws-1",
                "reference_code": "REF-1",
                "title": "Test",
                "process_type": "devis_simple",
                "zone": "MLI",
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
        "seal",
    ):
        assert key in snapshot
    assert len(seal_hash) == 64
    assert "winner" not in snapshot["evaluation"]["scores_matrix"]["bundle-1"]
    assert "weighted_scores" not in str(snapshot).lower()
