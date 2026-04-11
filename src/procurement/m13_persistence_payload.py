"""
Envelope JSONB pour ``m13_regulatory_profile_versions`` — cœur M13 + index + hooks M13B.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.procurement.compliance_models_m13 import M13Output
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.m13b_models import M13BHooksPayload

_SCHEMA_VERSION = "m13_regulatory_profile_envelope_v1"
_FRAMEWORK_CONFIG_SUBDIR = {
    ProcurementFramework.DGMP_MALI: "dgmp_mali",
    ProcurementFramework.SCI: "sci",
}


def _config_regulatory_prefix(framework: ProcurementFramework) -> str:
    sub = _FRAMEWORK_CONFIG_SUBDIR.get(framework)
    if not sub:
        return "config/regulatory/unknown"
    return f"config/regulatory/{sub}"


def build_m13_regulatory_profile_persist_payload(
    out: M13Output,
    *,
    case_id: str,
    document_id: str,
) -> dict[str, Any]:
    """Construit le dict persisté : M13 complet + index (seuils + hooks M13B vides sous ``profile_index``)."""
    regime = out.report.regime
    tier = regime.threshold_tier
    src = tier.source
    hooks = M13BHooksPayload()

    rules_applied: list[dict[str, Any]] = [
        {
            "rule_id": f"threshold_{tier.tier_name}",
            "source_file": f"{_config_regulatory_prefix(regime.framework)}/thresholds.yaml",
            "source_section": tier.tier_name,
            "source_reference": (src.article or "")
            + (f" {src.section}" if src.section else ""),
            "value": tier.min_value,
            "unit": tier.currency,
            "applied_because": (
                "; ".join(regime.evidence)[:2000] if regime.evidence else ""
            ),
            "result": f"procedure_type={regime.procedure_type.value}",
        }
    ]

    hooks_json = hooks.model_dump(mode="json")

    return {
        "schema_version": _SCHEMA_VERSION,
        "case_id": case_id,
        "document_id": document_id,
        "persisted_at": datetime.now(UTC).isoformat(),
        "profile_index": {
            "framework": regime.framework.value,
            "framework_version": "regulatory_yaml_bundle_v1",
            "procedure_type": regime.procedure_type.value,
            "rules_applied": rules_applied,
            "m13b": hooks_json,
        },
        "m13": out.model_dump(mode="json"),
    }
