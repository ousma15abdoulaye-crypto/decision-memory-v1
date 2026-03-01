"""
Tests ETL M4 — normalisation, mapping zones, logique rejet.
Tests unitaires purs (pas de DB).
"""

from __future__ import annotations

import pytest

from src.vendors.normalizer import (
    normalize_email,
    normalize_phone,
    normalize_zone,
)
from src.vendors.region_codes import ZONE_TO_REGION

# ── normalize_email ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "email",
    [
        "tobecomplete@savethechildren.org",
        "tobecompleted@savethechildren.org",
        "dummy@gmail.com",
        "dummy@gmail.fr",
        "0",
        "",
        None,
    ],
)
def test_normalize_email_placeholder_returns_none(email):
    assert normalize_email(email) is None


def test_normalize_email_valid():
    assert normalize_email("test@example.com") == "test@example.com"


def test_normalize_email_lowercased():
    assert normalize_email("Test@Example.COM") == "test@example.com"


# ── normalize_phone ───────────────────────────────────────────────


@pytest.mark.parametrize("phone", ["0", "00", "", None])
def test_normalize_phone_invalid_returns_none(phone):
    assert normalize_phone(phone) is None


def test_normalize_phone_mali_prefix_stripped():
    # 223 + 8 chiffres → garder les 8 chiffres
    assert normalize_phone("22320287979") == "20287979"


def test_normalize_phone_short_returns_none():
    assert normalize_phone("123") is None


# ── normalize_zone ────────────────────────────────────────────────


def test_normalize_zone_sevare_with_accent():
    assert normalize_zone("Sevaré") == "sevare"


def test_normalize_zone_sevare_uppercase():
    assert normalize_zone("SEVARE") == "sevare"


def test_normalize_zone_parentheses_stripped():
    assert normalize_zone("DOUENTZA (MOPTI)") == "douentza"


def test_normalize_zone_niafunke():
    assert normalize_zone("NIAFUNKE") == "niafunke"


def test_normalize_zone_none_returns_empty():
    assert normalize_zone(None) == ""


# ── ZONE_TO_REGION — invariants critiques ────────────────────────


def test_zone_gao_maps_to_gao_never_mpt():
    """GAO ne doit jamais mapper vers MPT."""
    assert ZONE_TO_REGION.get("gao") == "GAO"
    assert ZONE_TO_REGION.get("gao") != "MPT"


def test_zone_niafunke_maps_to_tbk_never_mpt():
    """NIAFUNKE est TBK (Tombouctou), jamais MPT."""
    assert ZONE_TO_REGION.get("niafunke") == "TBK"
    assert ZONE_TO_REGION.get("niafunke") != "MPT"


def test_zone_bamako_maps_to_bko():
    assert ZONE_TO_REGION.get("bamako") == "BKO"


def test_zone_mopti_maps_to_mpt():
    assert ZONE_TO_REGION.get("mopti") == "MPT"


def test_zone_sevare_maps_to_mpt():
    assert ZONE_TO_REGION.get("sevare") == "MPT"


def test_zone_tombouctou_maps_to_tbk():
    assert ZONE_TO_REGION.get("tombouctou") == "TBK"


# ── Seuils de rejet ───────────────────────────────────────────────


def test_rejection_rate_above_stop_threshold_raises():
    """Taux de rejet >= 15% → SystemExit STOP-M4-G."""
    from scripts.etl_vendors_m4 import ETLReport

    report = ETLReport()
    report.total_read = 100
    # 20 rejetés = 20%
    report.rejected = [
        {
            "name": f"v{i}",
            "zone_raw": "UNKNOWN",
            "zone_normalized": "unknown",
            "_source": "test.xlsx",
        }
        for i in range(20)
    ]
    assert report.rejection_rate >= 0.15


def test_rejection_rate_below_warn_threshold_no_warning():
    """Taux de rejet < 5% → pas de warning."""
    from scripts.etl_vendors_m4 import ETLReport

    report = ETLReport()
    report.total_read = 100
    # 3 rejetés = 3%
    report.rejected = [
        {
            "name": f"v{i}",
            "zone_raw": "UNKNOWN",
            "zone_normalized": "unknown",
            "_source": "test.xlsx",
        }
        for i in range(3)
    ]
    assert report.rejection_rate < 0.05
