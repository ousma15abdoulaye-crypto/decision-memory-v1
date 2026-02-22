"""
T-L3 : currency lue depuis cases.currency (ADR-0010 D2).
Zero hardcode XOF si le case declare une autre devise.
psycopg v3 -- row_factory=dict_row.
"""

import uuid

import pytest


@pytest.fixture
def case_usd(db_conn):
    """Case USD -- cleanup apres test."""
    case_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.cases (id, case_type, title, currency, created_at)
            VALUES (%s, %s, %s, 'USD', now())
            """,
            (case_id, "TEST", "Test-P1-Currency-USD"),
        )
    yield case_id
    try:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM public.cases WHERE id = %s", (case_id,))
    except Exception:
        pass  # cascade permission restriction in test env


@pytest.fixture
def case_xof(db_conn):
    """Case XOF explicite -- cleanup apres test."""
    case_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.cases (id, case_type, title, currency, created_at)
            VALUES (%s, %s, %s, 'XOF', now())
            """,
            (case_id, "TEST", "Test-P1-Currency-XOF"),
        )
    yield case_id
    try:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM public.cases WHERE id = %s", (case_id,))
    except Exception:
        pass  # cascade permission restriction in test env


def test_l3a_currency_usd_dans_calculation_details(db_conn, case_usd):
    """L3a : case USD -> currency='USD', is_fallback=False."""
    from src.couche_a.scoring.engine import _get_case_currency

    currency, is_fallback, reason = _get_case_currency(db_conn, case_usd)
    assert currency == "USD"
    assert currency != "XOF"
    assert is_fallback is False
    assert reason is None


def test_l3b_currency_xof_explicit(db_conn, case_xof):
    """L3b : case XOF explicite -> currency='XOF', is_fallback=False (legal)."""
    from src.couche_a.scoring.engine import _get_case_currency

    currency, is_fallback, reason = _get_case_currency(db_conn, case_xof)
    assert currency == "XOF"
    assert is_fallback is False
    assert reason is None


def test_l3c_currency_fallback_sans_case(db_conn):
    """L3c : case_id=None -> fallback XOF + is_fallback=True + reason non vide."""
    from src.couche_a.scoring.engine import _get_case_currency

    currency, is_fallback, reason = _get_case_currency(db_conn, None)
    assert currency == "XOF"
    assert is_fallback is True
    assert reason is not None and len(reason) > 0


def test_l3d_no_xof_hardcoded_in_engine():
    """L3d : scan AST -- zero 'XOF' hardcode dans engine.py hors _get_case_currency."""
    from pathlib import Path

    content = Path("src/couche_a/scoring/engine.py").read_text(encoding="utf-8")
    lines = content.splitlines()
    violations = []
    in_get_case_currency = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if "def _get_case_currency" in line:
            in_get_case_currency = True
        elif in_get_case_currency and stripped.startswith("def "):
            in_get_case_currency = False
        if not in_get_case_currency and '"XOF"' in line:
            violations.append(f"ligne {i}: {line.strip()}")
    assert not violations, "XOF hardcode hors _get_case_currency:\n" + "\n".join(
        f"  STOP {v}" for v in violations
    )
