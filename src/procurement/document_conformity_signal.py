"""
M12 V6 L6 — Document Conformity Signal.

Produces document-level conformity status and gates.
"""

from __future__ import annotations

from typing import Literal

from src.procurement.document_ontology import (
    OFFER_KINDS,
    DocumentKindParent,
)
from src.procurement.procedure_models import (
    DocumentConformitySignal,
    DocumentValidity,
    GateResult,
    TracedField,
)


def _determine_offer_composition(
    document_kind: DocumentKindParent,
    is_composite: str,
) -> Literal[
    "standalone_offer",
    "technical_only",
    "financial_only",
    "technical_plus_financial_expected",
    "multi_document_offer",
    "not_an_offer",
    "unknown",
]:
    if document_kind not in OFFER_KINDS:
        return "not_an_offer"
    if document_kind == DocumentKindParent.OFFER_COMBINED:
        return "standalone_offer"
    if is_composite == "yes":
        return "multi_document_offer"
    if document_kind == DocumentKindParent.OFFER_TECHNICAL:
        return "technical_only"
    if document_kind == DocumentKindParent.OFFER_FINANCIAL:
        return "financial_only"
    return "unknown"


def _build_gates(
    document_kind: DocumentKindParent,
    validity_status: str,
    mandatory_coverage: float,
) -> list[GateResult]:
    """Build conformity gates based on document type and validity."""
    gates: list[GateResult] = []

    # Gate: document identity resolved
    identity_ok = document_kind != DocumentKindParent.UNKNOWN
    gates.append(
        GateResult(
            gate_name="document_identity_resolved",
            gate_state="PASSED" if identity_ok else "FAILED",
            gate_value=identity_ok,
            confidence=1.0 if identity_ok else 0.60,
            evidence=f"kind={document_kind.value}",
        )
    )

    # Gate: validity assessment
    if validity_status in ("valid", "partial"):
        gates.append(
            GateResult(
                gate_name="validity_assessed",
                gate_state="PASSED",
                gate_value=True,
                confidence=0.80,
                evidence=f"status={validity_status}",
            )
        )
    elif validity_status == "not_assessable":
        gates.append(
            GateResult(
                gate_name="validity_assessed",
                gate_state="NOT_APPLICABLE",
                gate_value=None,
                confidence=1.0,
                evidence="not_assessable",
            )
        )
    else:
        gates.append(
            GateResult(
                gate_name="validity_assessed",
                gate_state="FAILED",
                gate_value=False,
                confidence=0.80,
                evidence=f"status={validity_status}",
            )
        )

    # Gate: mandatory coverage threshold (>= 50% for partial conformity)
    coverage_ok = mandatory_coverage >= 0.50
    gates.append(
        GateResult(
            gate_name="mandatory_coverage_threshold",
            gate_state="PASSED" if coverage_ok else "FAILED",
            gate_value=coverage_ok,
            confidence=0.80,
            evidence=f"coverage={mandatory_coverage:.2f}",
        )
    )

    return gates


def compute_conformity_signal(
    document_kind: DocumentKindParent,
    is_composite: str,
    validity: DocumentValidity,
) -> DocumentConformitySignal:
    """Compute document-level conformity signal from recognition + validity."""
    offer_comp = _determine_offer_composition(document_kind, is_composite)
    validity_status = validity.document_validity_status.value

    gates = _build_gates(document_kind, validity_status, validity.mandatory_coverage)

    all_passed = all(g.gate_state in ("PASSED", "NOT_APPLICABLE") for g in gates)
    any_failed = any(g.gate_state == "FAILED" for g in gates)

    if all_passed and validity_status == "valid":
        conformity_status: Literal[
            "conforme", "non_conforme", "partiellement_conforme", "non_statuable"
        ] = "conforme"
        conf = 0.85
    elif validity_status == "not_assessable":
        conformity_status = "non_statuable"
        conf = 0.60
    elif any_failed:
        conformity_status = "non_conforme"
        conf = 0.80
    else:
        conformity_status = "partiellement_conforme"
        conf = 0.70

    grounds: list[str] = []
    if validity_status != "valid":
        grounds.append(f"validity={validity_status}")
    for g in gates:
        if g.gate_state == "FAILED":
            grounds.append(f"gate_failed={g.gate_name}")

    return DocumentConformitySignal(
        offer_composition_hint=TracedField(
            value=offer_comp,
            confidence=0.80 if document_kind != DocumentKindParent.UNKNOWN else 0.50,
            evidence=[f"kind={document_kind.value}", f"composite={is_composite}"],
        ),
        document_conformity_status=TracedField(
            value=conformity_status,
            confidence=conf,
            evidence=grounds or ["all_gates_passed"],
        ),
        document_scope=TracedField(
            value="document_only",
            confidence=1.0,
            evidence=["m12_scope"],
        ),
        gates=gates,
        grounds=grounds,
    )
