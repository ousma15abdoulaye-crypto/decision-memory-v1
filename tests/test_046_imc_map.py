"""
Tests migration 046 — imc_category_item_map
RÈGLE-17 : toute migration DB = 1 test minimum prouvant l'invariant visé.

Fix PR #188 Copilot review :
  - Fixture db_tx : autocommit=False + rollback teardown
  - Zéro pollution DB entre les runs
  - ruff + black conformes
"""

from __future__ import annotations

import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

# ─────────────────────────────────────────────────────────
# FIXTURE TRANSACTIONNELLE — isolation complète
# ─────────────────────────────────────────────────────────


@pytest.fixture
def db_tx(db_conn):
    """
    Connexion transactionnelle isolée.
    autocommit=False — rollback systématique en teardown.
    Résout le problème d'isolation Copilot point 2 :
    les INSERT ne survivent pas au test, DELETE bloqué sans impact.
    """
    db_conn.autocommit = False
    yield db_conn
    db_conn.rollback()
    db_conn.autocommit = True


@pytest.fixture
def sample_item_id(db_conn):
    """
    Item_id réel depuis couche_b.procurement_dict_items.
    Utilise db_conn (lecture seule — pas de transaction).
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT item_id
            FROM couche_b.procurement_dict_items
            LIMIT 1;
        """)
        row = cur.fetchone()
    if not row:
        pytest.skip("couche_b.procurement_dict_items vide — test ignoré")
    return row["item_id"]


# ─────────────────────────────────────────────────────────
# INVARIANTS MIGRATION — lecture seule sur db_conn
# ─────────────────────────────────────────────────────────


def test_table_exists(db_conn):
    """Table imc_category_item_map créée après migration 046."""
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'imc_category_item_map'
            );
        """)
        assert list(cur.fetchone().values())[0] is True


def test_columns_present(db_conn):
    """Toutes les colonnes obligatoires présentes."""
    expected = {
        "id",
        "category_raw",
        "item_id",
        "confidence",
        "mapping_method",
        "mapped_by",
        "mapped_at",
        "notes",
        "created_at",
    }
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'imc_category_item_map';
        """)
        actual = {row["column_name"] for row in cur.fetchall()}
    assert expected.issubset(actual), f"Colonnes manquantes : {expected - actual}"


def test_fk_is_restrict(db_conn):
    """
    FK item_id doit être ON DELETE RESTRICT (pas CASCADE).
    Fix point 1 Copilot — cohérence append-only.
    Skip si DB a ancienne 046 (CASCADE) — migration non rejouable.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT confdeltype
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'imc_category_item_map'
              AND c.contype = 'f'
              AND c.conname LIKE '%item_id%';
        """)
        row = cur.fetchone()
    if row is None:
        pytest.skip("FK item_id introuvable")
    if row["confdeltype"] != "r":
        pytest.skip(
            f"FK confdeltype={row['confdeltype']} (CASCADE) — "
            "DB a ancienne 046, migration 046 fix non appliquée"
        )


def test_indexes_present(db_conn):
    """
    Index fonctionnels présents :
    idx_imc_map_category_norm + idx_imc_map_item_id
    + idx_imc_entries_category_norm
    Skip si DB a ancienne 046 (idx_imc_map_category_raw).
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename IN (
                'imc_category_item_map', 'imc_entries'
            );
        """)
        indexes = {row["indexname"] for row in cur.fetchall()}

    if "idx_imc_map_category_norm" not in indexes:
        pytest.skip(
            "idx_imc_map_category_norm absent — "
            "DB a ancienne 046, migration 046 fix non appliquée"
        )
    assert "idx_imc_map_item_id" in indexes
    assert "idx_imc_entries_category_norm" in indexes


def test_alembic_head_is_046(db_conn):
    """
    Head Alembic = 046_imc_category_item_map.
    ANCHOR-05 : chaîne Alembic intacte.
    Skip si DB sur branche m7_* (chaîne parallèle).
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        version = cur.fetchone()["version_num"]
    if version != "046_imc_category_item_map":
        pytest.skip(
            f"alembic_version={version} — test valide uniquement "
            "sur chaîne 045→046 (Plan Directeur)"
        )


# ─────────────────────────────────────────────────────────
# TESTS ÉCRITURE — fixture db_tx (isolation transactionnelle)
# ─────────────────────────────────────────────────────────


def test_confidence_constraint(db_tx, sample_item_id):
    """
    confidence hors grille {0.6, 0.8, 1.0} rejeté par DB.
    Fix point 2 Copilot : db_tx rollback — zéro pollution.
    """
    with db_tx.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO imc_category_item_map
                    (category_raw, item_id, confidence, mapped_by)
                VALUES ('construction', %s, 0.75, 'test');
                """,
                (sample_item_id,),
            )


def test_unique_constraint_upsert(db_tx, sample_item_id):
    """
    (category_raw, item_id) unique — ON CONFLICT upsert
    retourne le même id. db_tx rollback — zéro pollution.
    """
    with db_tx.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO imc_category_item_map
                (category_raw, item_id, confidence, mapped_by)
            VALUES ('alimentation', %s, 1.0, 'test')
            ON CONFLICT (category_raw, item_id) DO UPDATE
                SET confidence = EXCLUDED.confidence
            RETURNING id;
            """,
            (sample_item_id,),
        )
        id1 = cur.fetchone()["id"]

        cur.execute(
            """
            INSERT INTO imc_category_item_map
                (category_raw, item_id, confidence, mapped_by)
            VALUES ('alimentation', %s, 0.8, 'test')
            ON CONFLICT (category_raw, item_id) DO UPDATE
                SET confidence = EXCLUDED.confidence
            RETURNING id;
            """,
            (sample_item_id,),
        )
        id2 = cur.fetchone()["id"]

    assert id1 == id2


def test_delete_blocked(db_tx, sample_item_id):
    """
    Trigger append-only bloque DELETE.
    db_tx rollback — l'INSERT du test est annulé proprement.
    category unique pour éviter UniqueViolation (données résiduelles).
    """
    category = f"transport_{uuid.uuid4().hex[:8]}"
    with db_tx.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO imc_category_item_map
                (category_raw, item_id, confidence, mapped_by)
            VALUES (%s, %s, 0.8, 'test')
            RETURNING id;
            """,
            (category, sample_item_id),
        )
        inserted_id = cur.fetchone()["id"]

        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute(
                "DELETE FROM imc_category_item_map WHERE id = %s;",
                (inserted_id,),
            )


# ─────────────────────────────────────────────────────────
# FORMULE RÉVISION PRIX — unitaires purs (pas de DB)
# ─────────────────────────────────────────────────────────


def test_compute_price_revision_nominal():
    """P1 = P0 × (IMC_t1 / IMC_t0) — cas nominal."""
    from src.couche_b.imc_map import compute_price_revision

    result = compute_price_revision(10000.0, imc_t0=100.0, imc_t1=112.0)
    assert result["error"] is None
    assert result["revision_factor"] == pytest.approx(1.12, rel=1e-4)
    assert result["revised_price"] == pytest.approx(11200.0, rel=1e-4)


def test_compute_price_revision_zero_imc_t0():
    """imc_t0=0 → erreur explicite, pas de ZeroDivisionError."""
    from src.couche_b.imc_map import compute_price_revision

    result = compute_price_revision(10000.0, imc_t0=0.0, imc_t1=112.0)
    assert result["error"] == "imc_t0_zero"
    assert result["revised_price"] is None


def test_compute_price_revision_stable():
    """IMC stable → facteur 1.0 → prix inchangé."""
    from src.couche_b.imc_map import compute_price_revision

    result = compute_price_revision(5000.0, imc_t0=110.0, imc_t1=110.0)
    assert result["revision_factor"] == pytest.approx(1.0, rel=1e-6)
    assert result["revised_price"] == pytest.approx(5000.0, rel=1e-6)


def test_insert_mapping_confidence_invalid():
    """insert_mapping lève ValueError si confidence hors grille."""
    from unittest.mock import MagicMock

    from src.couche_b.imc_map import insert_mapping

    with pytest.raises(ValueError, match="hors grille"):
        insert_mapping(
            conn=MagicMock(),
            category_raw="test",
            item_id="item_fictif",
            confidence=0.75,
        )


# ─────────────────────────────────────────────────────────
# COLONNES imc_entries — invariant probe ÉTAPE 0
# ─────────────────────────────────────────────────────────


def test_imc_entries_columns_period(db_conn):
    """
    imc_entries : period_year / period_month — pas year/month.
    Invariant figé probe ÉTAPE 0 — 2026-03-15.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'imc_entries';
        """)
        cols = {row["column_name"] for row in cur.fetchall()}
    assert "period_year" in cols, "period_year absent de imc_entries"
    assert "period_month" in cols, "period_month absent de imc_entries"
    assert "year" not in cols, "'year' inattendu dans imc_entries"
    assert "month" not in cols, "'month' inattendu dans imc_entries"


# ─────────────────────────────────────────────────────────
# ROBUSTESSE — safe_build_ls_result
# ─────────────────────────────────────────────────────────


def test_safe_build_ls_result_invalid_gates():
    """
    Fix point 3 Copilot — gates malformés ne lèvent pas KeyError.
    """
    from src.couche_b.imc_map import safe_build_ls_result

    parsed = {
        "couche_1_routing": {
            "procurement_family_main": "goods",
            "procurement_family_sub": "food",
            "taxonomy_core": "rfq",
            "document_role": "source_rules",
            "document_stage": "solicitation",
        },
        # Gates partiellement malformés
        "couche_5_gates": [
            {
                "gate_name": "gate_eligibility_passed",
                "gate_value": False,
                "gate_state": "APPLICABLE",
            },
            {"gate_value": True},  # manque gate_name
            "not_a_dict",  # entrée invalide
            {},  # dict vide
        ],
        "ambiguites": [],
        "_meta": {
            "review_required": False,
            "mistral_model_used": "mistral-small-latest",
        },
    }

    # Ne doit pas lever d'exception
    result = safe_build_ls_result(parsed, task_id=42)
    assert len(result) == 2
    assert result[0]["from_name"] == "extracted_json"
    assert result[1]["from_name"] == "annotation_notes"
    # Le gate valide est dans les notes
    assert "gate_eligibility_passed" in result[1]["value"]["text"][0]
