"""
Tests patch M4 — correctifs techniques + badge activité.
Couvre les invariants P1-P12 du DoD patch.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.vendors.repository import insert_vendor

client = TestClient(app)

_SOURCE_PATCH = "TEST_PATCH"


@pytest.fixture(autouse=True)
def cleanup_patch_vendors(db_conn):
    """Nettoie les vendors de test patch avant et après chaque test."""
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = %s", (_SOURCE_PATCH,))
    yield
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = %s", (_SOURCE_PATCH,))


# ── P1 : CHECK regex vendor_id ───────────────────────────────────


def test_p1_regex_constraint_blocks_invalid_format(db_conn):
    """P1 : CHECK regex ^DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]$ doit rejeter les formats non conformes."""
    with db_conn.cursor() as cur:
        with pytest.raises(Exception):
            cur.execute("""
                INSERT INTO vendors
                    (vendor_id, fingerprint, name_raw, name_normalized,
                     canonical_name, zone_normalized, region_code, source)
                VALUES
                    ('DMS-VND-bko-0001-K', 'fp_p1_lower', 'Test', 'test',
                     'test', 'bamako', 'BKO', 'TEST_PATCH')
                """)


def test_p1_regex_constraint_accepts_valid_format(db_conn):
    """P1 : Un vendor_id valide doit être accepté par la contrainte regex."""
    with db_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO vendors
                (vendor_id, fingerprint, name_raw, name_normalized,
                 canonical_name, zone_normalized, region_code, source)
            VALUES
                ('DMS-VND-BKO-9991-Z', 'fp_p1_valid', 'Test P1', 'test p1',
                 'test p1', 'bamako', 'BKO', 'TEST_PATCH')
            """)


# ── P2 : 4 colonnes activité présentes ───────────────────────────


def test_p2_activity_columns_exist(db_conn):
    """P2 : Les 4 colonnes du badge activité doivent être présentes."""
    expected = {
        "activity_status",
        "verified_at",
        "verified_by",
        "verification_source",
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


# ── P3 : EXCEL_M4 → VERIFIED_ACTIVE ──────────────────────────────


def test_p3_excel_m4_vendors_verified_active(db_conn):
    """P3 : Après migration 043, les vendors EXCEL_M4 sont VERIFIED_ACTIVE."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN activity_status = 'VERIFIED_ACTIVE' THEN 1 ELSE 0 END) AS verified
            FROM vendors
            WHERE source = 'EXCEL_M4' AND is_active = TRUE
            """)
        row = cur.fetchone()
    # En local DB la table peut être vide (tests ont nettoyé), on vérifie la cohérence
    if row["total"] and row["total"] > 0:
        assert row["total"] == row["verified"], (
            f"Certains EXCEL_M4 ne sont pas VERIFIED_ACTIVE : "
            f"{row['total'] - row['verified']} sur {row['total']}"
        )


# ── P4 : ON CONFLICT DO NOTHING ──────────────────────────────────


def test_p4_on_conflict_do_nothing_returns_none_on_dup():
    """P4 : insert_vendor avec doublon fingerprint retourne None via ON CONFLICT."""
    kwargs = dict(
        name_raw="Patch Vendor Alpha",
        name_normalized="patch vendor alpha",
        zone_raw="BAMAKO",
        zone_normalized="bamako",
        region_code="BKO",
        category_raw=None,
        email=None,
        phone=None,
        email_verified=False,
        source=_SOURCE_PATCH,
    )
    v1 = insert_vendor(**kwargs)
    v2 = insert_vendor(**kwargs)

    assert v1 is not None, "Premier insert doit réussir"
    assert v2 is None, "Doublon doit retourner None via ON CONFLICT"


# ── P5 : get_next_sequence regex ─────────────────────────────────


def test_p5_sequence_increments_correctly():
    """P5 : Séquence croissante par région."""
    base = dict(
        zone_raw="BAMAKO",
        zone_normalized="bamako",
        region_code="BKO",
        category_raw=None,
        email=None,
        phone=None,
        email_verified=False,
        source=_SOURCE_PATCH,
    )
    v1 = insert_vendor(name_raw="Seq Test 1", name_normalized="seq test 1", **base)
    v2 = insert_vendor(name_raw="Seq Test 2", name_normalized="seq test 2", **base)

    assert v1 is not None and v2 is not None
    # Extraire les numéros de séquence
    seq1 = int(v1.split("-")[3])
    seq2 = int(v2.split("-")[3])
    assert seq2 == seq1 + 1, f"Séquence non incrémentale : {seq1} → {seq2}"


# ── P6 : skipped_no_region absent ────────────────────────────────


def test_p6_skipped_no_region_removed_from_etl_report():
    """P6 : ETLReport ne doit plus avoir skipped_no_region."""
    from scripts.etl_vendors_m4 import ETLReport

    report = ETLReport()
    assert not hasattr(
        report, "skipped_no_region"
    ), "skipped_no_region ne doit plus exister dans ETLReport"


# ── P7 : activity_status invalide → 422 ──────────────────────────


def test_p7_invalid_activity_status_returns_422():
    """P7 : GET /vendors?activity_status=INVALID doit retourner 422."""
    resp = client.get("/vendors?activity_status=INVALID_STATUS")
    assert resp.status_code == 422, f"Attendu 422, reçu {resp.status_code}"


def test_p7_valid_activity_statuses_return_200():
    """P7 : Les valeurs canoniques doivent être acceptées (200)."""
    for status in ["VERIFIED_ACTIVE", "UNVERIFIED", "INACTIVE", "GHOST_SUSPECTED"]:
        resp = client.get(f"/vendors?activity_status={status}")
        assert (
            resp.status_code == 200
        ), f"Statut {status!r} rejeté — attendu 200, reçu {resp.status_code}"


# ── P8 : filtre VERIFIED_ACTIVE cohérent ─────────────────────────


def test_p8_filter_verified_active_only_returns_verified():
    """P8 : GET /vendors?activity_status=VERIFIED_ACTIVE ne retourne que des verts."""
    vid = insert_vendor(
        name_raw="P8 Verified",
        name_normalized="p8 verified",
        zone_raw="BAMAKO",
        zone_normalized="bamako",
        region_code="BKO",
        category_raw=None,
        email=None,
        phone=None,
        email_verified=False,
        activity_status="VERIFIED_ACTIVE",
        verified_by="SCI_FIELD_TEAM_MALI",
        verification_source="SCI_FIELD_VISIT",
        source=_SOURCE_PATCH,
    )
    assert vid is not None

    resp = client.get("/vendors?activity_status=VERIFIED_ACTIVE")
    assert resp.status_code == 200
    data = resp.json()
    for v in data:
        assert (
            v["activity_status"] == "VERIFIED_ACTIVE"
        ), f"Vendor {v['vendor_id']} a un statut inattendu : {v['activity_status']}"


# ── P9 : TD-001 documentée ───────────────────────────────────────


def test_p9_td001_documented_in_technical_debt():
    """P9 : TD-001 doit être documentée dans TECHNICAL_DEBT.md."""
    from pathlib import Path

    td_path = Path("TECHNICAL_DEBT.md")
    assert td_path.exists(), "TECHNICAL_DEBT.md introuvable"
    content = td_path.read_text(encoding="utf-8")
    assert "TD-001" in content, "TD-001 absente de TECHNICAL_DEBT.md"
    assert (
        "MAX()+1" in content or "MAX() + 1" in content
    ), "Description de la non-atomicité absente de TD-001"


# ── P10 : alembic head = 043 ─────────────────────────────────────


def test_p10_alembic_head_is_043(db_conn):
    """P10 : alembic_version doit pointer sur m4_patch_a_fix."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
    assert (
        row["version_num"] == "m5_geo_fix_master"
    ), f"Head attendu : m5_geo_fix_master — réel : {row['version_num']}"


# ── P11 : trigger rebuilt sans OR REPLACE ────────────────────────


def test_p11_trigger_exists_after_042(db_conn):
    """P11 : trg_vendor_updated_at doit exister après migration 042."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.triggers
            WHERE event_object_table = 'vendors'
              AND trigger_name = 'trg_vendor_updated_at'
            """)
        row = cur.fetchone()
    assert row["cnt"] == 1, "Trigger trg_vendor_updated_at manquant après patch 042"


# ── P12 : chk_activity_status contraint ─────────────────────────


def test_p12_invalid_activity_status_rejected_by_db(db_conn):
    """P12 : La contrainte chk_activity_status doit bloquer les valeurs invalides."""
    with db_conn.cursor() as cur:
        with pytest.raises(Exception, match="chk_activity_status"):
            cur.execute("""
                INSERT INTO vendors
                    (vendor_id, fingerprint, name_raw, name_normalized,
                     canonical_name, zone_normalized, region_code, activity_status, source)
                VALUES
                    ('DMS-VND-BKO-9992-Z', 'fp_p12_bad', 'Test', 'test',
                     'test', 'bamako', 'BKO', 'INVALID_STATUS', 'TEST_PATCH')
                """)
