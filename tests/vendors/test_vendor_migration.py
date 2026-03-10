"""
Tests migration vendors — état post-consolidation m5_pre_vendors_consolidation.
Prouve table vendors · contraintes · index · trigger actifs après consolidation.

Historique :
  041_vendor_identities  : créait la table vendor_identities
  m4_patch_a_fix         : ajoutait colonnes V4.1.0 sur vendor_identities
  m5_pre_vendors_consolidation : vendor_identities → vendors · legacy supprimée
  Référence courante     : vendors (ex vendor_identities · 34 colonnes)
"""

from __future__ import annotations

import pytest


def test_vendors_table_exists(db_conn):
    """Table vendors (ex vendor_identities) doit exister après consolidation."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'vendors'
            """)
        row = cur.fetchone()
    assert row["cnt"] == 1, "Table vendors manquante"


def test_alembic_head_is_current(db_conn):
    """alembic_version DB doit correspondre au head repo courant (dynamique)."""
    import subprocess

    result = subprocess.run(["alembic", "heads"], capture_output=True, text=True)
    repo_head = next(
        (
            line.strip().split()[0]
            for line in result.stdout.splitlines()
            if line.strip() and not line.startswith("INFO")
        ),
        None,
    )
    assert repo_head is not None, "alembic heads n'a retourné aucune valeur"
    with db_conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
    assert row is not None
    assert (
        row["version_num"] == repo_head
    ), f"Head repo={repo_head} — DB={row['version_num']} — désaligné"


def test_chk_vendor_id_format_active(db_conn):
    """INSERT avec vendor_id non préfixé DMS-VND- doit lever une violation."""
    with db_conn.cursor() as cur:
        with pytest.raises(Exception, match="chk_vendor_id_format"):
            cur.execute("""
                INSERT INTO vendors
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
                INSERT INTO vendors
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
            INSERT INTO vendors
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
                INSERT INTO vendors
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
        cur.execute("DELETE FROM vendors WHERE fingerprint = %s", (fp,))


def test_vendor_updated_at_trigger_exists(db_conn):
    """Trigger trg_vendor_updated_at doit exister sur vendors."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.triggers
            WHERE event_object_table = 'vendors'
              AND trigger_name = 'trg_vendor_updated_at'
            """)
        row = cur.fetchone()
    assert row["cnt"] == 1, "Trigger trg_vendor_updated_at manquant"


def test_vendors_columns(db_conn):
    """vendors doit avoir toutes ses colonnes obligatoires (ex vendor_identities)."""
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
              AND table_name = 'vendors'
            """)
        cols = {row["column_name"] for row in cur.fetchall()}
    assert expected.issubset(cols), f"Colonnes manquantes : {expected - cols}"
