"""
Test : Aliases obligatoires Sahel présents en DB
Gate : BLOQUANT CI
ADR  : ADR-0002 §2.1
"""

# item_id (clé DB) + alias_raw attendus (forme terrain exacte seedée)
CRITICAL_ALIASES_SAHEL = [
    ("gasoil", ["gas oil", "diesel", "gaz oil", "GO"]),
    ("ciment_cpa_42_5", ["ciment 42.5", "CPA42,5", "CPJ 42.5"]),
    ("fer_ha_12_barre_12m", ["rond tor 12", "HA12", "tor 12"]),
    ("sable_fleuve_7m3", ["sable du fleuve", "sable voyage"]),
    ("toyota_land_cruiser_hzj78", ["Land Cruiser 78", "LC 78"]),
    ("paracetamol_500mg_boite_100cp", ["doliprane 500", "efferalgan 500"]),
]


def test_critical_aliases_sahel_present_in_db(db_conn):
    """
    Les aliases Sahel critiques doivent être présents en DB (alias_raw exact).
    ADR-0002 §2.1
    """
    cur = db_conn.cursor()

    for item_id, required_aliases in CRITICAL_ALIASES_SAHEL:
        for alias_raw in required_aliases:
            cur.execute(
                """
                SELECT 1
                FROM couche_b.procurement_dict_aliases
                WHERE item_id = %s
                  AND alias_raw = %s
                """,
                (item_id, alias_raw),
            )
            assert cur.fetchone() is not None, (
                f"Alias manquant — item_id='{item_id}' "
                f"alias_raw='{alias_raw}' absent — ADR-0002 §2.1"
            )
