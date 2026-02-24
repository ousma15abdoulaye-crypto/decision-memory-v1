"""L6 — Tests du mode e2e : INV-P16 (strict incomplete propagation).

Vérifie que run_pipeline_a_e2e() :
  - retourne un PipelineResult avec mode='e2e'
  - propage 'incomplete' en statut global si un step est incomplete (INV-P16)
  - retourne 'blocked' si preflight bloqué
  - persiste force_recompute dans pipeline_runs (INV-P18)
  - 'complete' est toujours interdit (INV-P16 / ADR-0012)

Fixtures : db_conn, case_factory, pipeline_case_with_dao_and_offers.
"""

from __future__ import annotations

from unittest.mock import patch

import psycopg
from psycopg.rows import dict_row

from src.couche_a.pipeline.models import PipelineResult
from src.couche_a.pipeline.service import run_pipeline_a_e2e

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn(db_conn) -> psycopg.Connection:
    """Connexion autocommit=False depuis la même DB que db_conn."""
    import os

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(conninfo=url, row_factory=dict_row, autocommit=False)


def _get_pipeline_run(db_conn, run_id: str) -> dict | None:
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.pipeline_runs WHERE pipeline_run_id = %s",
            (run_id,),
        )
        return cur.fetchone()


# ---------------------------------------------------------------------------
# Test : blocked sur case inexistant
# ---------------------------------------------------------------------------


def test_e2e_blocked_on_missing_case(db_conn):
    """Preflight bloqué → statut 'blocked', mode='e2e' tracé."""
    conn = _make_conn(db_conn)
    try:
        result = run_pipeline_a_e2e(
            case_id="case-inexistant-e2e",
            triggered_by="test-e2e-blocked",
            conn=conn,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    assert isinstance(result, PipelineResult)
    assert result.status == "blocked"
    assert result.mode == "e2e"
    assert result.case_id == "case-inexistant-e2e"

    row = _get_pipeline_run(db_conn, result.run_id)
    assert row is not None
    assert row["mode"] == "e2e"


# ---------------------------------------------------------------------------
# Test : incomplete propagé globalement (INV-P16 strict)
# ---------------------------------------------------------------------------


def test_e2e_incomplete_propagates_globally(db_conn, pipeline_case_with_dao_and_offers):
    """INV-P16 : un step incomplete → statut global 'incomplete' en mode e2e."""
    case_id = pipeline_case_with_dao_and_offers

    with patch(
        "src.couche_a.pipeline.service._run_scoring_step"
    ) as mock_scoring, patch(
        "src.couche_a.pipeline.service._load_extraction_summary"
    ) as mock_extraction:
        from src.couche_a.pipeline.models import StepOutcome

        mock_extraction.return_value = StepOutcome(
            status="incomplete",
            reason_code="NO_EXTRACTIONS",
            reason_message="Aucune extraction",
        )
        mock_scoring.return_value = StepOutcome(
            status="ok",
            meta={"scores_count": 0, "eliminations_count": 0},
        )

        conn = _make_conn(db_conn)
        try:
            result = run_pipeline_a_e2e(
                case_id=case_id,
                triggered_by="test-e2e-strict",
                conn=conn,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    assert result.status == "incomplete", (
        f"INV-P16 : statut global attendu 'incomplete', obtenu {result.status!r}"
    )
    assert result.mode == "e2e"
    assert result.status != "complete", "INV-P16 : 'complete' interdit dans #11"


# ---------------------------------------------------------------------------
# Test : partial_complete si tous les steps sont ok
# ---------------------------------------------------------------------------


def test_e2e_partial_complete_when_all_ok(db_conn, pipeline_case_with_dao_and_offers):
    """Tous les steps ok → partial_complete en mode e2e."""
    case_id = pipeline_case_with_dao_and_offers

    with patch(
        "src.couche_a.pipeline.service._load_extraction_summary"
    ) as mock_ex, patch(
        "src.couche_a.pipeline.service._load_criteria_summary"
    ) as mock_cr, patch(
        "src.couche_a.pipeline.service._load_normalization_summary"
    ) as mock_nr, patch(
        "src.couche_a.pipeline.service._run_scoring_step"
    ) as mock_sc:
        from src.couche_a.pipeline.models import StepOutcome

        mock_ex.return_value = StepOutcome(
            status="ok", meta={"extractions_count": 2}
        )
        mock_cr.return_value = StepOutcome(
            status="ok", meta={"criteria_count": 2}
        )
        mock_nr.return_value = StepOutcome(
            status="ok", meta={"normalized_count": 2}
        )
        mock_sc.return_value = StepOutcome(
            status="ok",
            meta={"scores_count": 2, "eliminations_count": 0, "score_entries": []},
        )

        conn = _make_conn(db_conn)
        try:
            result = run_pipeline_a_e2e(
                case_id=case_id,
                triggered_by="test-e2e-ok",
                conn=conn,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    assert result.status == "partial_complete"
    assert result.mode == "e2e"
    assert result.status != "complete"


# ---------------------------------------------------------------------------
# Test : force_recompute tracé dans pipeline_runs (INV-P18)
# ---------------------------------------------------------------------------


def test_e2e_force_recompute_persisted(db_conn, case_factory):
    """INV-P18 : force_recompute=True tracé dans pipeline_runs.force_recompute."""
    case_id = case_factory()

    with patch(
        "src.couche_a.pipeline.service._run_scoring_step"
    ) as mock_sc:
        from src.couche_a.pipeline.models import StepOutcome

        mock_sc.return_value = StepOutcome(
            status="ok",
            meta={"scores_count": 0, "eliminations_count": 0, "score_entries": []},
        )

        conn = _make_conn(db_conn)
        try:
            result = run_pipeline_a_e2e(
                case_id=case_id,
                triggered_by="test-e2e-force",
                conn=conn,
                force_recompute=True,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    assert result.force_recompute is True
    row = _get_pipeline_run(db_conn, result.run_id)
    assert row is not None
    assert row["force_recompute"] is True, (
        "INV-P18 : force_recompute=True doit être tracé dans pipeline_runs"
    )


# ---------------------------------------------------------------------------
# Test : 'complete' interdit
# ---------------------------------------------------------------------------


def test_e2e_complete_status_forbidden(db_conn, case_factory):
    """INV-P16 : status='complete' interdit en mode e2e (#11, réservé #14)."""
    case_id = case_factory()

    with patch(
        "src.couche_a.pipeline.service._load_extraction_summary"
    ) as mock_ex, patch(
        "src.couche_a.pipeline.service._load_criteria_summary"
    ) as mock_cr, patch(
        "src.couche_a.pipeline.service._load_normalization_summary"
    ) as mock_nr, patch(
        "src.couche_a.pipeline.service._run_scoring_step"
    ) as mock_sc:
        from src.couche_a.pipeline.models import StepOutcome

        for m in (mock_ex, mock_cr, mock_nr):
            m.return_value = StepOutcome(status="ok", meta={})
        mock_sc.return_value = StepOutcome(
            status="ok",
            meta={"scores_count": 1, "eliminations_count": 0, "score_entries": []},
        )

        conn = _make_conn(db_conn)
        try:
            result = run_pipeline_a_e2e(
                case_id=case_id,
                triggered_by="test-e2e-no-complete",
                conn=conn,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    assert result.status != "complete", (
        "INV-P16 : status='complete' interdit dans #11"
    )
