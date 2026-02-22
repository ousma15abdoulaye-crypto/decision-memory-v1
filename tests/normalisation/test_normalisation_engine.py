"""
Tests bloquants -- M-NORMALISATION-ENGINE (V3.1)
Gate CI : precision 1.0 sur CRITICAL_ALIASES_SAHEL + unresolved structure.

Reutilise CRITICAL_ALIASES_SAHEL (N2) sans duplication.
"""

from src.couche_b.normalisation.engine import normalize, normalize_batch
from tests.normalisation.test_aliases_mandatory_sahel import CRITICAL_ALIASES_SAHEL


def test_critical_aliases_precision_1_0(db_conn):
    """
    Chaque alias de CRITICAL_ALIASES_SAHEL doit resoudre vers le bon item_id.
    Precision attendue : 1.0. Strategy : exact_alias_raw ou exact_normalized_alias.
    Gate N2 -- bloquant CI.
    """
    all_aliases = [alias for _, aliases in CRITICAL_ALIASES_SAHEL for alias in aliases]
    results = normalize_batch(all_aliases, db_conn)
    result_map = {r.input_raw: r for r in results}

    for item_id, aliases in CRITICAL_ALIASES_SAHEL:
        for alias in aliases:
            result = result_map[alias]
            assert result.item_id == item_id, (
                f"PRECISION FAIL -- alias='{alias}' "
                f"attendu='{item_id}' obtenu='{result.item_id}'"
            )
            assert (
                result.score == 1.0
            ), f"SCORE FAIL -- alias='{alias}' score={result.score} (attendu 1.0)"
            assert result.strategy in (
                "exact_alias_raw",
                "exact_normalized_alias",
            ), f"STRATEGY FAIL -- alias='{alias}' strategy='{result.strategy}'"
            assert result.item_id is not None


def test_unresolved_returns_structured_result(db_conn):
    """
    Noise -> NormalisationResult(strategy=UNRESOLVED, item_id=None, score=0.0).
    Jamais None. Jamais exception.
    Gate N2 -- bloquant CI.
    """
    noise = [
        "xyzabc123incomprehensible",
        "qqqqq",
        "!!!",
        "00000000",
    ]
    for raw in noise:
        result = normalize(raw, db_conn)
        assert (
            result is not None
        ), f"normalize() a retourne None pour '{raw}' (interdit)"
        assert (
            result.strategy == "unresolved"
        ), f"STRATEGY FAIL -- '{raw}' -> strategy='{result.strategy}' (attendu 'unresolved')"
        assert (
            result.item_id is None
        ), f"FAUX POSITIF -- '{raw}' -> item_id='{result.item_id}' (interdit)"
        assert (
            result.score == 0.0
        ), f"SCORE FAIL -- '{raw}' -> score={result.score} (attendu 0.0)"
