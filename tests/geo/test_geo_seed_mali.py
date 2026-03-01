"""
Tests seed Mali — M3.
Prouve que le seed minimal réel est présent et cohérent.

Périmètre M3 : pays, régions, cercles Mopti, communes minimales.
geo_zones_operationnelles non seedée en M3 (table existe, données chargées hors M3).
"""

from __future__ import annotations

import pytest

from src.geo.seed_mali import (
    MALI_REGIONS,
    MOPTI_CERCLES,
    MOPTI_COMMUNES_MIN,
)

# ── Pays ─────────────────────────────────────────────────────────────────────


def test_mali_country_seeded(db_conn, geo_seed):
    """Le Mali doit être présent dans geo_countries."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT * FROM geo_countries WHERE iso2 = 'ML'")
        row = cur.fetchone()
    assert row is not None
    assert row["iso3"] == "MLI"
    assert row["name_fr"] == "Mali"
    assert row["is_active"] is True


# ── Régions ──────────────────────────────────────────────────────────────────


def test_mali_has_11_regions(db_conn, geo_seed):
    """Le Mali doit avoir exactement 11 régions seedées."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM geo_regions r
            JOIN geo_countries c ON c.id = r.country_id
            WHERE c.iso2 = 'ML'
            """)
        row = cur.fetchone()
    assert row["cnt"] == len(MALI_REGIONS)  # 11


@pytest.mark.parametrize("region", MALI_REGIONS)
def test_region_present(db_conn, geo_seed, region):
    """Chaque région du seed doit exister en DB."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM geo_regions WHERE code = %(code)s",
            {"code": region["code"]},
        )
        row = cur.fetchone()
    assert row is not None, f"Région manquante : {region['code']} — {region['name_fr']}"


def test_mopti_region_seeded(db_conn, geo_seed):
    """La région Mopti (ML-5) doit être présente."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT * FROM geo_regions WHERE code = 'ML-5'")
        row = cur.fetchone()
    assert row is not None
    assert row["name_fr"] == "Mopti"
    assert row["capitale"] == "Mopti"


# ── Cercles Mopti ─────────────────────────────────────────────────────────────


def test_mopti_cercles_count(db_conn, geo_seed):
    """8 cercles Mopti doivent être seedés."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM geo_cercles cer
            JOIN geo_regions reg ON reg.id = cer.region_id
            WHERE reg.code = 'ML-5'
            """)
        row = cur.fetchone()
    assert row["cnt"] == len(MOPTI_CERCLES)  # 8


@pytest.mark.parametrize("cercle", MOPTI_CERCLES)
def test_cercle_mopti_present(db_conn, geo_seed, cercle):
    """Chaque cercle Mopti du seed doit exister en DB."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM geo_cercles WHERE code = %(code)s",
            {"code": cercle["code"]},
        )
        row = cur.fetchone()
    assert row is not None, f"Cercle manquant : {cercle['code']} — {cercle['name_fr']}"


# ── Communes ─────────────────────────────────────────────────────────────────


def test_communes_min_count(db_conn, geo_seed):
    """4 communes minimales Mopti doivent être seedées."""
    codes = [c["code_instat"] for c in MOPTI_COMMUNES_MIN]
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM geo_communes WHERE code_instat = ANY(%s)",
            (codes,),
        )
        row = cur.fetchone()
    assert row["cnt"] == len(MOPTI_COMMUNES_MIN)  # 4


@pytest.mark.parametrize("commune", MOPTI_COMMUNES_MIN)
def test_commune_present(db_conn, geo_seed, commune):
    """Chaque commune du seed doit exister en DB."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM geo_communes WHERE code_instat = %(code)s",
            {"code": commune["code_instat"]},
        )
        row = cur.fetchone()
    assert row is not None
    assert row["type_commune"] == commune["type_commune"]


# ── Zones opérationnelles — non seedées en M3 ────────────────────────────────


def test_zones_table_exists_but_empty_in_m3(db_conn, geo_seed):
    """geo_zones_operationnelles existe mais n'est pas seedée en M3."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM geo_zones_operationnelles")
        row = cur.fetchone()
    assert row["cnt"] == 0, (
        "geo_zones_operationnelles doit rester vide en M3 "
        "(données organisationnelles hors périmètre M3)"
    )


# ── Idempotence ───────────────────────────────────────────────────────────────


def test_seed_idempotent(db_conn, geo_seed):
    """Exécuter le seed deux fois ne doit pas créer de doublons."""
    from src.geo.seed_mali import run_seed

    run_seed(db_conn)  # 2e exécution

    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM geo_countries WHERE iso2 = 'ML'")
        assert cur.fetchone()["cnt"] == 1

        cur.execute("""
            SELECT COUNT(*) AS cnt FROM geo_regions r
            JOIN geo_countries c ON c.id = r.country_id
            WHERE c.iso2 = 'ML'
            """)
        assert cur.fetchone()["cnt"] == 11
