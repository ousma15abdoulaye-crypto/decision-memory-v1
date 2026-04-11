"""M16 dans le modèle comparatif dérivé du snapshot PV."""

from __future__ import annotations

from src.services.comparative_table_model import (
    build_comparative_table_model_from_snapshot,
)
from src.services.pv_builder import SNAPSHOT_SCHEMA_VERSION


def test_comparative_model_from_snapshot_carries_m16() -> None:
    snap = {
        "process": {"workspace_id": "w1"},
        "evaluation": {
            "criteria": [],
            "bundles": [],
            "scores_matrix": {},
            "m16": {
                "domains": [
                    {"id": "d1", "code": "tech", "label": "Tech", "display_order": 0}
                ],
                "assessments": [
                    {
                        "id": "a1",
                        "bundle_id": "b1",
                        "criterion_key": "price",
                        "assessment_status": "draft",
                        "confidence": None,
                        "cell_json": {"score": 1},
                    }
                ],
                "price_lines": [],
                "price_values": [],
            },
        },
        "m14_proof": {"score_history": [], "decision_snapshots": []},
        "m13_proof": {"regulatory_profile_latest": None},
        "meta": {
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "render_template_version": "pv-1.0",
            "generated_from_session_id": "sid",
            "workspace_id": "w1",
        },
    }
    ct = build_comparative_table_model_from_snapshot(snap)
    assert ct.get("m16") is not None
    assert ct["m16"]["assessments"][0]["criterion_key"] == "price"
