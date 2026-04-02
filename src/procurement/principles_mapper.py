"""9 principes — PrinciplesComplianceMap."""

from __future__ import annotations

from typing import Any

from src.procurement.compliance_models_m13 import (
    DurabilityAssessment,
    ImplementingRule,
    PrincipleAssessment,
    PrinciplesComplianceMap,
    ProcedureRequirements,
    ProcurementPrinciple,
    RegulatoryRegime,
)
from src.procurement.document_ontology import ProcurementFamily
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader


class PrinciplesMapper:
    def __init__(self, config_loader: RegulatoryConfigLoader) -> None:
        self.config = config_loader

    def map_principles(
        self,
        regime: RegulatoryRegime,
        requirements: ProcedureRequirements,
    ) -> PrinciplesComplianceMap:
        fw = regime.framework.value
        bundle = self.config.load_framework_bundle(fw)
        pm = (bundle.get("principles_mapping") or {}).get("principle_mappings") or {}

        assessments: list[PrincipleAssessment] = []
        for principle in ProcurementPrinciple:
            assessments.append(
                self._assess_one(principle, pm.get(principle.value) or {}, regime)
            )

        summary = [f"{p.principle.value}: {p.status}" for p in assessments]
        return PrinciplesComplianceMap(
            principles=assessments,
            executive_summary_lines=summary,
            sustainability_highlight=self._sustainability_line(assessments),
            durability_highlight=self._durability_line(assessments),
        )

    def _assess_one(
        self,
        principle: ProcurementPrinciple,
        mapping: dict[str, Any],
        regime: RegulatoryRegime,
    ) -> PrincipleAssessment:
        rules: list[ImplementingRule] = []
        for rule_def in mapping.get("rules_implementing") or []:
            rules.append(
                ImplementingRule(
                    rule_name=rule_def.get("rule", "rule"),
                    description=rule_def.get("description", ""),
                    contribution=rule_def.get("contribution", "medium"),
                    active_in_this_case=True,
                    condition=rule_def.get("condition"),
                )
            )
        coverage = mapping.get("coverage", "none")
        status = self._coverage_to_status(coverage)
        gap = mapping.get("gap")

        durability = None
        if principle == ProcurementPrinciple.FIT_FOR_PURPOSE:
            durability = self._durability(mapping, regime)

        return PrincipleAssessment(
            principle=principle,
            status=status,
            implementing_rules=rules,
            gap_description=gap,
            durability_assessment=durability,
        )

    def _coverage_to_status(self, coverage: str) -> str:
        return {
            "full": "fully_addressed",
            "partial": "partially_addressed",
            "minimal": "minimally_addressed",
            "none": "not_addressed",
        }.get(coverage, "not_assessable")

    def _durability(
        self, ffp_mapping: dict[str, Any], regime: RegulatoryRegime
    ) -> DurabilityAssessment:
        fam = regime.procurement_family
        if fam not in (ProcurementFamily.GOODS, ProcurementFamily.WORKS):
            return DurabilityAssessment(
                applicable=False,
                durability_coverage="none",
                durability_gap=f"Not applicable for {fam.value}",
            )
        indicators = ffp_mapping.get("durability_indicators") or []
        drules: list[ImplementingRule] = []
        for ind in indicators:
            active = fam.value in ind.get("active_for_families", [])
            drules.append(
                ImplementingRule(
                    rule_name=ind.get("rule", ""),
                    description=ind.get("description", ""),
                    contribution=ind.get("contribution", "medium"),
                    active_in_this_case=active,
                )
            )
        return DurabilityAssessment(
            applicable=True,
            durability_rules_active=drules,
            durability_coverage=ffp_mapping.get("durability_coverage", "none"),
            durability_gap=ffp_mapping.get("durability_gap"),
        )

    def _sustainability_line(self, assessments: list[PrincipleAssessment]) -> str:
        for a in assessments:
            if a.principle == ProcurementPrinciple.SUSTAINABILITY:
                return a.gap_description or a.status
        return ""

    def _durability_line(self, assessments: list[PrincipleAssessment]) -> str:
        for a in assessments:
            if a.principle == ProcurementPrinciple.FIT_FOR_PURPOSE:
                d = a.durability_assessment
                if d and d.applicable:
                    return d.durability_coverage
        return ""
