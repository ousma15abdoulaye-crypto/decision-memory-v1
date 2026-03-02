"""
Tests PATCH-A — réconciliation structurelle vendor_identities V4.1.0.
DoD PA1-PA11 (Option B : table conserve son nom vendor_identities).
"""

import pytest

# ── PA1 : vendor_identities existe · vendors legacy non touchée ──


def test_pa1_vendor_identities_exists(db_conn):
    """PA1 : vendor_identities doit exister."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.tables "
            "WHERE table_name = 'vendor_identities'"
        )
        assert cur.fetchone()["n"] == 1


def test_pa1_legacy_vendors_untouched(db_conn):
    """PA1 : La table vendors legacy (4 colonnes) ne doit pas être modifiée."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'vendors' ORDER BY ordinal_position"
        )
        cols = [r["column_name"] for r in cur.fetchall()]
    assert cols == ["id", "name", "zone_id", "created_at"], (
        f"vendors legacy altérée : {cols}"
    )


# ── PA2 : données intactes ────────────────────────────────────────


def test_pa2_data_preserved(db_conn):
    """PA2 : Les colonnes M4 originales sont préservées."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.columns "
            "WHERE table_name = 'vendor_identities' "
            "AND column_name IN ('vendor_id','fingerprint','name_normalized',"
            "'zone_normalized','region_code','activity_status')"
        )
        assert cur.fetchone()["n"] == 6


# ── PA4 : canonical_name NOT NULL · UNIQUE ────────────────────────


def test_pa4_canonical_name_column_exists(db_conn):
    """PA4 : canonical_name doit exister · NOT NULL · UNIQUE."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'vendor_identities' "
            "AND column_name = 'canonical_name'"
        )
        row = cur.fetchone()
    assert row is not None, "canonical_name absente"
    assert row["is_nullable"] == "NO", "canonical_name doit être NOT NULL"


def test_pa4_canonical_name_unique_constraint(db_conn):
    """PA4 : UNIQUE(canonical_name) doit être actif."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.table_constraints "
            "WHERE table_name = 'vendor_identities' "
            "AND constraint_name = 'uq_vi_canonical_name'"
        )
        assert cur.fetchone()["n"] == 1, "Contrainte uq_vi_canonical_name absente"


# ── PA5 : verification_status · pas de suspended auto-mappé ──────


def test_pa5_verification_status_column_exists(db_conn):
    """PA5 : verification_status doit exister avec contrainte CHECK."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.check_constraints cc "
            "JOIN information_schema.constraint_column_usage ccu "
            "  ON cc.constraint_name = ccu.constraint_name "
            "WHERE ccu.table_name = 'vendor_identities' "
            "AND ccu.column_name = 'verification_status'"
        )
        assert cur.fetchone()["n"] >= 1, "CHECK sur verification_status absent"


def test_pa5_no_suspended_auto_mapped(db_conn):
    """PA5 : Aucun vendor ne doit avoir verification_status = suspended après mapping auto."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM vendor_identities "
            "WHERE verification_status = 'suspended'"
        )
        assert cur.fetchone()["n"] == 0, "suspended auto-mappé détecté — mapping incorrect"


# ── PA6 : trigger actif ───────────────────────────────────────────


def test_pa6_trigger_still_active(db_conn):
    """PA6 : Trigger updated_at doit toujours être actif sur vendor_identities."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.triggers "
            "WHERE event_object_table = 'vendor_identities' "
            "AND trigger_name = 'trg_vendor_updated_at'"
        )
        assert cur.fetchone()["n"] == 1, "Trigger trg_vendor_updated_at manquant"


# ── PA7 : index Couche B présents ────────────────────────────────


@pytest.mark.parametrize("idx", ["idx_vi_verification", "idx_vi_canonical"])
def test_pa7_couche_b_indexes_exist(db_conn, idx):
    """PA7 : Index Couche B doivent être présents."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM pg_indexes "
            "WHERE tablename = 'vendor_identities' AND indexname = %s",
            (idx,),
        )
        assert cur.fetchone()["n"] == 1, f"Index manquant : {idx}"


# ── PA8 : alembic head ────────────────────────────────────────────


def test_pa8_alembic_head_is_patch_a(db_conn):
    """PA8 : alembic_version doit pointer sur m4_patch_a_fix."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
    assert row["version_num"] == "m4_patch_a_fix", (
        f"Head attendu : m4_patch_a_fix — réel : {row['version_num']}"
    )


# ── Colonnes V4.1.0 présentes ─────────────────────────────────────


@pytest.mark.parametrize(
    "col",
    [
        "canonical_name",
        "aliases",
        "nif",
        "rccm",
        "rib",
        "verification_status",
        "vcrn",
        "zones_covered",
        "category_ids",
        "has_sanctions_cert",
        "has_sci_conditions",
        "key_personnel_verified",
        "suspension_reason",
        "suspended_at",
        "verified_at",
    ],
)
def test_v410_column_exists(db_conn, col):
    """Chaque colonne V4.1.0 doit être présente sur vendor_identities."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.columns "
            "WHERE table_name = 'vendor_identities' AND column_name = %s",
            (col,),
        )
        assert cur.fetchone()["n"] == 1, f"Colonne manquante : {col}"


def test_last_verified_at_renamed_to_verified_at(db_conn):
    """last_verified_at doit être renommée en verified_at."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.columns "
            "WHERE table_name = 'vendor_identities' "
            "AND column_name = 'last_verified_at'"
        )
        assert cur.fetchone()["n"] == 0, "last_verified_at encore présente — rename raté"
