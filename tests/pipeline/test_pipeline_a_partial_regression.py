"""L8 — Non-régression run_pipeline_a_partial (GUARD-OPS-01).

Vérifie que run_pipeline_a_partial() est INCHANGÉE depuis #10 :
  - Hash SHA256 du corps de la fonction = valeur preflight GUARD-OPS-01
  - Signature inchangée (3 params : case_id, triggered_by, conn)
  - Retourne PipelineResult (pas run_pipeline_a_e2e)
  - mode='partial' dans le résultat (backward compat #10)
  - force_recompute=False dans le résultat (backward compat #10)
  - 'complete' toujours interdit (INV-P16)

GUARD-OPS-01 hash : f424e91246465fe6f6575b4b8bea195c86bf76664247904e2f7aec1d4b0ca1db
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import pathlib
import re
from unittest.mock import patch

from src.couche_a.pipeline.models import PipelineResult
from src.couche_a.pipeline.service import run_pipeline_a_partial

# ---------------------------------------------------------------------------
# GUARD-OPS-01 : hash attendu du corps de run_pipeline_a_partial
# ---------------------------------------------------------------------------

GUARD_HASH = "f424e91246465fe6f6575b4b8bea195c86bf76664247904e2f7aec1d4b0ca1db"


def _extract_function_source(src_text: str, func_name: str) -> str:
    """Extrait le source d'une fonction top-level par analyse AST."""
    tree = ast.parse(src_text)
    lines = src_text.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            end = node.end_lineno
            start = node.lineno
            return "\n".join(lines[start - 1 : end])
    raise ValueError(f"Fonction {func_name!r} introuvable")


def _normalize(source: str) -> str:
    """Normalise le source pour le hash : supprime commentaires + espaces superflus."""
    source = re.sub(r"#[^\n]*", "", source)
    source = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    source = re.sub(r"'''.*?'''", "", source, flags=re.DOTALL)
    lines = [ln.rstrip() for ln in source.splitlines() if ln.strip()]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test GUARD-OPS-01 : hash intact
# ---------------------------------------------------------------------------


def test_guard_ops_01_partial_hash_unchanged():
    """GUARD-OPS-01 : run_pipeline_a_partial inchangée depuis preflight #11."""
    service_path = pathlib.Path("src/couche_a/pipeline/service.py")
    src = service_path.read_text(encoding="utf-8")
    func_src = _extract_function_source(src, "run_pipeline_a_partial")
    normalized = _normalize(func_src)
    actual_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    assert actual_hash == GUARD_HASH, (
        f"GUARD-OPS-01 VIOLATION : run_pipeline_a_partial a été modifiée !\n"
        f"  Hash attendu : {GUARD_HASH}\n"
        f"  Hash actuel  : {actual_hash}\n"
        f"  Cette fonction doit rester INCHANGÉE dans #11."
    )


# ---------------------------------------------------------------------------
# Test : signature inchangée
# ---------------------------------------------------------------------------


def test_partial_signature_unchanged():
    """Signature run_pipeline_a_partial : 3 params positionnels (case_id, triggered_by, conn)."""
    sig = inspect.signature(run_pipeline_a_partial)
    params = list(sig.parameters.keys())
    assert params == [
        "case_id",
        "triggered_by",
        "conn",
    ], f"Signature modifiée — attendu ['case_id', 'triggered_by', 'conn'], obtenu {params}"


# ---------------------------------------------------------------------------
# Test : retourne PipelineResult avec mode='partial' (backward compat #10)
# ---------------------------------------------------------------------------


def test_partial_returns_pipeline_result_mode_partial(db_conn, case_factory):
    """run_pipeline_a_partial retourne PipelineResult avec mode='partial'."""
    import os

    import psycopg
    from psycopg.rows import dict_row

    case_id = case_factory()

    with (
        patch("src.couche_a.pipeline.service._load_extraction_summary") as mock_ex,
        patch("src.couche_a.pipeline.service._load_criteria_summary") as mock_cr,
        patch("src.couche_a.pipeline.service._load_normalization_summary") as mock_nr,
        patch("src.couche_a.pipeline.service._run_scoring_step") as mock_sc,
    ):
        from src.couche_a.pipeline.models import StepOutcome

        mock_ex.return_value = StepOutcome(status="ok", meta={"extractions_count": 0})
        mock_cr.return_value = StepOutcome(status="ok", meta={"criteria_count": 0})
        mock_nr.return_value = StepOutcome(status="ok", meta={"normalized_count": 0})
        mock_sc.return_value = StepOutcome(
            status="ok",
            meta={"scores_count": 0, "eliminations_count": 0, "score_entries": []},
        )

        url = os.environ["DATABASE_URL"].replace(
            "postgresql+psycopg://", "postgresql://"
        )
        conn = psycopg.connect(conninfo=url, row_factory=dict_row, autocommit=False)
        try:
            result = run_pipeline_a_partial(
                case_id=case_id,
                triggered_by="test-regression",
                conn=conn,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    assert isinstance(result, PipelineResult)
    assert (
        result.mode == "partial"
    ), f"Compat backward #10 : mode attendu 'partial', obtenu {result.mode!r}"
    assert (
        result.force_recompute is False
    ), "Compat backward #10 : force_recompute doit être False par défaut"
    assert result.status != "complete", "INV-P16 : 'complete' interdit dans #11"


# ---------------------------------------------------------------------------
# Test : 'complete' toujours interdit
# ---------------------------------------------------------------------------


def test_partial_complete_status_never_returned(db_conn, case_factory):
    """INV-P16 : run_pipeline_a_partial ne retourne jamais status='complete'."""
    import os

    import psycopg
    from psycopg.rows import dict_row

    case_id = case_factory()

    with (
        patch("src.couche_a.pipeline.service._load_extraction_summary") as mock_ex,
        patch("src.couche_a.pipeline.service._load_criteria_summary") as mock_cr,
        patch("src.couche_a.pipeline.service._load_normalization_summary") as mock_nr,
        patch("src.couche_a.pipeline.service._run_scoring_step") as mock_sc,
    ):
        from src.couche_a.pipeline.models import StepOutcome

        for m in (mock_ex, mock_cr, mock_nr):
            m.return_value = StepOutcome(status="ok", meta={})
        mock_sc.return_value = StepOutcome(
            status="ok",
            meta={"scores_count": 5, "eliminations_count": 0, "score_entries": []},
        )

        url = os.environ["DATABASE_URL"].replace(
            "postgresql+psycopg://", "postgresql://"
        )
        conn = psycopg.connect(conninfo=url, row_factory=dict_row, autocommit=False)
        try:
            result = run_pipeline_a_partial(
                case_id=case_id,
                triggered_by="test-no-complete",
                conn=conn,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    assert (
        result.status != "complete"
    ), "INV-P16 : status='complete' interdit dans #10/#11 — réservé #14"
    assert result.status in ("partial_complete", "blocked", "incomplete", "failed")
