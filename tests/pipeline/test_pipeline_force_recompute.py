"""L7 — Tests force_recompute : INV-P14 (cache) / INV-P15A (calcul forcé).

Vérifie que _run_scoring_step() :
  - force_recompute=True  → toujours calculate_scores_for_case (INV-P15A)
  - force_recompute=False → tentative get_latest_score_run, fallback calcul (INV-P14)
  - _lookup_warning initialisé à None (PATCH-10) — pas de NameError possible
  - force_recompute tracé dans meta du step scoring

Fixtures : db_conn, case_factory.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.couche_a.pipeline.service import _run_scoring_step

# ---------------------------------------------------------------------------
# Helpers mock
# ---------------------------------------------------------------------------


def _mock_conn_with_rows(extractions=None, criteria=None):
    """Retourne un mock de connexion psycopg avec rows prédéfinis."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    if extractions is None:
        extractions = [
            {
                "id": "ext-1",
                "supplier_name": "FournisseurA",
                "extracted_data_json": '{"price": 1000}',
            }
        ]
    if criteria is None:
        criteria = []

    cursor.fetchall.side_effect = [extractions, criteria]
    return conn


# ---------------------------------------------------------------------------
# Test : force_recompute=True appelle toujours calculate_scores_for_case
# ---------------------------------------------------------------------------


def test_force_recompute_true_always_calculates():
    """INV-P15A : force_recompute=True → calculate_scores_for_case toujours appelé."""
    conn = _mock_conn_with_rows()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine") as mock_engine,
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        engine_instance = mock_engine.return_value
        engine_instance.calculate_scores_for_case.return_value = ([], [])

        _run_scoring_step("case-test", conn, force_recompute=True)

        engine_instance.calculate_scores_for_case.assert_called_once()
        engine_instance.get_latest_score_run.assert_not_called()


# ---------------------------------------------------------------------------
# Test : force_recompute=False tente get_latest_score_run d'abord
# ---------------------------------------------------------------------------


def test_force_recompute_false_tries_cache_first():
    """INV-P14 : force_recompute=False → get_latest_score_run tenté en premier."""
    conn = _mock_conn_with_rows()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine") as mock_engine,
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        engine_instance = mock_engine.return_value
        engine_instance.get_latest_score_run.return_value = {
            "scores": [],
            "eliminations": [],
        }

        _run_scoring_step("case-test", conn, force_recompute=False)

        engine_instance.get_latest_score_run.assert_called_once_with("case-test")
        engine_instance.calculate_scores_for_case.assert_not_called()


# ---------------------------------------------------------------------------
# Test : force_recompute=False avec AttributeError → fallback calcul (ADR-0013)
# ---------------------------------------------------------------------------


def test_force_recompute_false_fallback_on_missing_method():
    """ADR-0013 : get_latest_score_run absent → fallback calculate_scores_for_case."""
    conn = _mock_conn_with_rows()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine") as mock_engine,
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        engine_instance = mock_engine.return_value
        del engine_instance.get_latest_score_run
        type(engine_instance).get_latest_score_run = property(
            lambda self: (_ for _ in ()).throw(AttributeError("not implemented"))
        )
        engine_instance.calculate_scores_for_case.return_value = ([], [])

        outcome = _run_scoring_step("case-test", conn, force_recompute=False)

        engine_instance.calculate_scores_for_case.assert_called_once()
        assert outcome.meta.get("lookup_warning") == "SCORE_CACHE_UNAVAILABLE_FALLBACK"


# ---------------------------------------------------------------------------
# Test : PATCH-10 — _lookup_warning initialisé à None (pas de NameError)
# ---------------------------------------------------------------------------


def test_lookup_warning_initialized_no_name_error():
    """PATCH-10 : _lookup_warning initialisé à None — pas de NameError."""
    conn = _mock_conn_with_rows()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine") as mock_engine,
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        engine_instance = mock_engine.return_value
        engine_instance.calculate_scores_for_case.return_value = ([], [])

        # Force_recompute=True skip le bloc cache → _lookup_warning reste None → pas d'erreur
        outcome = _run_scoring_step("case-test", conn, force_recompute=True)

        assert "lookup_warning" not in outcome.meta


# ---------------------------------------------------------------------------
# Test : force_recompute tracé dans meta
# ---------------------------------------------------------------------------


def test_force_recompute_traced_in_meta():
    """force_recompute doit être tracé dans StepOutcome.meta."""
    conn = _mock_conn_with_rows()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine") as mock_engine,
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        engine_instance = mock_engine.return_value
        engine_instance.calculate_scores_for_case.return_value = ([], [])

        outcome_true = _run_scoring_step("case-test", conn, force_recompute=True)
        assert outcome_true.meta["force_recompute"] is True

        conn2 = _mock_conn_with_rows()
        engine_instance.get_latest_score_run = MagicMock(return_value=None)
        engine_instance.calculate_scores_for_case.return_value = ([], [])
        outcome_false = _run_scoring_step("case-test", conn2, force_recompute=False)
        assert outcome_false.meta["force_recompute"] is False


# ---------------------------------------------------------------------------
# Test : no extractions → incomplete immédiat (force_recompute ignoré)
# ---------------------------------------------------------------------------


def test_no_extractions_returns_incomplete_regardless_force_recompute():
    """Pas d'extractions → incomplete immédiat, force_recompute ignoré."""
    conn = _mock_conn_with_rows(extractions=[], criteria=[])

    outcome = _run_scoring_step("case-test", conn, force_recompute=True)
    assert outcome.status == "incomplete"
    assert outcome.reason_code == "NO_EXTRACTIONS_FOR_SCORING"
