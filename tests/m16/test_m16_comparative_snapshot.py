"""M16 dans le modèle comparatif dérivé du snapshot PV."""

from __future__ import annotations

from src.services.comparative_table_model import (
    build_comparative_table_model_from_snapshot,
)


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
        "meta": {
            "snapshot_schema_version": "1.1",
            "render_template_version": "pv-1.0",
            "generated_from_session_id": "sid",
            "workspace_id": "w1",
        },
    }
    ct = build_comparative_table_model_from_snapshot(snap)
    assert ct.get("m16") is not None
    assert ct["m16"]["assessments"][0]["criterion_key"] == "price"
