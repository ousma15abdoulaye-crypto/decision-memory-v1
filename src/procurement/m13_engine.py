"""M13 — RegulatoryComplianceEngine (déterministe)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.procurement.benchmark_status_service import BenchmarkStatusService
from src.procurement.compliance_gate_assembler import (
    ComplianceGateAssembler,
    build_gates_summary,
)
from src.procurement.compliance_models_m13 import (
    ComplianceCheckItem,
    ComplianceChecklist,
    EvaluationBlueprint,
    M13Meta,
    M13Output,
    M13RegulatoryComplianceReport,
)
from src.procurement.derogation_assessor import DerogationAssessor
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.m12_reconstruct import build_m12_output_from_pass_outputs
from src.procurement.m13_confidence import m13_discretize_confidence
from src.procurement.m13_persistence_payload import (
    build_m13_regulatory_profile_persist_payload,
)
from src.procurement.m13_regulatory_profile_repository import (
    M13RegulatoryProfileRepository,
)
from src.procurement.ocds_coverage_builder import build_ocds_default
from src.procurement.principles_mapper import PrinciplesMapper
from src.procurement.procedure_models import M12Output
from src.procurement.regime_resolver import RegimeResolver
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader
from src.procurement.regulatory_yaml_validity import RegulatoryYamlValidityLoader
from src.procurement.requirements_instantiator import RequirementsInstantiator


class RegulatoryComplianceEngine:
    def __init__(
        self,
        config_loader: RegulatoryConfigLoader | None = None,
        validity_loader: RegulatoryYamlValidityLoader | None = None,
        repository: Any = None,
        benchmark_service: BenchmarkStatusService | None = None,
    ) -> None:
        self.config_loader = config_loader or RegulatoryConfigLoader()
        self.validity_loader = validity_loader or RegulatoryYamlValidityLoader()
        self.repository = repository
        self.resolver = RegimeResolver(self.config_loader)
        self.instantiator = RequirementsInstantiator(
            self.config_loader, self.validity_loader
        )
        self.assembler = ComplianceGateAssembler()
        self.derogation = DerogationAssessor(self.config_loader)
        self.principles = PrinciplesMapper(self.config_loader)
        self.benchmark = benchmark_service or BenchmarkStatusService()

    def process_m12(
        self,
        *,
        case_id: str,
        document_id: str,
        m12: M12Output,
    ) -> M13Output:
        skeleton = m12.handoffs.regulatory_profile_skeleton
        if skeleton is None:
            raise ValueError("M13 requires regulatory_profile_skeleton (H1)")

        recognition = m12.procedure_recognition
        m12_gates = m12.document_conformity_signal.gates

        regime = self.resolver.resolve(skeleton, recognition)
        requirements = self.instantiator.instantiate(regime)
        validity_rules = requirements.document_validity_rules

        gates = self.assembler.assemble(
            list(m12_gates),
            requirements,
            validity_rules,
        )
        gates_summary = build_gates_summary(gates)

        derogations = self.derogation.assess(regime, recognition, requirements)
        principles_map = self.principles.map_principles(regime, requirements)
        ocds = build_ocds_default()

        transition = self.benchmark.evaluate_transition()
        mode = self.config_loader.get_m13_mode()

        review_required = (
            regime.framework == ProcurementFramework.UNKNOWN
            or mode == "bootstrap"
            or m13_discretize_confidence(skeleton.framework_confidence) == 0.6
        )

        report = M13RegulatoryComplianceReport(
            regime=regime,
            procedure_requirements=requirements,
            compliance_gates=gates,
            gates_summary=gates_summary,
            applicable_derogations=derogations,
            principles_compliance_map=principles_map,
            ocds_process_coverage=ocds,
            m13_meta=M13Meta(
                mode=mode if mode in ("bootstrap", "production") else "bootstrap",
                mode_transition_eligible=transition.transition_eligible,
                benchmark_status_summary=(
                    f"{len(transition.met_criteria)} met, "
                    f"{len(transition.blocking_criteria)} blocking"
                ),
                processing_timestamp=datetime.now(UTC).isoformat(),
                framework_resolved=regime.framework.value,
                confidence_floor=regime.confidence,
                review_required=review_required,
            ),
        )

        checklist = self._build_checklist(case_id, regime, gates, validity_rules)
        blueprint = self._build_blueprint(
            case_id, regime, requirements, principles_map, ocds, validity_rules
        )

        out = M13Output(
            report=report,
            compliance_checklist=checklist,
            evaluation_blueprint=blueprint,
        )
        if self.repository is not None:
            persist = build_m13_regulatory_profile_persist_payload(
                out,
                case_id=case_id,
                document_id=document_id,
            )
            self.repository.save_payload(case_id=case_id, payload=persist)
        return out

    def _build_checklist(
        self,
        case_id: str,
        regime: Any,
        gates: list[Any],
        validity_rules: list[Any],
    ) -> ComplianceChecklist:
        per_offer: list[ComplianceCheckItem] = []
        case_level: list[ComplianceCheckItem] = []
        expiry_count = 0
        for gate in gates:
            scope = (
                "per_offer"
                if gate.gate_category
                in ("eligibility", "administrative", "document_validity")
                else "case_level"
            )
            matching_rule = next(
                (
                    r
                    for r in validity_rules
                    if r.admin_subtype == gate.expected_admin_subtype
                ),
                None,
            )
            if gate.gate_category == "document_validity":
                expiry_count += 1
            item = ComplianceCheckItem(
                check_id=gate.gate_id,
                check_name=gate.gate_name,
                check_scope=scope,
                verification_method=gate.verification_method,
                is_eliminatory=gate.is_eliminatory,
                is_regularizable=gate.is_regularizable,
                normative_reference=gate.normative_reference,
                expiry_rule=matching_rule,
            )
            if scope == "per_offer":
                per_offer.append(item)
            else:
                case_level.append(item)

        return ComplianceChecklist(
            case_id=case_id,
            framework=regime.framework.value,
            procedure_type=regime.procedure_type.value,
            per_offer_checks=per_offer,
            case_level_checks=case_level,
            total_checks=len(per_offer) + len(case_level),
            eliminatory_checks=sum(1 for g in gates if g.is_eliminatory),
            regularizable_checks=sum(1 for g in gates if g.is_regularizable),
            expiry_checks=expiry_count,
        )

    def _build_blueprint(
        self,
        case_id: str,
        regime: Any,
        requirements: Any,
        principles_map: Any,
        ocds: Any,
        validity_rules: list[Any],
    ) -> EvaluationBlueprint:
        ev = requirements.evaluation_requirements
        return EvaluationBlueprint(
            evaluation_method=ev.evaluation_method,
            technical_weight=ev.technical_weight,
            financial_weight=ev.financial_weight,
            sustainability_weight=ev.sustainability_weight,
            minimum_bids=requirements.minimum_bids.minimum_bids,
            ocds_process_coverage=ocds,
            principles_summary=principles_map.executive_summary_lines,
            document_validity_rules=list(validity_rules),
            procedure_requirements_ref=(
                f"m13_regulatory_profile_versions/{case_id}/latest"
            ),
        )


def run_m13_from_pass_json(
    *,
    case_id: str,
    document_id: str,
    pass_1a: dict[str, Any],
    pass_1b: dict[str, Any],
    pass_1c: dict[str, Any],
    pass_1d: dict[str, Any],
) -> M13Output:
    m12 = build_m12_output_from_pass_outputs(
        pass_1a_data=pass_1a,
        pass_1b_data=pass_1b,
        pass_1c_data=pass_1c,
        pass_1d_data=pass_1d,
    )
    engine = RegulatoryComplianceEngine(
        repository=M13RegulatoryProfileRepository(),
    )
    return engine.process_m12(case_id=case_id, document_id=document_id, m12=m12)
