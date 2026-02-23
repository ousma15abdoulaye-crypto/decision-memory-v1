"""L4 — Contrat scoring_meta : stabilité et traçabilité.

ADR-0010 D2 / INV-9
Vérifie :
  - _SCORING_VERSION = "V3.3.2" (ASSERT strict, pas skip)
  - scoring_meta présent dans calculation_details des scores totaux
  - clés obligatoires : fallback, fallback_reason, fallback_weights,
                        profile_used, scoring_version, currency,
                        currency_is_fallback, currency_fallback_reason
  - fallback est strictement bool
  - scoring_version == _SCORING_VERSION (cohérence)
  - currency cohérente avec case.currency (via case_factory)

Tests L4a-L4c : constants/imports — zéro DB.
Tests L4d-L4g : run réel via calculate_scores_for_case (integration, DB I/O).
"""

import pytest

from src.core.models import DAOCriterion, SupplierPackage
from src.couche_a.scoring.engine import _SCORING_VERSION, ScoringEngine

_EXPECTED_VERSION = "V3.3.2"

_REQUIRED_META_KEYS = {
    "fallback",
    "fallback_reason",
    "fallback_weights",
    "profile_used",
    "scoring_version",
    "currency",
    "currency_is_fallback",
    "currency_fallback_reason",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_supplier(name: str = "TEST") -> SupplierPackage:
    """Fournisseur minimal valide (aucune élimination attendue)."""
    return SupplierPackage(
        supplier_name=name,
        offer_ids=["offer-1"],
        documents=[],
        package_status="COMPLETE",
        has_financial=True,
        has_technical=True,
        has_admin=True,
        extracted_data={},
        missing_fields=[],
    )


def _non_eliminatory_criterion() -> DAOCriterion:
    """Critère sans seuil d'élimination."""
    return DAOCriterion(
        categorie="commercial",
        critere_nom="Prix",
        description="Critère prix",
        ponderation=100.0,
        type_reponse="numerique",
        seuil_elimination=None,
        ordre_affichage=1,
    )


def _run_engine(case_id: str) -> tuple:
    """Appel réel au moteur. Retourne (scores, eliminations)."""
    engine = ScoringEngine()
    suppliers = [_minimal_supplier("SUPPLIER-TEST")]
    criteria = [_non_eliminatory_criterion()]
    return engine.calculate_scores_for_case(case_id, suppliers, criteria)


def _get_total_meta(scores) -> dict | None:
    """Extrait scoring_meta depuis le premier score total."""
    totals = [s for s in scores if s.category == "total"]
    if not totals:
        return None
    return totals[0].calculation_details.get("scoring_meta")


# ---------------------------------------------------------------------------
# L4a — _SCORING_VERSION = "V3.3.2" (ASSERT strict)
# ---------------------------------------------------------------------------


def test_l4a_scoring_version_constant_strict():
    """_SCORING_VERSION doit valoir exactement 'V3.3.2' (ASSERT strict, pas skip)."""
    assert _SCORING_VERSION == _EXPECTED_VERSION, (
        f"_SCORING_VERSION = {_SCORING_VERSION!r} != {_EXPECTED_VERSION!r}. "
        "La version a changé — mettre à jour le contrat ou ouvrir une PR de migration."
    )


# ---------------------------------------------------------------------------
# L4b — scoring_meta accessible via import (structure de base)
# ---------------------------------------------------------------------------


def test_l4b_scoring_version_importable():
    """_SCORING_VERSION est importable depuis src.couche_a.scoring.engine."""
    assert isinstance(_SCORING_VERSION, str)
    assert _SCORING_VERSION.startswith(
        "V"
    ), f"Format attendu 'V<semver>', obtenu {_SCORING_VERSION!r}"


# ---------------------------------------------------------------------------
# L4c — _DEFAULT_WEIGHTS présent et cohérent
# ---------------------------------------------------------------------------


def test_l4c_default_weights_coherent():
    """_DEFAULT_WEIGHTS contient les 4 catégories et somme à 1.0."""
    from src.couche_a.scoring.engine import _DEFAULT_WEIGHTS

    expected_keys = {"commercial", "capacity", "sustainability", "essentials"}
    assert set(_DEFAULT_WEIGHTS.keys()) == expected_keys
    total = sum(_DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-6, f"_DEFAULT_WEIGHTS sum = {total} != 1.0"


# ---------------------------------------------------------------------------
# L4d — run réel : scoring_meta présent dans total score
# ---------------------------------------------------------------------------


def test_l4d_scoring_meta_present_in_total_score(case_factory):
    """Run réel : scoring_meta doit être présent dans calculation_details du score total."""
    case_id = case_factory()
    scores, _ = _run_engine(case_id)

    meta = _get_total_meta(scores)
    assert meta is not None, (
        "scoring_meta absent du score total. "
        "Vérifier que _calculate_total_scores injecte scoring_meta."
    )


# ---------------------------------------------------------------------------
# L4e — run réel : clés obligatoires présentes
# ---------------------------------------------------------------------------


def test_l4e_scoring_meta_required_keys(case_factory):
    """scoring_meta doit contenir toutes les clés obligatoires du contrat."""
    case_id = case_factory()
    scores, _ = _run_engine(case_id)

    meta = _get_total_meta(scores)
    if meta is None:
        pytest.skip("scoring_meta absent du score total (L4d échoue en amont)")

    missing = _REQUIRED_META_KEYS - set(meta.keys())
    assert not missing, (
        f"Clés manquantes dans scoring_meta : {missing}. "
        f"Clés présentes : {set(meta.keys())}"
    )


# ---------------------------------------------------------------------------
# L4f — run réel : fallback est bool + scoring_version cohérente
# ---------------------------------------------------------------------------


def test_l4f_fallback_is_bool_and_version_coherent(case_factory):
    """fallback est bool ET scoring_version == _SCORING_VERSION dans le run réel."""
    case_id = case_factory()
    scores, _ = _run_engine(case_id)

    meta = _get_total_meta(scores)
    if meta is None:
        pytest.skip("scoring_meta absent du score total")

    assert isinstance(
        meta["fallback"], bool
    ), f"scoring_meta.fallback doit être bool, obtenu {type(meta['fallback'])}"
    assert meta["scoring_version"] == _EXPECTED_VERSION, (
        f"scoring_meta.scoring_version = {meta['scoring_version']!r} "
        f"!= {_EXPECTED_VERSION!r}"
    )


# ---------------------------------------------------------------------------
# L4g — currency cohérente avec case.currency (case_factory "USD")
# ---------------------------------------------------------------------------


def test_l4g_currency_read_from_case(case_factory):
    """currency dans scoring_meta doit correspondre à cases.currency (USD)."""
    case_id = case_factory(currency="USD")
    scores, _ = _run_engine(case_id)

    meta = _get_total_meta(scores)
    if meta is None:
        pytest.skip("scoring_meta absent du score total")

    assert meta["currency"] == "USD", (
        f"scoring_meta.currency = {meta['currency']!r} != 'USD'. "
        "Le moteur doit lire currency depuis cases.currency (ADR-0010 D2)."
    )
    assert (
        meta["currency_is_fallback"] is False
    ), "currency_is_fallback doit être False quand le case déclare USD."


# ---------------------------------------------------------------------------
# L4h — fallback activé → raison non vide
# ---------------------------------------------------------------------------


def test_l4h_fallback_active_reason_not_empty(case_factory):
    """Quand fallback=True (profil GENERIC absent), fallback_reason doit être non vide."""
    case_id = case_factory()
    engine = ScoringEngine()
    suppliers = [_minimal_supplier()]
    criteria = [_non_eliminatory_criterion()]

    scores, _ = engine.calculate_scores_for_case(
        case_id, suppliers, criteria, profile_code="PROFIL_INEXISTANT_L4H_TEST"
    )

    meta = _get_total_meta(scores)
    if meta is None:
        pytest.skip("scoring_meta absent du score total")

    if meta["fallback"] is True:
        assert (
            meta["fallback_reason"] is not None and len(meta["fallback_reason"]) > 0
        ), (
            "fallback=True mais fallback_reason est vide ou None. "
            "La traçabilité du fallback est incomplète (INV-9)."
        )
        assert (
            meta["fallback_weights"] is not None
        ), "fallback=True mais fallback_weights est None."
