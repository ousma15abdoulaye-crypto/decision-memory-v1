"""
T1–T3 rectificatif CTO P3.3 — corpus de référence CASE-28b05d85 (équivalent UUID prod documenté).

T4 (faux cache) : tests/pipeline/test_pipeline_force_recompute.py
"""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from src.core.models import SupplierPackage
from src.couche_a.scoring.engine import ScoringEngine
from src.couche_a.scoring.qualified_price import (
    PriceLevel,
    QualificationConfidence,
    QualifiedPrice,
    TaxBasis,
)

# Référence CTO : workspace / case canonique documenté dans le dépôt
CASE_CANON = "CASE-28b05d85"
UUID_CANON_EQUIVALENT = "28b05d85-62f1-4101-aaec-96bac40905cd"


def _supplier(name: str, extracted: dict) -> SupplierPackage:
    return SupplierPackage(
        supplier_name=name,
        offer_ids=["offer_1"],
        documents=[],
        package_status="COMPLETE",
        has_financial=True,
        has_technical=True,
        has_admin=True,
        extracted_data=extracted,
        missing_fields=[],
    )


def test_t1_all_vendors_no_qualifiable_price_no_rescale_total_not_comparable():
    """T1 : aucun prix qualifiable pour tous → pas de rescale ; total non comparable."""
    engine = ScoringEngine()
    suppliers = [
        _supplier("V-A", {"total_price": "1000 XOF", "currency": "XOF"}),
        _supplier("V-B", {"total_price": "900 XOF", "currency": "XOF"}),
    ]
    profile: dict = {"criteria": []}

    commercial = engine._calculate_commercial_scores(
        suppliers, profile, currency="XOF", case_id=CASE_CANON
    )
    assert len(commercial) == 2
    assert all(s.calculation_details.get("p33_commercial_suppressed") for s in commercial)
    assert all(s.calculation_details.get("p33_commercial_score_semantic_null") for s in commercial)

    cap = engine._calculate_capacity_scores(suppliers, profile)
    sus = engine._calculate_sustainability_scores(suppliers, profile)
    ess = engine._calculate_essentials_scores(suppliers, profile)
    all_cat = commercial + cap + sus + ess

    weights = {"commercial": 0.5, "capacity": 0.3, "sustainability": 0.1, "essentials": 0.1}
    totals = engine._calculate_total_scores(
        suppliers, all_cat, profile, weights=weights, case_id=UUID_CANON_EQUIVALENT
    )
    assert len(totals) == 2
    for t in totals:
        assert t.calculation_details.get("total_not_comparable") is True
        assert t.calculation_details.get("p33_total_score_semantic_incomplete") is True
        w = t.calculation_details["weights"]
        assert abs(w["commercial"] - 0.5) < 1e-9
        assert abs(w["capacity"] - 0.3) < 1e-9


def test_t2_single_vendor_unqualified_cohort_flag_not_total_not_comparable():
    """T2 : un seul vendor sans prix qualifiable → cohorte incomplète, pas total_not_comparable."""
    engine = ScoringEngine()
    suppliers = [
        _supplier("V-OK", {"total_price": "1000 XOF TTC", "currency": "XOF"}),
        _supplier("V-BAD", {"total_price": "900 XOF", "currency": "XOF"}),
    ]
    profile: dict = {"criteria": []}

    commercial = engine._calculate_commercial_scores(
        suppliers, profile, currency="XOF", case_id=CASE_CANON
    )
    ok = next(s for s in commercial if s.supplier_name == "V-OK")
    bad = next(s for s in commercial if s.supplier_name == "V-BAD")
    assert ok.score_value > 0
    assert bad.calculation_details.get("p33_commercial_suppressed")
    assert bad.calculation_details.get("p33_commercial_score_semantic_null")

    cap = engine._calculate_capacity_scores(suppliers, profile)
    sus = engine._calculate_sustainability_scores(suppliers, profile)
    ess = engine._calculate_essentials_scores(suppliers, profile)
    all_cat = commercial + cap + sus + ess

    weights = {"commercial": 0.5, "capacity": 0.3, "sustainability": 0.1, "essentials": 0.1}
    totals = engine._calculate_total_scores(
        suppliers, all_cat, profile, weights=weights, case_id=CASE_CANON
    )
    for t in totals:
        assert t.calculation_details.get("total_not_comparable") is not True
        assert t.calculation_details.get("p33_total_cohort_commercial_incomplete") is True


def test_t3_confidence_enum_only_float_rejected():
    """T3 : confiance P3.3 — enum uniquement ; float libre rejeté par Pydantic."""
    qp_ok = QualifiedPrice(
        amount=1.0,
        currency="XOF",
        tax_basis=TaxBasis.TTC,
        price_level=PriceLevel.OFFER_TOTAL,
        confidence=QualificationConfidence.HIGH,
    )
    assert qp_ok.confidence == QualificationConfidence.HIGH

    bad_confidence = 0.75
    with pytest.raises(ValidationError):
        QualifiedPrice(
            amount=1.0,
            currency="XOF",
            tax_basis=TaxBasis.TTC,
            price_level=PriceLevel.OFFER_TOTAL,
            confidence=bad_confidence,
        )


def test_t3_logging_emits_structured_line(caplog: pytest.LogCaptureFixture) -> None:
    """Trace minimale : événement p33_commercial_suppressed dans les logs."""
    caplog.set_level(logging.INFO, logger="dms.p33")
    engine = ScoringEngine()
    suppliers = [
        _supplier("V-LOG", {"total_price": "100 XOF", "currency": "XOF"}),
    ]
    engine._calculate_commercial_scores(
        suppliers, {"criteria": []}, currency="XOF", case_id=CASE_CANON
    )
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "p33_commercial_suppressed" in joined
    assert CASE_CANON in joined
