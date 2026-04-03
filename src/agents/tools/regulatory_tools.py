"""
Regulatory Tools — wrappers deterministes des services M13 pour agents.

Chaque tool est invocable via ToolManifest.invoke() et testable sans LLM.
Les tools LLM-assisted (analyze_clause, assess_complex_derogation) sont
en mode review_required=True.
"""

from __future__ import annotations

from typing import Any

from src.agents.tools.tool_manifest import ToolCategory, ToolDescriptor, ToolManifest
from src.procurement.compliance_models_m13 import (
    NormativeReference,
    RegulatoryRegime,
)
from src.procurement.document_ontology import ProcurementFramework
from src.procurement.procedure_models import (
    ProcedureRecognition,
    RegulatoryProfileSkeleton,
    TracedField,
)
from src.procurement.regulatory_config_loader import RegulatoryConfigLoader


def _tf(value: Any = None, confidence: float = 0.8) -> TracedField:
    return TracedField(value=value, confidence=confidence)


def _default_ref() -> NormativeReference:
    return NormativeReference(framework="unknown", description="default")


# ══════════════════════════════════════════════════════════════════
# TOOL 1: resolve_regime
# ══════════════════════════════════════════════════════════════════

RESOLVE_REGIME_DESCRIPTOR = ToolDescriptor(
    name="resolve_regime",
    description=(
        "Given a framework, procurement family, estimated value, and currency, "
        "resolves the regulatory regime (threshold tier, procedure type)."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=True,
    input_schema={
        "type": "object",
        "properties": {
            "framework": {"type": "string"},
            "procurement_family": {"type": "string"},
            "estimated_value": {"type": "number", "nullable": True},
            "currency": {"type": "string", "default": "XOF"},
            "framework_confidence": {"type": "number", "default": 0.8},
        },
        "required": ["framework", "procurement_family"],
    },
)


def resolve_regime(
    framework: str,
    procurement_family: str,
    estimated_value: float | None = None,
    currency: str = "XOF",
    framework_confidence: float = 0.8,
) -> dict[str, Any]:
    from src.procurement.regime_resolver import RegimeResolver

    loader = RegulatoryConfigLoader()
    resolver = RegimeResolver(loader)
    try:
        fw = ProcurementFramework(framework)
    except ValueError:
        fw = ProcurementFramework.UNKNOWN

    skeleton = RegulatoryProfileSkeleton(
        framework_detected=fw,
        framework_confidence=framework_confidence,
        other_framework_signals={},
    )

    recognition_fields = {
        "framework_detected": _tf(framework),
        "procurement_family": _tf(procurement_family),
        "procurement_family_sub": _tf("general"),
        "document_kind": _tf("unknown"),
        "document_subtype": _tf("unknown"),
        "is_composite": _tf(False),
        "document_layer": _tf("unknown"),
        "document_stage": _tf("unknown"),
        "procedure_type": _tf("unknown"),
        "procedure_reference_detected": _tf(None),
        "issuing_entity_detected": _tf(None),
        "project_name_detected": _tf(None),
        "zone_scope_detected": _tf(None),
        "submission_deadline_detected": _tf(None),
        "submission_mode_detected": _tf(None),
        "result_type_detected": _tf(None),
        "estimated_value_detected": _tf(estimated_value),
        "currency_detected": _tf(currency),
        "visit_required": _tf(False),
        "sample_required": _tf(False),
        "humanitarian_context": _tf("no"),
        "recognition_source": _tf("agent_tool"),
        "review_status": _tf("ok"),
    }
    recognition = ProcedureRecognition(**recognition_fields)

    regime = resolver.resolve(skeleton, recognition)
    return regime.model_dump()


# ══════════════════════════════════════════════════════════════════
# TOOL 2: instantiate_requirements
# ══════════════════════════════════════════════════════════════════

INSTANTIATE_REQUIREMENTS_DESCRIPTOR = ToolDescriptor(
    name="instantiate_requirements",
    description=(
        "Given a resolved regime dict, instantiates procedure requirements "
        "(required documents, timelines, control organs, evaluation, guarantees)."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=True,
    input_schema={
        "type": "object",
        "properties": {"regime_dict": {"type": "object"}},
        "required": ["regime_dict"],
    },
)


def instantiate_requirements(regime_dict: dict[str, Any]) -> dict[str, Any]:
    from src.procurement.regulatory_yaml_validity import RegulatoryYamlValidityLoader
    from src.procurement.requirements_instantiator import RequirementsInstantiator

    loader = RegulatoryConfigLoader()
    validity_loader = RegulatoryYamlValidityLoader()
    instantiator = RequirementsInstantiator(loader, validity_loader)
    regime = RegulatoryRegime(**regime_dict)
    reqs = instantiator.instantiate(regime)
    return reqs.model_dump()


# ══════════════════════════════════════════════════════════════════
# TOOL 3: assemble_compliance_gates
# ══════════════════════════════════════════════════════════════════

ASSEMBLE_GATES_DESCRIPTOR = ToolDescriptor(
    name="assemble_compliance_gates",
    description=(
        "Assembles compliance gates from M12 gate results and regulatory requirements."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=True,
    input_schema={
        "type": "object",
        "properties": {
            "m12_gates": {"type": "array"},
            "requirements_dict": {"type": "object"},
        },
        "required": ["m12_gates", "requirements_dict"],
    },
)


def assemble_compliance_gates(
    m12_gates: list[dict[str, Any]],
    requirements_dict: dict[str, Any],
) -> dict[str, Any]:
    from src.procurement.compliance_gate_assembler import (
        ComplianceGateAssembler,
        build_gates_summary,
    )
    from src.procurement.compliance_models_m13 import ProcedureRequirements
    from src.procurement.procedure_models import GateResult

    assembler = ComplianceGateAssembler()
    gates_in = [GateResult(**g) for g in m12_gates]
    reqs = ProcedureRequirements(**requirements_dict)

    gates = assembler.assemble(gates_in, reqs, reqs.document_validity_rules)
    summary = build_gates_summary(gates)
    return {
        "gates": [g.model_dump() for g in gates],
        "summary": summary.model_dump(),
    }


# ══════════════════════════════════════════════════════════════════
# TOOL 4: assess_derogations
# ══════════════════════════════════════════════════════════════════

ASSESS_DEROGATIONS_DESCRIPTOR = ToolDescriptor(
    name="assess_derogations",
    description=(
        "Assesses applicable derogations given a regime and procedure recognition."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=True,
    input_schema={
        "type": "object",
        "properties": {
            "regime_dict": {"type": "object"},
            "recognition_dict": {"type": "object"},
            "requirements_dict": {"type": "object"},
        },
        "required": ["regime_dict", "recognition_dict", "requirements_dict"],
    },
)


def assess_derogations(
    regime_dict: dict[str, Any],
    recognition_dict: dict[str, Any],
    requirements_dict: dict[str, Any],
) -> list[dict[str, Any]]:
    from src.procurement.compliance_models_m13 import ProcedureRequirements
    from src.procurement.derogation_assessor import DerogationAssessor

    loader = RegulatoryConfigLoader()
    assessor = DerogationAssessor(loader)
    regime = RegulatoryRegime(**regime_dict)
    recognition = ProcedureRecognition(**recognition_dict)
    requirements = ProcedureRequirements(**requirements_dict)
    derogs = assessor.assess(regime, recognition, requirements)
    return [d.model_dump() for d in derogs]


# ══════════════════════════════════════════════════════════════════
# TOOL 5: map_principles
# ══════════════════════════════════════════════════════════════════

MAP_PRINCIPLES_DESCRIPTOR = ToolDescriptor(
    name="map_principles",
    description=(
        "Maps 9 procurement principles compliance for a given regime and requirements."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=True,
    input_schema={
        "type": "object",
        "properties": {
            "regime_dict": {"type": "object"},
            "requirements_dict": {"type": "object"},
        },
        "required": ["regime_dict", "requirements_dict"],
    },
)


def map_principles(
    regime_dict: dict[str, Any],
    requirements_dict: dict[str, Any],
) -> dict[str, Any]:
    from src.procurement.compliance_models_m13 import ProcedureRequirements
    from src.procurement.principles_mapper import PrinciplesMapper

    loader = RegulatoryConfigLoader()
    mapper = PrinciplesMapper(loader)
    regime = RegulatoryRegime(**regime_dict)
    requirements = ProcedureRequirements(**requirements_dict)
    pmap = mapper.map_principles(regime, requirements)
    return pmap.model_dump()


# ══════════════════════════════════════════════════════════════════
# TOOL 6: get_benchmark_status
# ══════════════════════════════════════════════════════════════════

BENCHMARK_STATUS_DESCRIPTOR = ToolDescriptor(
    name="get_benchmark_status",
    description=(
        "Returns current M13 benchmark status (bootstrap/production mode transition)."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=True,
    input_schema={"type": "object", "properties": {}},
)


def get_benchmark_status() -> dict[str, Any]:
    from src.procurement.benchmark_status_service import BenchmarkStatusService

    svc = BenchmarkStatusService()
    status = svc.compute_status()
    proposal = svc.evaluate_transition()
    return {
        "status": status.model_dump(),
        "transition_proposal": proposal.model_dump(),
    }


# ══════════════════════════════════════════════════════════════════
# TOOL 7: analyze_clause (LLM-assisted placeholder)
# ══════════════════════════════════════════════════════════════════

ANALYZE_CLAUSE_DESCRIPTOR = ToolDescriptor(
    name="analyze_clause",
    description=(
        "LLM-assisted: Analyzes a specific clause from a procurement document "
        "against regulatory requirements. Returns structured assessment."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=False,
    review_required=True,
    input_schema={
        "type": "object",
        "properties": {
            "clause_text": {"type": "string"},
            "framework": {"type": "string"},
            "context": {"type": "string"},
        },
        "required": ["clause_text", "framework"],
    },
)


def analyze_clause(
    clause_text: str,
    framework: str,
    context: str = "",
) -> dict[str, Any]:
    return {
        "review_required": True,
        "status": "placeholder",
        "message": "LLM-assisted tool — not yet wired to inference endpoint",
        "clause_length": len(clause_text),
        "framework": framework,
    }


# ══════════════════════════════════════════════════════════════════
# TOOL 8: assess_complex_derogation (LLM-assisted placeholder)
# ══════════════════════════════════════════════════════════════════

ASSESS_COMPLEX_DEROGATION_DESCRIPTOR = ToolDescriptor(
    name="assess_complex_derogation",
    description=(
        "LLM-assisted: Assesses complex derogation scenarios that require "
        "contextual reasoning beyond deterministic rules."
    ),
    category=ToolCategory.REGULATORY,
    deterministic=False,
    review_required=True,
    input_schema={
        "type": "object",
        "properties": {
            "derogation_context": {"type": "string"},
            "framework": {"type": "string"},
            "supporting_evidence": {"type": "array"},
        },
        "required": ["derogation_context", "framework"],
    },
)


def assess_complex_derogation(
    derogation_context: str,
    framework: str,
    supporting_evidence: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "review_required": True,
        "status": "placeholder",
        "message": "LLM-assisted tool — not yet wired to inference endpoint",
        "context_length": len(derogation_context),
        "framework": framework,
    }


# ══════════════════════════════════════════════════════════════════
# REGISTRY BUILDER
# ══════════════════════════════════════════════════════════════════


def build_default_manifest() -> ToolManifest:
    """Build and return the default ToolManifest with all regulatory tools."""
    manifest = ToolManifest()
    manifest.register(RESOLVE_REGIME_DESCRIPTOR, resolve_regime)
    manifest.register(INSTANTIATE_REQUIREMENTS_DESCRIPTOR, instantiate_requirements)
    manifest.register(ASSEMBLE_GATES_DESCRIPTOR, assemble_compliance_gates)
    manifest.register(ASSESS_DEROGATIONS_DESCRIPTOR, assess_derogations)
    manifest.register(MAP_PRINCIPLES_DESCRIPTOR, map_principles)
    manifest.register(BENCHMARK_STATUS_DESCRIPTOR, get_benchmark_status)
    manifest.register(ANALYZE_CLAUSE_DESCRIPTOR, analyze_clause)
    manifest.register(ASSESS_COMPLEX_DEROGATION_DESCRIPTOR, assess_complex_derogation)
    return manifest
