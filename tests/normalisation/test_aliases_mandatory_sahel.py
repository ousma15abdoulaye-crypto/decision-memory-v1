"""
Test : Aliases obligatoires Sahel présents en DB
Gate : 🔴 BLOQUANT CI (actif dès M-NORMALISATION-ITEMS)
ADR  : ADR-0002 §2.1
"""
import pytest


CRITICAL_ALIASES_SAHEL = [
    ("gasoil", ["gas oil", "diesel", "gaz oil", "GO"]),
    ("ciment CPA 42.5", ["ciment 42.5", "CPA42,5", "CPJ 42.5"]),
    ("fer HA 12mm barre 12m", ["rond tor 12", "HA12", "tor 12"]),
    ("sable fleuve 7m3", ["sable du fleuve", "sable voyage"]),
    ("Toyota Land Cruiser 4x4 HZJ78", ["Land Cruiser 78", "LC 78"]),
    ("paracetamol 500mg comprimé", ["doliprane 500", "efferalgan 500"]),
]


@pytest.mark.skip(
    reason="À implémenter dans M-NORMALISATION-ITEMS. "
           "Vérifier que les aliases critiques Sahel (ADR-0002 §2.1) "
           "sont présents dans la DB après le seed. "
           "🔴 BLOQUE CI quand actif."
)
def test_critical_aliases_sahel_present_in_db():
    """
    Les aliases Sahel les plus critiques doivent être en DB.
    Source : ADR-0002 §2.1 ALIASES_MANDATORY_SAHEL.
    🔴 BLOQUE CI quand actif.
    """
    for canonical, required_aliases in CRITICAL_ALIASES_SAHEL:
        for alias in required_aliases:
            # assert alias_exists_in_db(canonical, alias)
            pass
