"""
Test : Couverture minimale dictionnaire procurement Sahel
Gate : 🔴 BLOQUANT CI (actif dès M-NORMALISATION-ITEMS)
ADR  : ADR-0002 §2.1
"""

import pytest

MANDATORY_FAMILIES = [
    "carburants",
    "construction_liants",
    "construction_agregats",
    "construction_fer",
    "vehicules",
    "informatique",
    "alimentation",
    "medicaments",
    "equipements",
]

MINIMUM_ITEMS_PER_FAMILY = 5
MINIMUM_ALIASES_PER_ITEM = 3


@pytest.mark.skip(
    reason="À implémenter dans M-NORMALISATION-ITEMS. "
    "Vérifier que le dictionnaire contient au minimum "
    "5 items par famille et 3 aliases par item "
    "pour les 9 familles Sahel obligatoires (ADR-0002 §2.1). "
    "🔴 BLOQUE CI quand actif."
)
def test_dict_minimum_coverage_all_families():
    """
    Garantit la couverture minimale du dictionnaire procurement.
    9 familles × 5 items × 3 aliases minimum.
    🔴 BLOQUE CI quand actif.
    """
    for family in MANDATORY_FAMILIES:
        # items = get_items_by_family(family)
        # assert len(items) >= MINIMUM_ITEMS_PER_FAMILY
        # for item in items:
        #     aliases = get_aliases(item.id)
        #     assert len(aliases) >= MINIMUM_ALIASES_PER_ITEM
        pass
