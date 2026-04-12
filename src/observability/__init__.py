"""Observabilité DMS (métriques pipeline, compatibilité optionnelle Prometheus)."""

from src.observability.pipeline_v5_metrics import (
    observe_mistral_key_missing,
    observe_pass1_hitl_bypass,
    observe_pipeline_v5_run,
)

__all__ = [
    "observe_mistral_key_missing",
    "observe_pass1_hitl_bypass",
    "observe_pipeline_v5_run",
]
