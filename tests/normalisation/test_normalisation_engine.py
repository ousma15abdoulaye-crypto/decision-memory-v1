"""
Tests bloquants -- M-NORMALISATION-ENGINE
Gate CI : precision 1.0 sur CRITICAL_ALIASES_SAHEL + zero faux positif.

Reutilise CRITICAL_ALIASES_SAHEL (N2) sans duplication.
"""

from src.couche_b.normalisation.engine import normalize_batch
from tests.normalisation.test_aliases_mandatory_sahel import CRITICAL_ALIASES_SAHEL

# Inputs qui ne doivent JAMAIS matcher quoi que ce soit
_NOISE_INPUTS = [
    "xxxxxinconnu",
    "random string 999",
    "not a real procurement item",
    "zzzz_noise_42",
    "abcdefghijklmnop",
    "lorem ipsum dolor",
    "$$##@@!!",
    "0000000",
]


def test_critical_aliases_precision_1_0():
    """
    Chaque alias de CRITICAL_ALIASES_SAHEL doit resoudre vers le bon item_id.
    Precision attendue : 1.0 (zero miss tolere).
    Gate N2 -- bloquant CI.
    """
    all_aliases = [alias for _, aliases in CRITICAL_ALIASES_SAHEL for alias in aliases]
    results = normalize_batch(all_aliases)

    for item_id, aliases in CRITICAL_ALIASES_SAHEL:
        for alias in aliases:
            actual = results.get(alias)
            assert actual == item_id, (
                f"PRECISION FAIL -- alias='{alias}' "
                f"attendu='{item_id}' obtenu='{actual}'"
            )


def test_zero_false_positives_on_noise():
    """
    Les inputs bruites ne doivent jamais produire de match.
    Zero faux positif tolere.
    Gate N2 -- bloquant CI.
    """
    results = normalize_batch(_NOISE_INPUTS)

    for alias in _NOISE_INPUTS:
        actual = results.get(alias)
        assert (
            actual is None
        ), f"FAUX POSITIF -- alias='{alias}' a matche item_id='{actual}' (interdit)"
