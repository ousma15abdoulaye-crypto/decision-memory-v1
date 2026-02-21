"""
Test : Couverture minimale dictionnaire procurement Sahel
Gate : BLOQUANT CI
ADR  : ADR-0002 §2.1
"""

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


def test_dict_minimum_coverage_all_families(db_conn):
    """
    9 familles x >= 5 items actifs x >= 3 aliases chacun.
    ADR-0002 §2.1
    """
    cur = db_conn.cursor()

    for family in MANDATORY_FAMILIES:
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE family_id = %s
              AND active = TRUE
            """,
            (family,),
        )
        item_count = cur.fetchone()["n"]
        assert item_count >= MINIMUM_ITEMS_PER_FAMILY, (
            f"Famille '{family}' : {item_count} items actifs "
            f"(minimum : {MINIMUM_ITEMS_PER_FAMILY}) — ADR-0002 §2.1"
        )

        cur.execute(
            """
            SELECT i.item_id, COUNT(a.alias_id) AS alias_count
            FROM couche_b.procurement_dict_items i
            LEFT JOIN couche_b.procurement_dict_aliases a
                   ON a.item_id = i.item_id
            WHERE i.family_id = %s
              AND i.active = TRUE
            GROUP BY i.item_id
            HAVING COUNT(a.alias_id) < %s
            """,
            (family, MINIMUM_ALIASES_PER_ITEM),
        )
        under_aliased = cur.fetchall()
        assert len(under_aliased) == 0, (
            f"Famille '{family}' — items avec < {MINIMUM_ALIASES_PER_ITEM} "
            f"aliases : {[r['item_id'] for r in under_aliased]} "
            f"— ADR-0002 §2.1"
        )
