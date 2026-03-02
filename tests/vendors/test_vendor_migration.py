"""
Tests migration 041_vendor_identities.
Prouve table · contraintes · index · trigger actifs après upgrade.
"""

from __future__ import annotations

import pytest


def test_vendor_identities_table_exists(db_conn):
    """Table vendor_identities doit exister après migration 041."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'vendor_identities'
            """)
        row = cur.fetchone()
    assert row["cnt"] == 1, "Table vendor_identities manquante"


def test_alembic_head_is_current(db_conn):
    """alembic_version doit pointer sur m4_patch_a_fix (head M4-patch)."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
    assert row is not None
    assert row["version_num"] == "m4_patch_a_fix"


def test_chk_vendor_id_format_active(db_conn):
    """INSERT avec vendor_id non préfixé DMS-VND- doit lever une violation."""
    with db_conn.cursor() as cur:
        with pytest.raises(Exception, match="chk_vendor_id_format"):
            cur.execute("""
                INSERT INTO vendor_identities
                    (vendor_id, fingerprint, name_raw, name_normalized,
                     canonical_name, zone_normalized, region_code, source)
                VALUES
                    ('INVALID-ID', 'fp_test_bad', 'Test', 'test',
                     'test|BKO', 'bamako', 'BKO', 'TEST')
                """)


def test_chk_region_code_active(db_conn):
    """INSERT avec region_code invalide doit lever une violation."""
    with db_conn.cursor() as cur:
        with pytest.raises(Exception, match="chk_region_code"):
            cur.execute("""
                INSERT INTO vendor_identities
                    (vendor_id, fingerprint, name_raw, name_normalized,
                     canonical_name, zone_normalized, region_code, source)
                VALUES
                    ('DMS-VND-XXX-0001-A', 'fp_test_rgn', 'Test', 'test',
                     'test|XXX', 'zone', 'XXX', 'TEST')
                """)


def test_fingerprint_unique_constraint(db_conn):
    """Double INSERT avec même fingerprint doit lever une violation UNIQUE."""
    fp = "fp_unique_test_m4"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO vendor_identities
                (vendor_id, fingerprint, name_raw, name_normalized,
                 canonical_name, zone_normalized, region_code, source)
            VALUES
                ('DMS-VND-BKO-9901-Z', %s, 'Test Unique', 'test unique',
                 'test unique|BKO', 'bamako', 'BKO', 'TEST')
            """,
            (fp,),
        )
        with pytest.raises(Exception):
            cur.execute(
                """
                INSERT INTO vendor_identities
                    (vendor_id, fingerprint, name_raw, name_normalized,
                     canonical_name, zone_normalized, region_code, source)
                VALUES
                    ('DMS-VND-BKO-9902-Z', %s, 'Test Unique 2', 'test unique 2',
                     'test unique|BKO', 'bamako', 'BKO', 'TEST')
                """,
                (fp,),
            )
    # Nettoyage
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendor_identities WHERE fingerprint = %s", (fp,))


def test_vendor_updated_at_trigger_exists(db_conn):
    """Trigger trg_vendor_updated_at doit exister sur vendor_identities."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.triggers
            WHERE event_object_table = 'vendor_identities'
              AND trigger_name = 'trg_vendor_updated_at'
            """)
        row = cur.fetchone()
    assert row["cnt"] == 1, "Trigger trg_vendor_updated_at manquant"


def test_vendor_identities_columns(db_conn):
    """vendor_identities doit avoir toutes ses colonnes obligatoires."""
    expected = {
        "id",
        "vendor_id",
        "fingerprint",
        "name_raw",
        "name_normalized",
        "zone_raw",
        "zone_normalized",
        "region_code",
        "category_raw",
        "email",
        "phone",
        "email_verified",
        "is_active",
        "source",
        "created_at",
        "updated_at",
    }
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'vendor_identities'
            """)
        cols = {row["column_name"] for row in cur.fetchall()}
    assert expected.issubset(cols), f"Colonnes manquantes : {expected - cols}"
