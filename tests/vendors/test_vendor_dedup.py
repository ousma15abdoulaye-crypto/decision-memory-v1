"""
Tests déduplication vendor — M4.
Prouve que le fingerprint anti-doublon est actif et fiable.
"""

from __future__ import annotations

import pytest

from src.vendors.repository import generate_fingerprint, insert_vendor


@pytest.fixture(autouse=True)
def cleanup_test_vendors(db_conn):
    """Nettoie les vendors de test avant et après chaque test."""
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'TEST_DEDUP'")
    yield
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'TEST_DEDUP'")


def test_same_vendor_inserted_twice_only_one_record(db_conn):
    """Même vendor inséré deux fois → 1 seul enregistrement en DB."""
    kwargs = dict(
        name_raw="Alpha SARL",
        name_normalized="alpha sarl",
        zone_raw="BAMAKO",
        zone_normalized="bamako",
        region_code="BKO",
        category_raw=None,
        email=None,
        phone=None,
        email_verified=False,
        source="TEST_DEDUP",
    )
    vid1 = insert_vendor(**kwargs)
    vid2 = insert_vendor(**kwargs)

    assert vid1 is not None, "Premier insert doit réussir"
    assert vid2 is None, "Deuxième insert doit retourner None (doublon)"

    with db_conn.cursor() as cur:
        fp = generate_fingerprint("alpha sarl", "BKO")
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM vendors WHERE fingerprint = %s",
            (fp,),
        )
        row = cur.fetchone()
    assert row["cnt"] == 1, f"Attendu 1 enregistrement · trouvé : {row['cnt']}"


def test_duplicate_fingerprint_second_insert_returns_none():
    """Fingerprint identique → deuxième insert retourne None."""
    kwargs = dict(
        name_raw="Beta SCI",
        name_normalized="beta sci",
        zone_raw="MOPTI",
        zone_normalized="mopti",
        region_code="MPT",
        category_raw="Transport",
        email=None,
        phone=None,
        email_verified=False,
        source="TEST_DEDUP",
    )
    first = insert_vendor(**kwargs)
    second = insert_vendor(**kwargs)

    assert first is not None
    assert second is None


def test_different_casing_deduplication():
    """Noms avec casse différente → dédupliqués via name_normalized."""
    base = dict(
        zone_raw="BAMAKO",
        zone_normalized="bamako",
        region_code="BKO",
        category_raw=None,
        email=None,
        phone=None,
        email_verified=False,
        source="TEST_DEDUP",
    )
    vid1 = insert_vendor(
        name_raw="Gamma Tech SARL",
        name_normalized="gamma tech sarl",
        **base,
    )
    vid2 = insert_vendor(
        name_raw="GAMMA TECH SARL",
        name_normalized="gamma tech sarl",  # même normalisé
        **base,
    )

    assert vid1 is not None
    assert vid2 is None, "Doublon de casse doit être détecté"


def test_different_region_not_deduplicated():
    """Même nom normalisé mais région différente = vendors distincts."""
    common = dict(
        name_raw="Delta Services",
        name_normalized="delta services",
        zone_raw="ZONE",
        category_raw=None,
        email=None,
        phone=None,
        email_verified=False,
        source="TEST_DEDUP",
    )
    vid_bko = insert_vendor(zone_normalized="bamako", region_code="BKO", **common)
    vid_mpt = insert_vendor(zone_normalized="mopti", region_code="MPT", **common)

    # Les deux doivent réussir — fingerprint inclut region_code
    assert vid_bko is not None, "BKO vendor doit s'insérer"
    assert vid_mpt is not None, "MPT vendor doit s'insérer"
    assert vid_bko != vid_mpt
