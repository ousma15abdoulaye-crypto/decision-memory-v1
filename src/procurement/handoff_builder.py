"""
M12 V6 — Handoff Builder (H1/H2/H3).

Builds structured handoffs for M13 (regulatory) and M14 (evaluation + market).
Handoffs PREPARE data — they never APPLY rules (S18).
"""

from __future__ import annotations

import re
from pathlib import Path

from src.procurement.document_ontology import (
    SOURCE_RULES_KINDS,
    DocumentKindParent,
    ProcurementFamily,
    ProcurementFamilySub,
    ProcurementFramework,
)
from src.procurement.monetary_normalizer import (
    classify_dgmp_tier,
    normalize_monetary_value,
)
from src.procurement.procedure_models import (
    AtomicCapabilitySkeleton,
    EligibilityGateExtracted,
    M12Handoffs,
    MarketContextSignal,
    RegulatoryProfileSkeleton,
    ScoringStructureDetected,
)

_CURRENCY_PATTERN = re.compile(r"\b(FCFA|XOF|USD|EUR|CFA)\b", re.IGNORECASE)
_ZONE_PATTERN = re.compile(
    r"\b(Bamako|Mopti|Ségou|Sikasso|Koulikoro|Kayes|Gao|Tombouctou"
    r"|Kidal|Ménaka|Taoudénit|Niamey|Ouagadougou|Dakar)\b",
    re.IGNORECASE,
)
_MATERIAL_PATTERN = re.compile(
    r"\b(ciment|fer\s*[àa]\s*b[eé]ton|gravier|sable|bois|t[oô]le|peinture|brique)\b",
    re.IGNORECASE,
)

# SCI-specific signal patterns
_SCI_CONDITIONS = re.compile(
    r"conditions\s+g[eé]n[eé]rales\s+d.achat|general\s+conditions\s+of\s+purchase",
    re.IGNORECASE,
)
_SCI_SUSTAINABILITY = re.compile(
    r"sustainability|d[eé]veloppement\s+durable|environnement",
    re.IGNORECASE,
)
_SCI_IAPG = re.compile(r"IAPG|intolerable\s+acts", re.IGNORECASE)
_SCI_SANCTIONS = re.compile(r"sanctions?\s+clause|non[- ]sanctions?", re.IGNORECASE)

# DGMP-specific signal patterns
_DGMP_PROCEDURE = re.compile(
    r"appel\s+d.offres?\s+(ouvert|restreint|national|international)",
    re.IGNORECASE,
)
_DGMP_THRESHOLD = re.compile(
    r"seuil\s+de\s+passation|threshold|montant\s+sup[eé]rieur\s+[aà]",
    re.IGNORECASE,
)


def _read_sci_thresholds_framework_key_from_repo() -> str | None:
    """Lit ``framework`` dans ``config/regulatory/sci/thresholds.yaml`` (Gate A / P0-H1)."""
    path = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "regulatory"
        / "sci"
        / "thresholds.yaml"
    )
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("framework:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _build_h1_regulatory(
    framework: ProcurementFramework,
    framework_confidence: float,
    text: str,
    family: ProcurementFamily | None = None,
) -> RegulatoryProfileSkeleton:
    """Build H1: Regulatory Profile Skeleton."""
    sci_signals: list[str] = []
    dgmp_signals: list[str] = []

    if _SCI_CONDITIONS.search(text):
        sci_signals.append("general_conditions_referenced")
    if _SCI_SUSTAINABILITY.search(text):
        sci_signals.append("sustainability_referenced")
    if _SCI_IAPG.search(text):
        sci_signals.append("iapg_referenced")
    if _SCI_SANCTIONS.search(text):
        sci_signals.append("sanctions_clause_present")

    dgmp_proc = _DGMP_PROCEDURE.search(text)
    dgmp_proc_type = dgmp_proc.group(1) if dgmp_proc else None
    if _DGMP_THRESHOLD.search(text):
        dgmp_signals.append("threshold_referenced")

    sustainability_pct = None
    pct_match = re.search(
        r"(\d{1,3})\s*%\s*(?:sustainability|durable)", text, re.IGNORECASE
    )
    if pct_match:
        sustainability_pct = float(pct_match.group(1))

    # Détection tier DGMP via normalisation monétaire.
    # La famille influe sur les seuils DGMP Art. 45-46 (travaux ≠ biens/services).
    dgmp_threshold_tier: str | None = None
    if framework == ProcurementFramework.DGMP_MALI:
        monetary_values = normalize_monetary_value(text)
        if monetary_values:
            largest = monetary_values[0]
            dgmp_family = (
                "works" if family == ProcurementFamily.WORKS else "goods_services"
            )
            dgmp_threshold_tier = classify_dgmp_tier(largest.amount_fcfa, dgmp_family)
            dgmp_signals.append(f"tier_{dgmp_threshold_tier}_detected")

    if framework == ProcurementFramework.SCI:
        yaml_fw = _read_sci_thresholds_framework_key_from_repo()
        if yaml_fw:
            sci_signals.append(f"regulatory_yaml_framework={yaml_fw}")

    return RegulatoryProfileSkeleton(
        framework_detected=framework,
        framework_confidence=framework_confidence,
        sci_signals_detected=sci_signals,
        sci_conditions_referenced=bool(_SCI_CONDITIONS.search(text)),
        sci_sustainability_pct_detected=sustainability_pct,
        sci_iapg_referenced=bool(_SCI_IAPG.search(text)),
        sci_sanctions_clause_present=bool(_SCI_SANCTIONS.search(text)),
        dgmp_signals_detected=dgmp_signals,
        dgmp_procedure_type_detected=dgmp_proc_type,
        dgmp_threshold_tier_detected=dgmp_threshold_tier,
    )


def _build_h2_capability(
    family: ProcurementFamily,
    family_sub: ProcurementFamilySub,
    gates: list[EligibilityGateExtracted],
    scoring: ScoringStructureDetected | None,
) -> AtomicCapabilitySkeleton:
    """Build H2: Atomic Capability Skeleton."""
    active: list[str] = []
    inactive: list[str] = []

    all_sections = [
        "methodology",
        "team_composition",
        "qa_plan",
        "ethics_plan",
        "workplan",
        "warehouse_capacity",
        "equipment_list",
        "delivery_schedule",
        "experience_references",
        "financial_capacity",
    ]

    if family == ProcurementFamily.CONSULTANCY:
        active = [
            "methodology",
            "team_composition",
            "qa_plan",
            "workplan",
            "experience_references",
        ]
        inactive = ["warehouse_capacity", "equipment_list", "delivery_schedule"]
    elif family == ProcurementFamily.GOODS:
        active = ["delivery_schedule", "experience_references", "financial_capacity"]
        inactive = ["methodology", "team_composition", "qa_plan", "workplan"]
    elif family == ProcurementFamily.WORKS:
        active = [
            "methodology",
            "equipment_list",
            "workplan",
            "experience_references",
            "financial_capacity",
        ]
        inactive = ["team_composition"]
    elif family == ProcurementFamily.SERVICES:
        active = ["methodology", "experience_references", "financial_capacity"]
        inactive = ["warehouse_capacity", "equipment_list"]
    else:
        active = all_sections
        inactive = []

    return AtomicCapabilitySkeleton(
        procurement_family=family,
        procurement_family_sub=family_sub,
        active_capability_sections=active,
        inactive_capability_sections=inactive,
        eligibility_checklist=gates,
        scoring_structure=scoring,
    )


def _build_h3_market(text: str) -> MarketContextSignal:
    """Build H3: Market Context Signal."""
    currency_match = _CURRENCY_PATTERN.search(text)
    currency = currency_match.group(1).upper() if currency_match else None

    prices_detected = bool(re.search(r"\d{1,3}(?:[.\s]\d{3})+|\d{4,}", text))

    price_basis = None
    if re.search(r"\bHT\b|hors\s+taxes", text, re.IGNORECASE):
        price_basis = "HT"
    elif re.search(r"\bTTC\b|toutes\s+taxes", text, re.IGNORECASE):
        price_basis = "TTC"

    zones = list({m.group(1) for m in _ZONE_PATTERN.finditer(text)})
    materials = list({m.group(1).lower() for m in _MATERIAL_PATTERN.finditer(text)})

    return MarketContextSignal(
        prices_detected=prices_detected,
        currency_detected=currency,
        price_basis_detected=price_basis,  # type: ignore[arg-type]
        material_price_index_applicable=bool(materials),
        material_categories_detected=materials,
        zone_for_price_reference=zones,
    )


def build_handoffs(
    document_kind: DocumentKindParent,
    framework: ProcurementFramework,
    framework_confidence: float,
    family: ProcurementFamily,
    family_sub: ProcurementFamilySub,
    gates: list[EligibilityGateExtracted],
    scoring: ScoringStructureDetected | None,
    text: str,
) -> M12Handoffs:
    """Build all applicable handoffs for a document."""
    h1: RegulatoryProfileSkeleton | None = None
    h2: AtomicCapabilitySkeleton | None = None
    h3: MarketContextSignal | None = None

    if document_kind in SOURCE_RULES_KINDS:
        h1 = _build_h1_regulatory(framework, framework_confidence, text, family=family)
        h2 = _build_h2_capability(family, family_sub, gates, scoring)
    elif framework != ProcurementFramework.UNKNOWN:
        h1 = _build_h1_regulatory(framework, framework_confidence, text, family=family)

    h3 = _build_h3_market(text)
    if (
        not h3.prices_detected
        and not h3.material_categories_detected
        and not h3.zone_for_price_reference
    ):
        h3 = None

    return M12Handoffs(
        regulatory_profile_skeleton=h1,
        atomic_capability_skeleton=h2,
        market_context_signal=h3,
    )
