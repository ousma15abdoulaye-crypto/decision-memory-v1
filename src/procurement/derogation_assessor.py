"""R4 — Derogation Handling."""

from __future__ import annotations

from typing import Any

from src.procurement.compliance_models_m13 import (
    DerogationAssessment,
    DerogationType,
    NormativeReference,
    ProcedureRequirements,
    RegulatoryProcedureType,
    RegulatoryRegime,
)
from src.procurement.m13_confidence import m13_discretize_confidence
from src.procurement.procedure_models import ProcedureRecognition
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader


class DerogationAssessor:
    def __init__(self, config_loader: RegulatoryConfigLoader) -> None:
        self.config = config_loader

    def assess(
        self,
        regime: RegulatoryRegime,
        recognition: ProcedureRecognition,
        requirements: ProcedureRequirements,
    ) -> list[DerogationAssessment]:
        fw = regime.framework.value
        derog = self.config.load_derogations(fw)
        out: list[DerogationAssessment] = []

        hum_val = recognition.humanitarian_context.value
        hum_str = str(hum_val).lower() if hum_val is not None else ""
        if hum_str in ("yes", "true", "1"):
            out.append(self._humanitarian(derog, fw))

        if regime.procedure_type == RegulatoryProcedureType.SOLE_SOURCE:
            out.append(self._sole_source(derog, fw))

        if self._security_hint(recognition):
            out.append(self._security(derog, fw))

        return out

    def _security_hint(self, recognition: ProcedureRecognition) -> bool:
        z = recognition.zone_scope_detected.value
        if isinstance(z, str) and "gao" in z.lower():
            return True
        return False

    def _humanitarian(self, cfg: dict[str, Any], fw: str) -> DerogationAssessment:
        params = cfg.get("humanitarian_emergency") or cfg.get("emergency") or {}
        return DerogationAssessment(
            derogation_type=DerogationType.HUMANITARIAN_EMERGENCY,
            is_applicable=True,
            approval_required=str(params.get("approval_required", "Country Director")),
            approval_authority=str(params.get("approval_authority", "CD")),
            parameters_modified={
                "submission_period_days": f"reduced by {params.get('timeline_reduction_pct', 50)}%"
            },
            normative_reference=NormativeReference(
                framework=fw,
                article=params.get("article"),
                description=str(params.get("description", "Humanitarian emergency")),
            ),
            evidence=["humanitarian_context detected by M12"],
            confidence=m13_discretize_confidence(0.9),
        )

    def _sole_source(self, cfg: dict[str, Any], fw: str) -> DerogationAssessment:
        params = cfg.get("sole_source") or {}
        return DerogationAssessment(
            derogation_type=DerogationType.SOLE_SOURCE_JUSTIFIED,
            is_applicable=True,
            approval_required=str(params.get("approval_required", "PRMP")),
            approval_authority=str(params.get("approval_authority", "PRMP")),
            parameters_modified={},
            normative_reference=NormativeReference(
                framework=fw,
                article=params.get("article"),
                description=str(params.get("description", "Sole source")),
            ),
            evidence=["procedure_type sole_source"],
            confidence=0.8,
        )

    def _security(self, cfg: dict[str, Any], fw: str) -> DerogationAssessment:
        params = cfg.get("security_context") or {}
        return DerogationAssessment(
            derogation_type=DerogationType.SECURITY_CONTEXT,
            is_applicable=True,
            approval_required=str(params.get("approval_required", "SD+CD")),
            approval_authority=str(params.get("approval_authority", "SD+CD")),
            parameters_modified={},
            normative_reference=NormativeReference(
                framework=fw,
                description=str(params.get("description", "Security context")),
            ),
            evidence=["security zone hint"],
            confidence=0.6,
        )
