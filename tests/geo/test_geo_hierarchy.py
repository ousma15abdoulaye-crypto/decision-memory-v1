"""
Tests hiérarchie géographique — pays → région → cercle → commune.
Prouve les FK et la traversabilité de la hiérarchie.
"""

from __future__ import annotations


def test_region_fk_references_country(db_conn, geo_seed):
    """Toutes les régions doivent avoir un country_id valide."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS orphans
            FROM geo_regions r
            LEFT JOIN geo_countries c ON c.id = r.country_id
            WHERE c.id IS NULL
            """)
        row = cur.fetchone()
    assert row["orphans"] == 0


def test_cercle_fk_references_region(db_conn, geo_seed):
    """Tous les cercles doivent avoir un region_id valide."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS orphans
            FROM geo_cercles c
            LEFT JOIN geo_regions r ON r.id = c.region_id
            WHERE r.id IS NULL
            """)
        row = cur.fetchone()
    assert row["orphans"] == 0


def test_commune_fk_references_cercle(db_conn, geo_seed):
    """Toutes les communes doivent avoir un cercle_id valide."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS orphans
            FROM geo_communes com
            LEFT JOIN geo_cercles cer ON cer.id = com.cercle_id
            WHERE cer.id IS NULL
            """)
        row = cur.fetchone()
    assert row["orphans"] == 0


def test_full_hierarchy_traversal(db_conn, geo_seed):
    """Traversée Mali → Mopti → Cercle → Commune doit retourner des résultats."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT com.name_fr AS commune, cer.name_fr AS cercle,
                   reg.name_fr AS region, cou.name_fr AS pays
            FROM geo_communes com
            JOIN geo_cercles cer ON cer.id = com.cercle_id
            JOIN geo_regions reg ON reg.id = cer.region_id
            JOIN geo_countries cou ON cou.id = reg.country_id
            WHERE cou.iso2 = 'ML'
              AND reg.name_fr = 'Mopti'
            ORDER BY com.name_fr
            """)
        rows = cur.fetchall()
    assert len(rows) >= 1
    for row in rows:
        assert row["pays"] == "Mali"
        assert row["region"] == "Mopti"


def test_mopti_has_8_cercles(db_conn, geo_seed):
    """La région Mopti doit avoir exactement 8 cercles seedés."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM geo_cercles cer
            JOIN geo_regions reg ON reg.id = cer.region_id
            WHERE reg.name_fr = 'Mopti'
            """)
        row = cur.fetchone()
    assert row["cnt"] == 8


def test_unique_constraint_region_code(db_conn, geo_seed):
    """Un même code ne peut apparaître deux fois pour un même pays."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT country_id, code, COUNT(*) AS cnt
            FROM geo_regions
            GROUP BY country_id, code
            HAVING COUNT(*) > 1
            """)
        duplicates = cur.fetchall()
    assert len(duplicates) == 0


def test_unique_constraint_cercle_code(db_conn, geo_seed):
    """Un même code ne peut apparaître deux fois pour une même région."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT region_id, code, COUNT(*) AS cnt
            FROM geo_cercles
            GROUP BY region_id, code
            HAVING COUNT(*) > 1
            """)
        duplicates = cur.fetchall()
    assert len(duplicates) == 0


def test_unique_constraint_commune_code_instat(db_conn, geo_seed):
    """code_instat doit être unique dans geo_communes."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT code_instat, COUNT(*) AS cnt
            FROM geo_communes
            GROUP BY code_instat
            HAVING COUNT(*) > 1
            """)
        duplicates = cur.fetchall()
    assert len(duplicates) == 0
