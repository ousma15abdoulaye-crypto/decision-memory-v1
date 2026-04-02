"""R3 — Compliance Gate Assembly (4 phases)."""

from __future__ import annotations

import re
from typing import Any

from src.procurement.compliance_models_m13 import (
    ComplianceGateAssembled,
    ComplianceGateSource,
    GatesSummary,
    ProcedureRequirements,
    ReconciliationStatus,
    RegulatoryDocumentValidityRule,
    VerificationMethod,
)
from src.procurement.m13_confidence import m13_discretize_confidence
from src.procurement.procedure_models import GateResult


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


class ComplianceGateAssembler:
    def assemble(
        self,
        m12_gates: list[GateResult],
        regulatory_rules: ProcedureRequirements,
        validity_rules: list[RegulatoryDocumentValidityRule],
    ) -> list[ComplianceGateAssembled]:
        assembled: list[ComplianceGateAssembled] = []
        reg_gates = self._extract_regulatory_gates(regulatory_rules)
        p1, used_reg = self._phase_1(m12_gates, reg_gates)
        assembled.extend(p1)
        assembled.extend(self._phase_2(reg_gates, used_reg))
        assembled.extend(self._phase_3(m12_gates, p1))
        assembled.extend(self._phase_4(validity_rules))
        return assembled

    def _extract_regulatory_gates(
        self, req: ProcedureRequirements
    ) -> list[dict[str, Any]]:
        gates: list[dict[str, Any]] = []
        for doc in (
            req.required_documents.supplier_documents
            + req.required_documents.buyer_documents
        ):
            gates.append(
                {
                    "name": _norm_name(doc.document_name),
                    "display": doc.document_name,
                    "category": "administrative",
                    "is_eliminatory": doc.is_eliminatory,
                    "verification_method": VerificationMethod.DOCUMENT_PRESENCE,
                    "reference": doc.normative_reference,
                }
            )
        return gates

    def _gates_match(self, m12: GateResult, reg: dict[str, Any]) -> bool:
        a = _norm_name(m12.gate_name)
        b = reg["name"]
        return a == b or a in b or b in a

    def _phase_1(
        self, m12_gates: list[GateResult], reg_gates: list[dict[str, Any]]
    ) -> tuple[list[ComplianceGateAssembled], set[str]]:
        matched: list[ComplianceGateAssembled] = []
        used_reg: set[str] = set()
        for m12_gate in m12_gates:
            for reg_gate in reg_gates:
                if self._gates_match(m12_gate, reg_gate):
                    matched.append(
                        ComplianceGateAssembled(
                            gate_id=f"matched_{m12_gate.gate_name}",
                            gate_name=m12_gate.gate_name,
                            gate_category="administrative",
                            source=ComplianceGateSource.BOTH,
                            reconciliation=ReconciliationStatus.MATCHED,
                            is_eliminatory=reg_gate["is_eliminatory"],
                            verification_method=reg_gate["verification_method"],
                            normative_reference=reg_gate["reference"],
                            confidence=m13_discretize_confidence(m12_gate.confidence),
                            evidence=[
                                m12_gate.evidence,
                                f"Regulatory: {reg_gate['reference'].description}",
                            ],
                        )
                    )
                    used_reg.add(reg_gate["name"])
                    break
        return matched, used_reg

    def _phase_2(
        self,
        reg_gates: list[dict[str, Any]],
        used_reg: set[str],
    ) -> list[ComplianceGateAssembled]:
        reg_only: list[ComplianceGateAssembled] = []
        for reg_gate in reg_gates:
            if reg_gate["name"] in used_reg:
                continue
            reg_only.append(
                ComplianceGateAssembled(
                    gate_id=f"reg_only_{reg_gate['name']}",
                    gate_name=reg_gate["display"],
                    gate_category="administrative",
                    source=ComplianceGateSource.REGULATORY_REQUIRED,
                    reconciliation=ReconciliationStatus.REGULATION_ONLY,
                    is_eliminatory=reg_gate["is_eliminatory"],
                    verification_method=reg_gate["verification_method"],
                    normative_reference=reg_gate["reference"],
                    confidence=1.0,
                    evidence=[
                        "Required by regulation but not matched to M12 gate name"
                    ],
                )
            )
        return reg_only

    def _phase_3(
        self,
        m12_gates: list[GateResult],
        phase1: list[ComplianceGateAssembled],
    ) -> list[ComplianceGateAssembled]:
        matched_m12 = {g.gate_name for g in phase1}
        doc_only: list[ComplianceGateAssembled] = []
        for m12_gate in m12_gates:
            if m12_gate.gate_name in matched_m12:
                continue
            doc_only.append(
                ComplianceGateAssembled(
                    gate_id=f"doc_only_{m12_gate.gate_name}",
                    gate_name=m12_gate.gate_name,
                    gate_category="eligibility",
                    source=ComplianceGateSource.DOCUMENT_DETECTED,
                    reconciliation=ReconciliationStatus.DOCUMENT_ONLY,
                    is_eliminatory=False,
                    verification_method=VerificationMethod.MANUAL_REVIEW,
                    confidence=m13_discretize_confidence(m12_gate.confidence * 0.8),
                    evidence=[
                        m12_gate.evidence,
                        "Detected in document but not in loaded regulations",
                    ],
                    conflict_requires_human_resolution=True,
                    conflict_description=(
                        "Gate found in document but not in regulatory config"
                    ),
                )
            )
        return doc_only

    def _phase_4(
        self, validity_rules: list[RegulatoryDocumentValidityRule]
    ) -> list[ComplianceGateAssembled]:
        validity_gates: list[ComplianceGateAssembled] = []
        for vr in validity_rules:
            if vr.no_expiry:
                continue
            validity_gates.append(
                ComplianceGateAssembled(
                    gate_id=f"{vr.framework}_{vr.admin_subtype}_expiry",
                    gate_name=f"Validity: {vr.document_name}",
                    gate_category="document_validity",
                    source=ComplianceGateSource.REGULATORY_REQUIRED,
                    reconciliation=ReconciliationStatus.REGULATION_ONLY,
                    is_eliminatory=vr.expiry_consequence == "rejection",
                    is_regularizable=vr.expiry_consequence == "regularization",
                    verification_method=VerificationMethod.EXPIRY_CHECK,
                    expected_admin_subtype=vr.admin_subtype,
                    normative_reference=vr.normative_reference,
                    confidence=1.0,
                    evidence=[
                        f"{vr.document_name}: validity rule loaded from YAML",
                    ],
                )
            )
        return validity_gates


def build_gates_summary(gates: list[ComplianceGateAssembled]) -> GatesSummary:
    return GatesSummary(
        total_gates=len(gates),
        eliminatory_gates=sum(1 for g in gates if g.is_eliminatory),
        regularizable_gates=sum(1 for g in gates if g.is_regularizable),
        matched_gates=sum(
            1 for g in gates if g.reconciliation == ReconciliationStatus.MATCHED
        ),
        regulation_only_gates=sum(
            1 for g in gates if g.reconciliation == ReconciliationStatus.REGULATION_ONLY
        ),
        document_only_gates=sum(
            1 for g in gates if g.reconciliation == ReconciliationStatus.DOCUMENT_ONLY
        ),
        conflict_gates=sum(
            1 for g in gates if g.reconciliation == ReconciliationStatus.CONFLICT
        ),
        document_validity_gates=sum(
            1 for g in gates if g.gate_category == "document_validity"
        ),
    )
