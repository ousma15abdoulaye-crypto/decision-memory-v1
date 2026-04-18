"""P3.3 — tests du normalisateur prix commercial."""

import pytest

from src.core.models import SupplierPackage
from src.couche_a.scoring.commercial_normalizer import qualify_supplier_commercial_price
from src.couche_a.scoring.qualified_price import (
    PriceAmbiguousError,
    PriceLevel,
    QualificationConfidence,
    TaxBasis,
)


def _supplier(**kwargs) -> SupplierPackage:
    base = dict(
        offer_ids=["offer_1"],
        documents=[],
        package_status="COMPLETE",
        has_financial=True,
        has_technical=True,
        has_admin=True,
        extracted_data={},
        missing_fields=[],
    )
    base.update(kwargs)
    return SupplierPackage(**base)


def test_qualify_ttc_total_ok():
    s = _supplier(
        supplier_name="A",
        extracted_data={"total_price": "1 234 567 XOF TTC", "currency": "XOF"},
    )
    qp = qualify_supplier_commercial_price(s, case_currency="XOF")
    assert qp is not None
    assert qp.tax_basis == TaxBasis.TTC
    assert qp.price_level == PriceLevel.OFFER_TOTAL
    assert qp.amount == 1234567.0
    assert qp.currency == "XOF"
    assert qp.confidence == QualificationConfidence.HIGH


def test_qualify_no_tax_signal_returns_none():
    s = _supplier(
        supplier_name="B",
        extracted_data={"total_price": "500 XOF", "currency": "XOF"},
    )
    assert qualify_supplier_commercial_price(s, case_currency="XOF") is None


def test_qualify_ht_ttc_ambiguous_raises():
    s = _supplier(
        supplier_name="C",
        extracted_data={
            "total_price": "500 XOF HT TTC",
            "total_price_source": "",
            "currency": "XOF",
        },
    )
    with pytest.raises(PriceAmbiguousError) as ei:
        qualify_supplier_commercial_price(s, case_currency="XOF")
    assert "HT_TTC_AMBIGUOUS" in ei.value.codes


def test_qualify_currency_mismatch_raises():
    s = _supplier(
        supplier_name="D",
        extracted_data={"total_price": "100 EUR TTC", "currency": "EUR"},
    )
    with pytest.raises(PriceAmbiguousError) as ei:
        qualify_supplier_commercial_price(s, case_currency="XOF")
    assert "CURRENCY_MISMATCH" in ei.value.codes


def test_qualify_line_sum_mismatch_raises():
    lines = [
        {"line_total": 100.0, "line_total_check": "OK"},
        {"line_total": 100.0, "line_total_check": "OK"},
    ]
    s = _supplier(
        supplier_name="E",
        extracted_data={
            "total_price": "500 XOF TTC",
            "currency": "XOF",
            "line_items": lines,
        },
    )
    with pytest.raises(PriceAmbiguousError) as ei:
        qualify_supplier_commercial_price(s, case_currency="XOF")
    assert "OFFER_TOTAL_LINE_SUM_MISMATCH" in ei.value.codes


def test_qualify_mixed_ok_and_anomaly_lines_yields_medium_confidence():
    """Lignes OK + ANOMALY → drapeaux ligne → confiance MEDIUM (grille P3.3)."""
    lines = [
        {"line_total": 500.0, "line_total_check": "OK"},
        {"line_total": 1.0, "line_total_check": "ANOMALY"},
    ]
    s = _supplier(
        supplier_name="G",
        extracted_data={
            "total_price": "500 XOF TTC",
            "currency": "XOF",
            "line_items": lines,
        },
    )
    qp = qualify_supplier_commercial_price(s, case_currency="XOF")
    assert qp is not None
    assert qp.confidence == QualificationConfidence.MEDIUM


def test_qualify_line_sum_within_tolerance_ok():
    lines = [{"line_total": 1000.0, "line_total_check": "OK"}]
    s = _supplier(
        supplier_name="F",
        extracted_data={
            "total_price": "1000 XOF TTC",
            "currency": "XOF",
            "line_items": lines,
        },
    )
    qp = qualify_supplier_commercial_price(s, case_currency="XOF")
    assert qp is not None
    assert qp.amount == 1000.0
    assert qp.confidence == QualificationConfidence.HIGH
