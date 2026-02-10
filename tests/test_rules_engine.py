"""Test business rules engine."""
import pytest
from backend.couche_a.rules_engine import (
    check_essential_criteria,
    score_capacity,
    score_durability,
    score_commercial,
)


def test_essential_pass():
    pa = [{"detected_type": "TECH"}, {"detected_type": "FIN"}]
    ok, reasons = check_essential_criteria(pa)
    assert ok is True
    assert reasons == []


def test_essential_fail_missing_tech():
    pa = [{"detected_type": "FIN"}]
    ok, reasons = check_essential_criteria(pa)
    assert ok is False
    assert "Missing technical offer document" in reasons


def test_essential_fail_missing_fin():
    pa = [{"detected_type": "TECH"}]
    ok, reasons = check_essential_criteria(pa)
    assert ok is False
    assert "Missing financial offer document" in reasons


def test_essential_fail_missing_both():
    pa = [{"detected_type": "AUTRE"}]
    ok, reasons = check_essential_criteria(pa)
    assert ok is False
    assert len(reasons) == 2


def test_score_capacity_full():
    pa = [
        {"detected_type": "TECH", "doc_checklist": {"has_technical": True}, "vendor_name": "Test"}
    ]
    s = score_capacity(pa)
    assert s == 40.0


def test_score_capacity_partial():
    pa = [{"detected_type": "AUTRE", "doc_checklist": {}, "vendor_name": None}]
    s = score_capacity(pa)
    assert 0.0 <= s < 40.0


def test_score_durability():
    pa = [{"flags": {}}]
    s = score_durability(pa)
    assert s == 20.0


def test_score_commercial_full():
    pa = [{"detected_type": "FIN", "amount": "1000000"}]
    s = score_commercial(pa)
    assert s == 40.0


def test_score_commercial_no_fin():
    pa = [{"detected_type": "TECH", "amount": None}]
    s = score_commercial(pa)
    assert s == 0.0
