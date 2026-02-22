"""
T-L4 : fallback weights toujours traces (INV-9 + ADR-0010 D2).
Verifie que _load_weights() retourne is_fallback=True quand profil absent,
et que _DEFAULT_WEIGHTS est un dict coherent (somme = 1.0).
psycopg v3 -- row_factory=dict_row.
"""

import pytest


def test_l4a_fallback_weights_traced_quand_profil_absent(db_conn):
    """L4a : profil inexistant -> is_fallback=True + weights non vides."""
    from src.couche_a.scoring.engine import _load_weights

    weights, is_fallback = _load_weights(db_conn, "PROFIL_INEXISTANT_XYZ_P1")
    assert is_fallback is True
    assert weights is not None
    assert "commercial" in weights
    assert "capacity" in weights
    assert "sustainability" in weights
    assert "essentials" in weights


def test_l4b_fallback_false_quand_profil_present(db_conn):
    """L4b : profil trouve en DB -> is_fallback=False."""
    from src.couche_a.scoring.engine import _load_weights

    with db_conn.cursor() as cur:
        cur.execute("SELECT profile_code FROM public.scoring_configs LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("Aucun profil seed dans scoring_configs")

    _, is_fallback = _load_weights(db_conn, row["profile_code"])
    assert is_fallback is False


def test_l4c_load_weights_none_profile_is_fallback(db_conn):
    """L4c : profile_code=None -> is_fallback=True."""
    from src.couche_a.scoring.engine import _load_weights

    _, is_fallback = _load_weights(db_conn, None)
    assert is_fallback is True


def test_l4d_fallback_weights_sum_to_one():
    """L4d : _DEFAULT_WEIGHTS somme a 1.0 -- coherence mathematique."""
    from src.couche_a.scoring.engine import _DEFAULT_WEIGHTS

    total = sum(_DEFAULT_WEIGHTS.values())
    assert (
        abs(total - 1.0) < 1e-6
    ), f"Poids defaut = {total} != 1.0 -- incoherence mathematique"


def test_l4e_default_weights_has_all_categories():
    """L4e : _DEFAULT_WEIGHTS contient toutes les categories attendues."""
    from src.couche_a.scoring.engine import _DEFAULT_WEIGHTS

    expected = {"commercial", "capacity", "sustainability", "essentials"}
    assert set(_DEFAULT_WEIGHTS.keys()) == expected
