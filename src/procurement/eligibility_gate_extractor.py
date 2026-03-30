"""
M12 V6 L6 sub — Eligibility Gate Extractor.

Extracts eligibility gates from source_rules documents (DAO, ITT, RFQ).
"""

from __future__ import annotations

import re

from src.procurement.procedure_models import EligibilityGateExtracted

_GATE_PATTERNS: list[tuple[str, str, str | None, bool, re.Pattern[str]]] = [
    (
        "nif_required",
        "administrative",
        "nif",
        True,
        re.compile(r"NIF|num[eé]ro\s+d.identification\s+fiscale", re.IGNORECASE),
    ),
    (
        "rccm_required",
        "administrative",
        "rccm",
        True,
        re.compile(r"RCCM|registre\s+du\s+commerce", re.IGNORECASE),
    ),
    (
        "rib_required",
        "administrative",
        "rib",
        True,
        re.compile(r"RIB|relev[eé]\s+d.identit[eé]\s+bancaire", re.IGNORECASE),
    ),
    (
        "quitus_fiscal_required",
        "administrative",
        "quitus_fiscal",
        True,
        re.compile(r"quitus\s+fiscal", re.IGNORECASE),
    ),
    (
        "cert_non_faillite_required",
        "administrative",
        "cert_non_faillite",
        True,
        re.compile(r"certificat\s+de\s+non[- ]faillite|non[- ]faillite", re.IGNORECASE),
    ),
    (
        "sci_conditions_signed",
        "eligibility",
        "sci_conditions_signed",
        True,
        re.compile(
            r"conditions\s+g[eé]n[eé]rales\s+d.achat|general\s+conditions",
            re.IGNORECASE,
        ),
    ),
    (
        "sanctions_cert_required",
        "eligibility",
        "sanctions_cert",
        True,
        re.compile(
            r"sanctions?|d[eé]claration\s+de\s+non[- ]sanctions?", re.IGNORECASE
        ),
    ),
    (
        "caution_soumission",
        "financial_minimum",
        "caution_soumission",
        True,
        re.compile(
            r"caution\s+de\s+soumission|bid\s+bond|garantie\s+de\s+soumission",
            re.IGNORECASE,
        ),
    ),
    (
        "visite_site_obligatoire",
        "eliminatory",
        "attestation_visite",
        True,
        re.compile(r"visite\s+(?:de\s+)?(?:site|lieux)\s+obligatoire", re.IGNORECASE),
    ),
    (
        "licence_required",
        "qualification",
        "licence",
        False,
        re.compile(r"licence|agr[eé]ment|autorisation\s+d.exercice", re.IGNORECASE),
    ),
]


def extract_eligibility_gates(text: str) -> list[EligibilityGateExtracted]:
    """Extract eligibility gates from a source_rules document text."""
    if not text or not text.strip():
        return []

    gates: list[EligibilityGateExtracted] = []

    for gate_name, gate_type, doc_required, is_elim, pattern in _GATE_PATTERNS:
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            evidence_snippet = text[start:end].strip()

            gates.append(
                EligibilityGateExtracted(
                    gate_name=gate_name,
                    gate_type=gate_type,  # type: ignore[arg-type]
                    document_source_required=doc_required,  # type: ignore[arg-type]
                    is_eliminatory=is_elim,
                    confidence=0.80,
                    evidence=evidence_snippet[:200],
                )
            )

    return gates
