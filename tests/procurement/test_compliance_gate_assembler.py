"""Tests — ComplianceGateAssembler (4 phases) + build_gates_summary."""

from __future__ import annotations

from src.procurement.compliance_gate_assembler import (
    ComplianceGateAssembler,
    build_gates_summary,
)
from src.procurement.compliance_models_m13 import (
    ComplianceGateSource,
    EvaluationRequirements,
    GuaranteeRequirements,
    MinimumBidsRequirement,
    NormativeReference,
    ProcedureRequirements,
    ReconciliationStatus,
    RegulatoryDocumentValidityRule,
    RegulatoryProcedureType,
    RegulatoryRegime,
    RequiredDocument,
    RequiredDocumentSet,
    ThresholdTier,
    TimelineRequirements,
    VerificationMethod,
)
from src.procurement.document_ontology import ProcurementFamily, ProcurementFramework
from src.procurement.procedure_models import GateResult

# ── Fixtures ────────────────────────────────────────────────────


def _ref(fw: str = "sci", desc: str = "test") -> NormativeReference:
    return NormativeReference(framework=fw, description=desc)


def _tier() -> ThresholdTier:
    return ThresholdTier(
        tier_name="tier_1",
        min_value=0.0,
        max_value=50000.0,
        currency="XOF",
        procedure_required="request_for_quotation",
        source=_ref(),
    )


def _regime() -> RegulatoryRegime:
    return RegulatoryRegime(
        framework=ProcurementFramework.SCI,
        procurement_family=ProcurementFamily.GOODS,
        threshold_tier=_tier(),
        procedure_type=RegulatoryProcedureType.REQUEST_FOR_QUOTATION,
        confidence=0.8,
    )


def _requirements(
    supplier_docs: list[RequiredDocument] | None = None,
    buyer_docs: list[RequiredDocument] | None = None,
) -> ProcedureRequirements:
    return ProcedureRequirements(
        regime=_regime(),
        required_documents=RequiredDocumentSet(
            supplier_documents=supplier_docs or [],
            buyer_documents=buyer_docs or [],
        ),
        timeline_requirements=TimelineRequirements(),
        evaluation_requirements=EvaluationRequirements(
            evaluation_method="lowest_price"
        ),
        guarantee_requirements=GuaranteeRequirements(),
        minimum_bids=MinimumBidsRequirement(),
    )


def _gate(name: str, confidence: float = 0.85, evidence: str = "doc") -> GateResult:
    return GateResult(
        gate_name=name,
        gate_state="PASSED",
        confidence=confidence,
        evidence=evidence,
    )


def _supplier_doc(name: str, is_eliminatory: bool = False) -> RequiredDocument:
    return RequiredDocument(
        document_name=name,
        is_eliminatory=is_eliminatory,
        normative_reference=_ref(desc=name),
    )


# ── Phase 1: Matched gates ─────────────────────────────────────


class TestPhase1Matched:
    def test_exact_name_match(self) -> None:
        assembler = ComplianceGateAssembler()
        m12 = [_gate("fiscal_clearance")]
        reqs = _requirements(supplier_docs=[_supplier_doc("fiscal_clearance", True)])
        result = assembler.assemble(m12, reqs, [])
        matched = [
            g for g in result if g.reconciliation == ReconciliationStatus.MATCHED
        ]
        assert len(matched) == 1
        assert matched[0].source == ComplianceGateSource.BOTH
        assert matched[0].is_eliminatory is True

    def test_partial_name_match(self) -> None:
        assembler = ComplianceGateAssembler()
        m12 = [_gate("fiscal")]
        reqs = _requirements(supplier_docs=[_supplier_doc("fiscal_clearance")])
        result = assembler.assemble(m12, reqs, [])
        matched = [
            g for g in result if g.reconciliation == ReconciliationStatus.MATCHED
        ]
        assert len(matched) >= 1

    def test_no_match(self) -> None:
        assembler = ComplianceGateAssembler()
        m12 = [_gate("random_gate")]
        reqs = _requirements(supplier_docs=[_supplier_doc("fiscal_clearance")])
        result = assembler.assemble(m12, reqs, [])
        matched = [
            g for g in result if g.reconciliation == ReconciliationStatus.MATCHED
        ]
        assert len(matched) == 0


# ── Phase 2: Regulation-only ────────────────────────────────────


class TestPhase2RegulationOnly:
    def test_reg_only_gate(self) -> None:
        assembler = ComplianceGateAssembler()
        m12: list[GateResult] = []
        reqs = _requirements(supplier_docs=[_supplier_doc("tax_receipt", True)])
        result = assembler.assemble(m12, reqs, [])
        reg_only = [
            g
            for g in result
            if g.reconciliation == ReconciliationStatus.REGULATION_ONLY
        ]
        assert len(reg_only) == 1
        assert reg_only[0].source == ComplianceGateSource.REGULATORY_REQUIRED
        assert reg_only[0].confidence == 1.0


# ── Phase 3: Document-only ──────────────────────────────────────


class TestPhase3DocumentOnly:
    def test_doc_only_gate(self) -> None:
        assembler = ComplianceGateAssembler()
        m12 = [_gate("unknown_gate", confidence=0.7)]
        reqs = _requirements()
        result = assembler.assemble(m12, reqs, [])
        doc_only = [
            g for g in result if g.reconciliation == ReconciliationStatus.DOCUMENT_ONLY
        ]
        assert len(doc_only) == 1
        assert doc_only[0].conflict_requires_human_resolution is True
        assert doc_only[0].verification_method == VerificationMethod.MANUAL_REVIEW


# ── Phase 4: Validity rules ─────────────────────────────────────


class TestPhase4Validity:
    def test_validity_gate_created(self) -> None:
        assembler = ComplianceGateAssembler()
        rules = [
            RegulatoryDocumentValidityRule(
                framework="sci",
                admin_subtype="fiscal_clearance",
                document_name="Attestation Fiscale",
                validity_period_months=3,
                no_expiry=False,
                expiry_consequence="rejection",
                normative_reference=_ref(desc="Art. 45"),
            )
        ]
        result = assembler.assemble([], _requirements(), rules)
        validity = [g for g in result if g.gate_category == "document_validity"]
        assert len(validity) == 1
        assert validity[0].verification_method == VerificationMethod.EXPIRY_CHECK
        assert validity[0].is_eliminatory is True

    def test_no_expiry_skipped(self) -> None:
        assembler = ComplianceGateAssembler()
        rules = [
            RegulatoryDocumentValidityRule(
                framework="sci",
                admin_subtype="rc",
                document_name="Registre Commerce",
                no_expiry=True,
                expiry_consequence="warning",
                normative_reference=_ref(),
            )
        ]
        result = assembler.assemble([], _requirements(), rules)
        validity = [g for g in result if g.gate_category == "document_validity"]
        assert len(validity) == 0


# ── build_gates_summary ─────────────────────────────────────────


class TestGatesSummary:
    def test_summary_counts(self) -> None:
        assembler = ComplianceGateAssembler()
        m12 = [_gate("fiscal_clearance"), _gate("orphan_gate")]
        reqs = _requirements(
            supplier_docs=[
                _supplier_doc("fiscal_clearance", True),
                _supplier_doc("tax_receipt"),
            ]
        )
        rules = [
            RegulatoryDocumentValidityRule(
                framework="sci",
                admin_subtype="fc",
                document_name="FC",
                validity_period_months=6,
                no_expiry=False,
                expiry_consequence="regularization",
                normative_reference=_ref(),
            )
        ]
        gates = assembler.assemble(m12, reqs, rules)
        summary = build_gates_summary(gates)
        assert summary.total_gates == len(gates)
        assert summary.total_gates >= 4
        assert summary.matched_gates >= 1
        assert summary.document_only_gates >= 1
        assert summary.regulation_only_gates >= 1
        assert summary.document_validity_gates >= 1

    def test_empty_gates(self) -> None:
        summary = build_gates_summary([])
        assert summary.total_gates == 0
