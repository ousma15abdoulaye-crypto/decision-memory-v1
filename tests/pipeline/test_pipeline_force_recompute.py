"""L7 — Tests force_recompute : INV-P15A (calcul exécuté).

Rectificatif CTO P3.3 : le scoring Couche A appelle toujours
``calculate_scores_for_case`` — pas de cache via ``get_latest_score_run``.

Fixtures : db_conn, case_factory.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.couche_a.pipeline.service import _run_scoring_step


class _EngineStub:
    """Stub sans get_latest_score_run — toute utilisation future lèverait AttributeError."""

    def __init__(self) -> None:
        self.calculate_scores_for_case = MagicMock(return_value=([], []))


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


def test_force_recompute_true_calls_calculate_scores():
    """force_recompute=True → calculate_scores_for_case appelé."""
    conn = _mock_conn_with_rows()
    stub = _EngineStub()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine", return_value=stub),
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        _run_scoring_step("CASE-28b05d85", conn, force_recompute=True)

        stub.calculate_scores_for_case.assert_called_once()
        assert not hasattr(stub, "get_latest_score_run")


def test_force_recompute_false_also_calls_calculate_scores_no_cache():
    """Rectificatif CTO : force_recompute=False → même chemin, pas de get_latest_score_run."""
    conn = _mock_conn_with_rows()
    stub = _EngineStub()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine", return_value=stub),
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        _run_scoring_step("CASE-28b05d85", conn, force_recompute=False)

        stub.calculate_scores_for_case.assert_called_once()
        assert not hasattr(stub, "get_latest_score_run")


def test_no_lookup_warning_in_meta():
    """Le meta scoring ne contient plus lookup_warning (cache retiré)."""
    conn = _mock_conn_with_rows()
    stub = _EngineStub()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine", return_value=stub),
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        outcome = _run_scoring_step("CASE-28b05d85", conn, force_recompute=False)

        assert "lookup_warning" not in outcome.meta


def test_force_recompute_traced_in_meta():
    """force_recompute doit être tracé dans StepOutcome.meta."""
    conn = _mock_conn_with_rows()
    stub = _EngineStub()

    with (
        patch("src.couche_a.pipeline.service.ScoringEngine", return_value=stub),
        patch(
            "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
            return_value=[],
        ),
        patch(
            "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
            return_value=[],
        ),
    ):
        outcome_true = _run_scoring_step("case-test", conn, force_recompute=True)
        assert outcome_true.meta["force_recompute"] is True

        conn2 = _mock_conn_with_rows()
        stub2 = _EngineStub()
        with (
            patch("src.couche_a.pipeline.service.ScoringEngine", return_value=stub2),
            patch(
                "src.couche_a.pipeline.service._build_supplier_packages_from_extractions",
                return_value=[],
            ),
            patch(
                "src.couche_a.pipeline.service._build_dao_criteria_from_rows",
                return_value=[],
            ),
        ):
            outcome_false = _run_scoring_step("case-test", conn2, force_recompute=False)
        assert outcome_false.meta["force_recompute"] is False


def test_no_extractions_returns_incomplete_regardless_force_recompute():
    """Pas d'extractions → incomplete immédiat, force_recompute ignoré."""
    conn = _mock_conn_with_rows(extractions=[], criteria=[])

    outcome = _run_scoring_step("case-test", conn, force_recompute=True)
    assert outcome.status == "incomplete"
    assert outcome.reason_code == "NO_EXTRACTIONS_FOR_SCORING"
