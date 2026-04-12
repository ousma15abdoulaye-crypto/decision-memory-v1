"""Métriques pipeline V5 — séries Prometheus après observe_* (REGISTRY par défaut)."""

from __future__ import annotations

import pytest

pytest.importorskip("prometheus_client")


def test_pipeline_v5_counters_appear_in_registry_after_observe() -> None:
    from prometheus_client import REGISTRY, generate_latest

    from src.observability.pipeline_v5_metrics import (
        observe_mistral_key_missing,
        observe_pass1_hitl_bypass,
        observe_pipeline_v5_run,
    )

    observe_mistral_key_missing(phase="metrics_test")
    observe_pass1_hitl_bypass(workspace_id="00000000-0000-0000-0000-000000000099")
    observe_pipeline_v5_run(
        workspace_id="00000000-0000-0000-0000-000000000099",
        duration_seconds=1.5,
        assessments_created=2,
    )

    body = generate_latest(REGISTRY).decode("utf-8")
    for name in (
        "dms_pipeline_assessments_created_total",
        "dms_pipeline_duration_seconds",
        "dms_pipeline_empty_assessments_total",
        "dms_pipeline_mistral_key_missing_total",
        "dms_pass1_hitl_bypass_total",
    ):
        assert name in body, f"métrique absente : {name}"
