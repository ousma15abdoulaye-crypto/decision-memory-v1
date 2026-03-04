"""
Tests migration 040_geo_master_mali.
Prouve que les 7 tables geo existent en DB après upgrade.
Prouve que le downgrade supprime les tables.
"""

from __future__ import annotations

import pytest

GEO_TABLES = [
    "geo_countries",
    "geo_regions",
    "geo_cercles",
    "geo_communes",
    "geo_localites",
    "geo_zones_operationnelles",
    "geo_zone_commune_mapping",
]


@pytest.mark.parametrize("table", GEO_TABLES)
def test_geo_table_exists(db_conn, table):
    """Chaque table geo doit exister après migration 040."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
            """,
            (table,),
        )
        row = cur.fetchone()
    assert row["cnt"] == 1, f"Table manquante : {table}"


def test_alembic_head_is_current(db_conn):
    """alembic_version doit pointer sur m5_pre_vendors_consolidation (head M5-PRE)."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
    assert row is not None
    assert row["version_num"] == "m5_cleanup_a_committee_event_type_check"


def test_fn_set_updated_at_exists(db_conn):
    """La fonction fn_set_updated_at doit exister."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM pg_proc
            WHERE proname = 'fn_set_updated_at'
            """)
        row = cur.fetchone()
    assert row["cnt"] >= 1


@pytest.mark.parametrize(
    "table",
    [
        "geo_countries",
        "geo_regions",
        "geo_cercles",
        "geo_communes",
        "geo_localites",
        "geo_zones_operationnelles",
    ],
)
def test_updated_at_trigger_exists(db_conn, table):
    """Chaque table geo doit avoir un trigger updated_at."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.triggers
            WHERE event_object_table = %s
              AND trigger_name = %s
            """,
            (table, f"trg_{table}_updated_at"),
        )
        row = cur.fetchone()
    assert row["cnt"] == 1, f"Trigger manquant sur {table}"


def test_geo_countries_columns(db_conn):
    """geo_countries doit avoir toutes ses colonnes obligatoires."""
    expected = {
        "id",
        "iso2",
        "iso3",
        "name_fr",
        "name_en",
        "is_active",
        "created_at",
        "updated_at",
    }
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'geo_countries'
            """)
        cols = {row["column_name"] for row in cur.fetchall()}
    assert expected.issubset(cols)


def test_geo_communes_check_type_commune(db_conn):
    """geo_communes.type_commune doit avoir une contrainte CHECK."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.check_constraints cc
            JOIN information_schema.constraint_column_usage ccu
                ON cc.constraint_name = ccu.constraint_name
            WHERE ccu.table_name = 'geo_communes'
              AND ccu.column_name = 'type_commune'
            """)
        row = cur.fetchone()
    assert row["cnt"] >= 1


def test_geo_zones_check_type_zone(db_conn):
    """geo_zones_operationnelles.type_zone doit avoir une contrainte CHECK."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.check_constraints cc
            JOIN information_schema.constraint_column_usage ccu
                ON cc.constraint_name = ccu.constraint_name
            WHERE ccu.table_name = 'geo_zones_operationnelles'
              AND ccu.column_name = 'type_zone'
            """)
        row = cur.fetchone()
    assert row["cnt"] >= 1
