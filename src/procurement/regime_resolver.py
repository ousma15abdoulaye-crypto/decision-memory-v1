"""R1 — Regime Resolution (YAML + M12 H1 / ProcedureRecognition)."""

from __future__ import annotations

import logging
from typing import Any

from src.procurement.compliance_models_m13 import (
    NormativeReference,
    RegulatoryProcedureType,
    RegulatoryRegime,
    ThresholdTier,
)
from src.procurement.document_ontology import ProcurementFamily, ProcurementFramework
from src.procurement.m13_confidence import m13_discretize_confidence
from src.procurement.procedure_models import (
    ProcedureRecognition,
    RegulatoryProfileSkeleton,
)
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader

logger = logging.getLogger(__name__)


def _threshold_family_key(
    framework: ProcurementFramework, family: ProcurementFamily
) -> str:
    if framework == ProcurementFramework.DGMP_MALI:
        return "works" if family == ProcurementFamily.WORKS else "goods"
    if family == ProcurementFamily.WORKS:
        return "works"
    return "default"


class RegimeResolver:
    def __init__(self, config_loader: RegulatoryConfigLoader) -> None:
        self.config = config_loader

    def resolve(
        self,
        skeleton: RegulatoryProfileSkeleton,
        recognition: ProcedureRecognition,
    ) -> RegulatoryRegime:
        framework = skeleton.framework_detected
        fam_raw = recognition.procurement_family.value
        try:
            family = ProcurementFamily(fam_raw)
        except ValueError:
            family = ProcurementFamily.UNKNOWN

        ev = recognition.estimated_value_detected.value
        value = float(ev) if isinstance(ev, int | float) else None
        cur_raw = recognition.currency_detected.value
        currency = str(cur_raw) if cur_raw is not None else None

        if framework == ProcurementFramework.UNKNOWN:
            return self._unknown_regime(skeleton, recognition, family, value, currency)

        if framework == ProcurementFramework.MIXED:
            return self._mixed_regime(skeleton, recognition, family, value, currency)

        return self._resolve_single(
            framework, skeleton, recognition, family, value, currency
        )

    def _resolve_single(
        self,
        framework: ProcurementFramework,
        skeleton: RegulatoryProfileSkeleton,
        recognition: ProcedureRecognition,
        family: ProcurementFamily,
        value: float | None,
        currency: str | None,
    ) -> RegulatoryRegime:
        fw = framework.value
        bundle = self.config.load_framework_bundle(fw)
        thresholds_root = bundle.get("thresholds") or {}
        key = _threshold_family_key(framework, family)
        thresholds_block = thresholds_root.get(key) or thresholds_root.get("default")
        if not thresholds_block:
            logger.warning("[M13] no thresholds for %s/%s", fw, key)
            return self._unknown_regime(skeleton, recognition, family, value, currency)

        tier = self._resolve_threshold(
            thresholds_block, family, value, currency or "XOF", fw
        )
        proc = self._procedure_from_tier(tier)
        refs = self._collect_refs(thresholds_block, tier, proc)
        conf_raw = skeleton.framework_confidence
        return RegulatoryRegime(
            framework=framework,
            procurement_family=family,
            estimated_value=value,
            currency=currency,
            threshold_tier=tier,
            procedure_type=proc,
            normative_references=refs,
            confidence=m13_discretize_confidence(conf_raw),
            evidence=[
                f"Framework: {fw}",
                f"Tier: {tier.tier_name}",
                f"Procedure: {proc.value}",
            ],
        )

    def _mixed_regime(
        self,
        skeleton: RegulatoryProfileSkeleton,
        recognition: ProcedureRecognition,
        family: ProcurementFamily,
        value: float | None,
        currency: str | None,
    ) -> RegulatoryRegime:
        keys = list(skeleton.other_framework_signals.keys())
        if not keys:
            keys = ["sci", "dgmp_mali"]
        regimes: list[RegulatoryRegime] = []
        for fw_str in keys:
            try:
                fw = ProcurementFramework(fw_str)
            except ValueError:
                continue
            sub = skeleton.model_copy(update={"framework_detected": fw})
            regimes.append(
                self._resolve_single(fw, sub, recognition, family, value, currency)
            )
        if not regimes:
            return self._unknown_regime(skeleton, recognition, family, value, currency)
        strictest = max(regimes, key=self._strictness_key)
        strictest = strictest.model_copy(
            update={
                "is_mixed_framework": True,
                "mixed_resolution_strategy": (
                    "Most strict framework applied. Compared: " + ", ".join(keys)
                ),
            }
        )
        return strictest

    def _strictness_key(self, regime: RegulatoryRegime) -> tuple[int, float, str, str]:
        """Clé de tri stable (pas de hash() — PYTHONHASHSEED rendrait MIXED non déterministe)."""
        fw = regime.framework.value
        bundle = self.config.load_framework_bundle(fw)
        req = bundle.get("required_documents") or {}
        sup = req.get("supplier_documents") or {}
        common = sup.get("common") or []
        n = sum(1 for d in common if d.get("is_eliminatory"))
        tier = regime.threshold_tier
        return (n, tier.min_value, tier.tier_name, fw)

    def _unknown_regime(
        self,
        skeleton: RegulatoryProfileSkeleton,
        recognition: ProcedureRecognition,
        family: ProcurementFamily,
        value: float | None,
        currency: str | None,
    ) -> RegulatoryRegime:
        return RegulatoryRegime(
            framework=ProcurementFramework.UNKNOWN,
            procurement_family=family,
            estimated_value=value,
            currency=currency,
            threshold_tier=ThresholdTier(
                tier_name="unknown",
                min_value=0.0,
                max_value=None,
                currency="unknown",
                procedure_required="unknown",
                source=NormativeReference(
                    framework="unknown",
                    description="Framework not resolved",
                ),
            ),
            procedure_type=RegulatoryProcedureType.UNKNOWN,
            normative_references=[],
            confidence=m13_discretize_confidence(0.3),
            evidence=["Framework UNKNOWN — degraded output"],
        )

    def _resolve_threshold(
        self,
        thresholds_block: dict[str, Any],
        family: ProcurementFamily,
        value: float | None,
        currency: str,
        fw_name: str,
    ) -> ThresholdTier:
        tiers = (thresholds_block.get("tiers") or []) if thresholds_block else []
        if value is None and tiers:
            # Valeur absente : palier le plus exigeant (dernier tier = typ. AO ouvert)
            return self._tier_to_model(tiers[-1], currency, fw_name)
        if not tiers:
            return ThresholdTier(
                tier_name="fallback",
                min_value=0.0,
                max_value=None,
                currency=currency,
                procedure_required="unknown",
                source=NormativeReference(framework=fw_name, description="fallback"),
            )
        for tier in tiers:
            min_v = float(tier.get("min_value", 0))
            max_v = tier.get("max_value")
            max_f = float("inf") if max_v is None else float(max_v)
            if max_v is None:
                if value is None or value >= min_v:
                    return self._tier_to_model(tier, currency, fw_name)
            elif value is not None and min_v <= value < max_f:
                return self._tier_to_model(tier, currency, fw_name)
        return self._tier_to_model(tiers[-1], currency, fw_name)

    def _tier_to_model(
        self, tier: dict[str, Any], currency: str, fw_name: str
    ) -> ThresholdTier:
        max_v = tier.get("max_value")
        return ThresholdTier(
            tier_name=tier["name"],
            min_value=float(tier.get("min_value", 0)),
            max_value=None if max_v is None else float(max_v),
            currency=tier.get("currency", currency),
            procedure_required=str(tier.get("procedure_required", "unknown")),
            source=NormativeReference(
                framework=fw_name,
                article=tier.get("article"),
                description=tier.get("description", ""),
            ),
        )

    def _procedure_from_tier(self, tier: ThresholdTier) -> RegulatoryProcedureType:
        try:
            return RegulatoryProcedureType(tier.procedure_required)
        except ValueError:
            return RegulatoryProcedureType.UNKNOWN

    def _collect_refs(
        self,
        thresholds_block: dict[str, Any],
        tier: ThresholdTier,
        proc: RegulatoryProcedureType,
    ) -> list[NormativeReference]:
        refs = [tier.source]
        return refs
