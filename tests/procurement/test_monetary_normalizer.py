"""
Tests normalisation monétaire M13-prérequis.

T1  : normalize_monetary_value — format "25 000 000 FCFA"
T2  : normalize_monetary_value — format "25M FCFA"
T3  : normalize_monetary_value — format "500.000.000 XOF"
T4  : normalize_monetary_value — format "50,000 USD" → FCFA
T5  : normalize_monetary_value — retourne [] si texte sans montant
T6  : classify_dgmp_tier — gré à gré (< 25M FCFA, goods/services)
T7  : classify_dgmp_tier — aon (25M FCFA, goods/services)
T8  : classify_dgmp_tier — aoi (≥ 500M FCFA)
T9  : classify_dgmp_tier — travaux tier works (< 100M = gré à gré)
T10 : H1 builder peuple dgmp_threshold_tier_detected si framework=DGMP
T11 : H1 builder transmet family=WORKS → tier travaux correct (80M → gré à gré)
T12 : H1 SCI — dgmp_threshold_tier_detected reste None
T13 : SCI_DGMP_OVERLAP_ZONE_USD — zone de recouvrement correctement bornée
"""

from __future__ import annotations

import pytest

# ── T1-T5 : normalize_monetary_value ─────────────────────────────────────


def test_normalize_25m_fcfa():
    from src.procurement.monetary_normalizer import normalize_monetary_value

    results = normalize_monetary_value("Montant estimé : 25 000 000 FCFA")
    assert len(results) >= 1
    first = results[0]
    assert first.currency_iso == "XOF"
    assert abs(first.amount_fcfa - 25_000_000) < 1


def test_normalize_25m_suffix_fcfa():
    from src.procurement.monetary_normalizer import normalize_monetary_value

    results = normalize_monetary_value("Budget : 25M FCFA")
    assert len(results) >= 1
    assert abs(results[0].amount_fcfa - 25_000_000) < 1


def test_normalize_dot_separated_xof():
    from src.procurement.monetary_normalizer import normalize_monetary_value

    results = normalize_monetary_value("500.000.000 XOF")
    assert len(results) >= 1
    assert abs(results[0].amount_fcfa - 500_000_000) < 1


def test_normalize_usd_to_fcfa():
    from src.procurement.monetary_normalizer import normalize_monetary_value

    results = normalize_monetary_value("50,000 USD")
    assert len(results) >= 1
    val = results[0]
    assert val.currency_iso == "USD"
    assert abs(val.amount_native - 50_000) < 1
    assert val.amount_fcfa > 0


def test_normalize_empty_text_returns_empty_list():
    from src.procurement.monetary_normalizer import normalize_monetary_value

    results = normalize_monetary_value("Dossier sans montant mentionné.")
    assert results == []


# ── T6-T9 : classify_dgmp_tier ───────────────────────────────────────────


def test_classify_dgmp_tier_gre_a_gre_goods():
    from src.procurement.monetary_normalizer import classify_dgmp_tier

    assert classify_dgmp_tier(10_000_000, "goods_services") == "gre_a_gre"


def test_classify_dgmp_tier_aon_goods():
    from src.procurement.monetary_normalizer import classify_dgmp_tier

    assert classify_dgmp_tier(25_000_000, "goods_services") == "aon"


def test_classify_dgmp_tier_aoi():
    from src.procurement.monetary_normalizer import classify_dgmp_tier

    assert classify_dgmp_tier(500_000_000, "goods_services") == "aoi"
    assert classify_dgmp_tier(600_000_000, "works") == "aoi"


def test_classify_dgmp_tier_works_gre_a_gre():
    from src.procurement.monetary_normalizer import classify_dgmp_tier

    assert classify_dgmp_tier(80_000_000, "works") == "gre_a_gre"
    assert classify_dgmp_tier(100_000_000, "works") == "aon"


# ── T10 : H1 builder peuple dgmp_threshold_tier_detected ─────────────────


def test_h1_dgmp_tier_detected_in_handoff():
    from src.procurement.document_ontology import ProcurementFramework
    from src.procurement.handoff_builder import _build_h1_regulatory

    text = "Marché d'un montant de 30 000 000 FCFA — appel d'offres ouvert"
    profile = _build_h1_regulatory(
        framework=ProcurementFramework.DGMP_MALI,
        framework_confidence=0.85,
        text=text,
    )
    assert profile.dgmp_threshold_tier_detected == "aon"
    assert any("tier_aon" in s for s in profile.dgmp_signals_detected)


def test_h1_no_dgmp_tier_for_sci_framework():
    from src.procurement.document_ontology import ProcurementFramework
    from src.procurement.handoff_builder import _build_h1_regulatory

    text = "Marché d'un montant de 30 000 000 FCFA — conditions générales SCI"
    profile = _build_h1_regulatory(
        framework=ProcurementFramework.SCI,
        framework_confidence=0.90,
        text=text,
    )
    assert profile.dgmp_threshold_tier_detected is None


# ── T11 : H1 builder family=WORKS → seuils travaux ───────────────────────


def test_h1_dgmp_tier_works_80m_is_gre_a_gre():
    """80M FCFA = gré à gré pour les travaux (seuil travaux: 100M), pas pour biens (25M)."""
    from src.procurement.document_ontology import (
        ProcurementFamily,
        ProcurementFramework,
    )
    from src.procurement.handoff_builder import _build_h1_regulatory

    text = "Travaux de réhabilitation — budget estimé 80 000 000 FCFA"
    profile = _build_h1_regulatory(
        framework=ProcurementFramework.DGMP_MALI,
        framework_confidence=0.85,
        text=text,
        family=ProcurementFamily.WORKS,
    )
    assert profile.dgmp_threshold_tier_detected == "gre_a_gre", (
        "80M FCFA pour des travaux doit être gré à gré (seuil 100M), "
        "pas aon comme pour les biens/services (seuil 25M)"
    )


# ── T12 : SCI → pas de tier DGMP (déjà couvert, référence mise à jour) ───
# (test_h1_no_dgmp_tier_for_sci_framework ci-dessus)

# ── T13 : SCI_DGMP_OVERLAP_ZONE_USD ──────────────────────────────────────


def test_sci_dgmp_overlap_zone_bounds():
    from src.procurement.monetary_normalizer import SCI_DGMP_OVERLAP_ZONE_USD

    assert SCI_DGMP_OVERLAP_ZONE_USD["min_usd"] > 0
    assert SCI_DGMP_OVERLAP_ZONE_USD["max_usd"] == pytest.approx(50_000.0)
    assert SCI_DGMP_OVERLAP_ZONE_USD["min_fcfa"] == pytest.approx(25_000_000.0)
    assert SCI_DGMP_OVERLAP_ZONE_USD["min_usd"] < SCI_DGMP_OVERLAP_ZONE_USD["max_usd"]
