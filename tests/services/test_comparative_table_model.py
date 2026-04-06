"""Modèle tableau comparatif — dérivé snapshot / kill list."""

from __future__ import annotations

import pytest

from src.services.comparative_table_model import (
    build_comparative_table_model_from_snapshot,
)
from src.services.pv_builder import SNAPSHOT_SCHEMA_VERSION, validate_pv_snapshot


def test_validate_pv_snapshot_rejects_forbidden_key_in_scores() -> None:
    bad = {
        "process": {"workspace_id": "w1"},
        "committee": {"session_id": "s1"},
        "deliberation": {"total_events": 0, "events": []},
        "evaluation": {
            "criteria": [],
            "bundles": [],
            "scores_matrix": {"b1": {"rank": 1}},
        },
        "decision": {"sealed_by": "1", "sealed_at": "2026-01-01T00:00:00+00:00"},
        "meta": {
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "render_template_version": "pv-1.0",
            "generated_from_session_id": "s1",
            "workspace_id": "w1",
        },
    }
    with pytest.raises(ValueError, match="interdits"):
        validate_pv_snapshot(bad)


def test_build_comparative_table_model_from_snapshot_trace() -> None:
    snap = {
        "process": {"workspace_id": "w1"},
        "evaluation": {
            "criteria": [{"id": "c1", "name": "N", "weight": 1.0}],
            "bundles": [{"id": "b1", "supplier_name_display": "S"}],
            "scores_matrix": {"b1": {"c1": {"score": 1, "value": 1}}},
        },
        "meta": {
            "snapshot_schema_version": "1.1",
            "render_template_version": "pv-1.0",
            "generated_from_session_id": "sid-x",
            "workspace_id": "w1",
        },
    }
    ct = build_comparative_table_model_from_snapshot(snap)
    assert ct["source"] == "pv_snapshot_sealed"
    assert ct["trace"]["generated_from_session_id"] == "sid-x"
    assert "winner" not in str(ct["scores_matrix"])
