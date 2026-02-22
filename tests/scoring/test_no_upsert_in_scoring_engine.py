"""
L3 — Gate anti-retour : interdit ON CONFLICT / DO UPDATE dans scoring engine.

ADR-0006 / INV-6 : append-only opposable.
Échoue dès qu'un UPSERT réapparaît dans src/couche_a/scoring/engine.py.
"""

import re
from pathlib import Path

ENGINE_PATH = Path("src/couche_a/scoring/engine.py")


def _engine_content() -> str:
    assert ENGINE_PATH.exists(), f"{ENGINE_PATH} introuvable"
    return ENGINE_PATH.read_text(encoding="utf-8")


def test_no_on_conflict_in_engine():
    """ON CONFLICT interdit (ADR-0006 append-only)."""
    content = _engine_content()
    assert "ON CONFLICT" not in content, (
        f"UPSERT détecté : 'ON CONFLICT' présent dans {ENGINE_PATH}. "
        "Remplacer par INSERT INTO public.score_runs."
    )


def test_no_do_update_in_engine():
    """DO UPDATE interdit (ADR-0006 append-only)."""
    content = _engine_content()
    assert "DO UPDATE" not in content, (
        f"UPSERT détecté : 'DO UPDATE' présent dans {ENGINE_PATH}. "
        "Remplacer par INSERT INTO public.score_runs."
    )


def test_no_upsert_pattern_in_engine():
    """Pattern ON CONFLICT.*DO UPDATE interdit (regex)."""
    content = _engine_content()
    match = re.search(r"ON CONFLICT.*DO UPDATE", content, re.DOTALL)
    assert match is None, (
        f"UPSERT pattern 'ON CONFLICT...DO UPDATE' détecté dans {ENGINE_PATH}. "
        f"Contexte: {content[max(0, match.start()-50):match.end()+50]!r}"
    )


def test_writes_to_score_runs():
    """Le moteur écrit dans public.score_runs (pas supplier_scores via UPSERT)."""
    content = _engine_content()
    assert "score_runs" in content, (
        f"'score_runs' absent de {ENGINE_PATH}. "
        "L'écriture doit cibler public.score_runs (append-only)."
    )
