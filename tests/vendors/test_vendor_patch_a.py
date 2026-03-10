"""
Tests PATCH-A + consolidation M5-PRE — état post-consolidation V4.1.0.
DoD PA1-PA11 mis à jour après migration m5_pre_vendors_consolidation.

Historique :
  PATCH-A (Option B) : vendor_identities conservait son nom · vendors legacy intacte
  M5-PRE consolidation : vendor_identities → vendors · vendors legacy supprimée
  Référence courante   : vendors (ex vendor_identities · 34 colonnes)

Contraintes renommées par consolidation :
  uq_vi_canonical_name  → uq_vendors_canonical_name
  vendor_identities_pkey → vendors_pkey  (géré par PK)
Index renommés :
  idx_vi_canonical    → idx_vendors_canonical
  idx_vi_verification → idx_vendors_verification
"""

import pytest

# ── PA1 : vendors existe · vendors legacy supprimée ──────────────


def test_pa1_vendors_table_exists(db_conn):
    """PA1 : vendors (ex vendor_identities) doit exister après consolidation."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.tables "
            "WHERE table_name = 'vendors'"
        )
        assert cur.fetchone()["n"] == 1


def test_pa1_legacy_vendors_removed(db_conn):
    """PA1 : La table vendors legacy (4 colonnes) doit être supprimée par m5_pre."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'vendors' ORDER BY ordinal_position"
        )
        cols = [r["column_name"] for r in cur.fetchall()]
    # vendors ne doit plus avoir le schema legacy (id, name, zone_id, created_at)
    # Il doit avoir le schema canonique vendor_identities (34 colonnes)
    assert (
        "name_normalized" in cols
    ), f"vendors ne semble pas être l'ex vendor_identities — colonnes : {cols[:5]}"
    assert (
        "fingerprint" in cols
    ), "fingerprint absent — vendors ne semble pas être l'ex vendor_identities"


# ── PA2 : données intactes ────────────────────────────────────────


def test_pa2_data_preserved(db_conn):
    """PA2 : Les colonnes M4 originales sont préservées sur vendors."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.columns "
            "WHERE table_name = 'vendors' "
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
            "WHERE table_name = 'vendors' "
            "AND column_name = 'canonical_name'"
        )
        row = cur.fetchone()
    assert row is not None, "canonical_name absente"
    assert row["is_nullable"] == "NO", "canonical_name doit être NOT NULL"


def test_pa4_canonical_name_unique_constraint(db_conn):
    """PA4 : UNIQUE(canonical_name) doit être actif sous son nouveau nom."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.table_constraints "
            "WHERE table_name = 'vendors' "
            "AND constraint_name = 'uq_vendors_canonical_name'"
        )
        assert cur.fetchone()["n"] == 1, "Contrainte uq_vendors_canonical_name absente"


# ── PA5 : verification_status · pas de suspended auto-mappé ──────


def test_pa5_verification_status_column_exists(db_conn):
    """PA5 : verification_status doit exister avec contrainte CHECK."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.check_constraints cc "
            "JOIN information_schema.constraint_column_usage ccu "
            "  ON cc.constraint_name = ccu.constraint_name "
            "WHERE ccu.table_name = 'vendors' "
            "AND ccu.column_name = 'verification_status'"
        )
        assert cur.fetchone()["n"] >= 1, "CHECK sur verification_status absent"


def test_pa5_no_suspended_auto_mapped(db_conn):
    """PA5 : Aucun vendor ne doit avoir verification_status = suspended après mapping auto."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM vendors "
            "WHERE verification_status = 'suspended'"
        )
        assert (
            cur.fetchone()["n"] == 0
        ), "suspended auto-mappé détecté — mapping incorrect"


# ── PA6 : trigger actif ───────────────────────────────────────────


def test_pa6_trigger_still_active(db_conn):
    """PA6 : Trigger updated_at doit toujours être actif sur vendors."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.triggers "
            "WHERE event_object_table = 'vendors' "
            "AND trigger_name = 'trg_vendor_updated_at'"
        )
        assert cur.fetchone()["n"] == 1, "Trigger trg_vendor_updated_at manquant"


# ── PA7 : index Couche B présents (renommés post-consolidation) ───


@pytest.mark.parametrize("idx", ["idx_vendors_verification", "idx_vendors_canonical"])
def test_pa7_couche_b_indexes_exist(db_conn, idx):
    """PA7 : Index Couche B doivent être présents sous leurs nouveaux noms."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM pg_indexes "
            "WHERE tablename = 'vendors' AND indexname = %s",
            (idx,),
        )
        assert cur.fetchone()["n"] == 1, f"Index manquant : {idx}"


# ── PA8 : alembic head ────────────────────────────────────────────


def test_alembic_head_est_m7_4a(db_conn):
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
    assert (
        row["version_num"] == repo_head
    ), f"Head repo={repo_head} — DB={row['version_num']} — désaligné"


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
    """Chaque colonne V4.1.0 doit être présente sur vendors (ex vendor_identities)."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.columns "
            "WHERE table_name = 'vendors' AND column_name = %s",
            (col,),
        )
        assert cur.fetchone()["n"] == 1, f"Colonne manquante : {col}"


def test_last_verified_at_renamed_to_verified_at(db_conn):
    """last_verified_at doit être renommée en verified_at."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM information_schema.columns "
            "WHERE table_name = 'vendors' "
            "AND column_name = 'last_verified_at'"
        )
        assert (
            cur.fetchone()["n"] == 0
        ), "last_verified_at encore présente — rename raté"
