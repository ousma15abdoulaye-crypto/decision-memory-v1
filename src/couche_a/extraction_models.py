# src/couche_a/extraction_models.py
"""
Modèles de données extraction — DMS v4.1
Contrat de sortie du pipeline d'extraction.

Ces dataclasses sont le contrat entre :
  annotation-backend (JSON brut)
  → pipeline Couche A (données typées)
  → scoring, comité, exports Couche B

Règle : GO CTO obligatoire avant toute modification.
ADR-015 — ADR-M11-002 — Mandat 4 — 2026-03-17
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Tier(str, Enum):
    T1 = "tier_1_mistral_large"
    T2 = "tier_2_mistral_small"
    T3 = "tier_3_mistral_7b"
    T4_OFFLINE = "tier_4_offline"


@dataclass
class ExtractionField:
    """
    Champ extrait atomique — RÈGLE-19 DMS.
    confidence : 0.6 | 0.8 | 1.0 uniquement.
    evidence   : "p.N — fragment exact".
    """

    field_name: str
    value: Any
    confidence: float
    evidence: str
    tier_used: Tier = Tier.T1

    _ALLOWED = frozenset({0.6, 0.8, 1.0})

    def __post_init__(self) -> None:
        if self.confidence not in self._ALLOWED:
            raise ValueError(
                f"confidence={self.confidence} interdit. " f"Valeurs : {self._ALLOWED}"
            )
        if not self.evidence:
            raise ValueError(f"evidence vide sur champ '{self.field_name}'")


@dataclass
class LineItem:
    """
    Ligne de prix — ADR-015.
    line_total_check recalculé Python — jamais accepté du LLM.
    E-47.
    """

    item_line_no: int
    item_description_raw: str
    unit_raw: str
    quantity: float
    unit_price: float
    line_total: float
    line_total_check: str
    confidence: float
    evidence: str

    def __post_init__(self) -> None:
        # Recalcul mathématique côté Python — E-47
        if self.quantity and self.unit_price:
            expected = round(self.quantity * self.unit_price, 2)
            actual = round(self.line_total, 2)
            if actual == 0:
                self.line_total_check = "NON_VERIFIABLE"
            elif abs(expected - actual) / max(abs(actual), 1) <= 0.01:
                self.line_total_check = "OK"
            else:
                self.line_total_check = "ANOMALY"
        else:
            self.line_total_check = "NON_VERIFIABLE"

        if not self.unit_raw or not self.unit_raw.strip():
            self.unit_raw = "non_precise"


@dataclass
class TDRExtractionResult:
    """
    Résultat d'extraction complet — contrat pipeline DMS.

    extraction_ok=False → review_required obligatoire.
    Le système ne décide jamais seul en cas d'échec.
    """

    document_id: str
    document_role: str
    family_main: str
    family_sub: str
    taxonomy_core: str
    fields: list[ExtractionField] = field(default_factory=list)
    line_items: list[LineItem] = field(default_factory=list)
    gates: list[dict] = field(default_factory=list)
    ambiguites: list[str] = field(default_factory=list)
    tier_used: Tier = Tier.T1
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    extraction_ok: bool = True
    review_required: bool = False
    error_reason: str | None = None
    schema_version: str = "v3.0.1d"
    raw_annotation: dict | None = None

    def __post_init__(self) -> None:
        if not self.extraction_ok and not self.review_required:
            self.review_required = True
        if self.review_required:
            if "AMBIG-6_review_required" not in self.ambiguites:
                self.ambiguites.append("AMBIG-6_review_required")


def make_fallback_result(
    document_id: str,
    document_role: str,
    error_reason: str,
    tier: Tier = Tier.T4_OFFLINE,
) -> TDRExtractionResult:
    """
    Résultat vide traçable.
    Jamais silencieux. Toujours review_required.
    Le système renvoie à l'humain — ne décide pas.
    """
    return TDRExtractionResult(
        document_id=document_id,
        document_role=document_role,
        family_main="ABSENT",
        family_sub="ABSENT",
        taxonomy_core="ABSENT",
        fields=[],
        line_items=[],
        gates=[],
        ambiguites=[
            "AMBIG-6_review_required",
            f"AMBIG-6_{error_reason[:50]}",
        ],
        tier_used=tier,
        extraction_ok=False,
        review_required=True,
        error_reason=error_reason,
    )
