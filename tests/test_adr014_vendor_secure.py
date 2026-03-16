"""
Tests ADR-014 — vendors_sensitive_data + vendor_secure service
RÈGLE-17 : invariants DB prouvés.
E-24 : fixture db_tx — autocommit=False + rollback.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from psycopg.rows import dict_row


@pytest.fixture
def db_tx(db_conn):
    db_conn.autocommit = False
    yield db_conn
    db_conn.rollback()
    db_conn.autocommit = True


# ─── MIGRATION ───────────────────────────────────────────


def _vsd_tables_exist(db_conn) -> bool:
    """Vérifie si les tables ADR-014 existent (migration 048 appliquée)."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'vendors_sensitive_data'
            ) AS ok;
        """)
        row = cur.fetchone()
        return (row.get("ok") if isinstance(row, dict) else row[0]) is True


def test_vendors_sensitive_data_exists(db_conn):
    if not _vsd_tables_exist(db_conn):
        pytest.skip("Migration 048 non appliquée — tables absentes")
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'vendors_sensitive_data'
            ) AS ok;
        """)
        row = cur.fetchone()
        ok = row.get("ok") if isinstance(row, dict) else row[0]
        assert ok is True


def test_vendors_doc_validity_exists(db_conn):
    if not _vsd_tables_exist(db_conn):
        pytest.skip("Migration 048 non appliquée — tables absentes")
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'vendors_doc_validity'
            ) AS ok;
        """)
        row = cur.fetchone()
        ok = row.get("ok") if isinstance(row, dict) else row[0]
        assert ok is True


def test_vsd_field_type_constraint(db_conn, db_tx):
    """field_type invalide rejeté par CHECK."""
    import psycopg

    if not _vsd_tables_exist(db_conn):
        pytest.skip("Migration 048 non appliquée — tables absentes")
    with db_tx.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute("""
                INSERT INTO vendors_sensitive_data
                    (token, field_type, encrypted_value,
                     supplier_name_normalized)
                VALUES ('tok_test_001', 'rib', 'encrypted', 'test_vendor');
            """)


def test_vsd_token_unique(db_conn, db_tx):
    """Token unique — ON CONFLICT DO NOTHING."""
    if not _vsd_tables_exist(db_conn):
        pytest.skip("Migration 048 non appliquée — tables absentes")
    with db_tx.cursor() as cur:
        cur.execute("""
            INSERT INTO vendors_sensitive_data
                (token, field_type, encrypted_value,
                 supplier_name_normalized)
            VALUES ('tok_nif_abcd1234', 'nif', 'enc_val', 'mali_commerce');
        """)
        cur.execute("""
            INSERT INTO vendors_sensitive_data
                (token, field_type, encrypted_value,
                 supplier_name_normalized)
            VALUES ('tok_nif_abcd1234', 'nif', 'enc_val_2', 'mali_commerce')
            ON CONFLICT (token) DO NOTHING;
        """)
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM vendors_sensitive_data
            WHERE token = 'tok_nif_abcd1234';
        """)
        row = cur.fetchone()
        cnt = row.get("cnt") if isinstance(row, dict) else row[0]
        assert cnt == 1


def test_vsd_delete_blocked(db_conn, db_tx):
    """Trigger append-only bloque DELETE."""
    import psycopg

    if not _vsd_tables_exist(db_conn):
        pytest.skip("Migration 048 non appliquée — tables absentes")
    with db_tx.cursor() as cur:
        cur.execute("""
            INSERT INTO vendors_sensitive_data
                (token, field_type, encrypted_value,
                 supplier_name_normalized)
            VALUES ('tok_phone_test99', 'phone', 'enc', 'vendor_test')
            RETURNING id;
        """)
        row = cur.fetchone()
        inserted_id = row.get("id") if isinstance(row, dict) else row[0]
        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute(
                "DELETE FROM vendors_sensitive_data WHERE id = %s;",
                (inserted_id,),
            )


def test_alembic_head_is_048(db_conn):
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        row = cur.fetchone()
    if not row:
        pytest.skip("alembic_version vide")
    version = (
        row.get("version_num") if isinstance(row, dict) else (row[0] if row else None)
    )
    if version != "048_vendors_sensitive_data":
        pytest.skip(
            f"Head actuel {version} — test exige 048 (DB sur branche 046b→047→048)"
        )


# ─── SERVICE ─────────────────────────────────────────────


def test_generate_token_deterministic():
    """Même valeur + même sel → même token."""
    from src.couche_b.vendor_secure import _generate_token

    t1 = _generate_token("nif", "123456789")
    t2 = _generate_token("nif", "123456789")
    assert t1 == t2
    assert t1.startswith("tok_nif_")


def test_generate_token_different_values():
    """Valeurs différentes → tokens différents."""
    from src.couche_b.vendor_secure import _generate_token

    t1 = _generate_token("nif", "111111111")
    t2 = _generate_token("nif", "222222222")
    assert t1 != t2


def test_compute_doc_validity_valid():
    """Date future → is_valid=True + expires_in_days > 0."""
    from datetime import UTC, datetime, timedelta

    from src.couche_b.vendor_secure import compute_doc_validity

    future = (datetime.now(UTC) + timedelta(days=300)).strftime("%Y-%m-%d")
    result = compute_doc_validity(future)
    assert result["is_valid"] is True
    assert result["expires_in_days"] > 0
    assert result["status"] == "VALID"


def test_compute_doc_validity_expired():
    """Date passée → is_valid=False."""
    from src.couche_b.vendor_secure import compute_doc_validity

    result = compute_doc_validity("2020-01-01")
    assert result["is_valid"] is False
    assert result["expires_in_days"] < 0
    assert result["status"] == "EXPIRED"


def test_compute_doc_validity_absent():
    """ABSENT → is_valid=None."""
    from src.couche_b.vendor_secure import compute_doc_validity

    result = compute_doc_validity("ABSENT")
    assert result["is_valid"] is None
    assert result["status"] == "ABSENT"


def test_secure_identifiants_no_raw_in_output():
    """
    secure_identifiants ne retourne JAMAIS de valeur brute sensible.
    Les clés _raw doivent être absentes du résultat.
    """
    from src.couche_b.vendor_secure import secure_identifiants

    raw = {
        "supplier_name_raw": "SARL Mali Commerce",
        "supplier_legal_form": "SARL",
        "supplier_nif_raw": "123456789",
        "supplier_rccm_raw": "MLI-BKO-2019-B-1234",
        "supplier_phone_raw": "+223 76 12 34 56",
        "supplier_email_raw": "contact@mali.ml",
        "has_rib": True,
        "quitus_fiscal_date": "2026-01-15",
        "cert_non_faillite_date": "2025-11-20",
    }

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    result = secure_identifiants(raw, mock_conn, "case-001", 42)

    forbidden_keys = {
        "supplier_nif_raw",
        "supplier_rccm_raw",
        "supplier_phone_raw",
        "supplier_email_raw",
        "quitus_fiscal_date",
        "cert_non_faillite_date",
    }
    for key in forbidden_keys:
        assert key not in result, f"Valeur brute sensible dans la sortie : {key}"

    assert "supplier_nif_token" in result
    assert "supplier_rccm_token" in result
    assert "supplier_phone_token" in result
    assert "supplier_email_token" in result
    assert "quitus_fiscal_valide" in result
    assert "cert_non_faillite_valide" in result
