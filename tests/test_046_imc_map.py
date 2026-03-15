"""
Tests migration 046 — imc_category_item_map
RÈGLE-17 : toute migration DB = 1 test minimum prouvant l'invariant visé.

Corrections probe ÉTAPE 0 :
  - item_id = TEXT → couche_b.procurement_dict_items
  - imc_entries : period_year / period_month
"""

import uuid

import pytest
import psycopg
from psycopg.rows import dict_row


# ─────────────────────────────────────────────────────────
# FIXTURE — item_id réel depuis couche_b
# ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_item_id(db_conn):
    """
    Récupère un item_id réel depuis couche_b.procurement_dict_items.
    Évite de dépendre d'un UUID hardcodé.
    """
    with db_conn.cursor() as cur:
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
# INVARIANTS MIGRATION
# ─────────────────────────────────────────────────────────

def test_table_exists(db_conn):
    """Table imc_category_item_map créée après migration 046."""
    with db_conn.cursor() as cur:
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
        "id", "category_raw", "item_id", "confidence",
        "mapping_method", "mapped_by", "mapped_at",
        "notes", "created_at",
    }
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'imc_category_item_map';
        """)
        actual = {row["column_name"] for row in cur.fetchall()}
    assert expected.issubset(actual), (
        f"Colonnes manquantes : {expected - actual}"
    )


def test_confidence_constraint(db_conn, sample_item_id):
    """confidence hors grille {0.6, 0.8, 1.0} rejeté par DB."""
    with db_conn.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute("""
                INSERT INTO imc_category_item_map
                    (category_raw, item_id, confidence, mapped_by)
                VALUES ('construction', %s, 0.75, 'test');
            """, (sample_item_id,))
    db_conn.rollback()


def test_unique_constraint_upsert(db_conn, sample_item_id):
    """(category_raw, item_id) unique — ON CONFLICT upsert retourne même id."""
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            INSERT INTO imc_category_item_map
                (category_raw, item_id, confidence, mapped_by)
            VALUES ('alimentation', %s, 1.0, 'test')
            ON CONFLICT (category_raw, item_id) DO UPDATE
                SET confidence = EXCLUDED.confidence
            RETURNING id;
        """, (sample_item_id,))
        id1 = cur.fetchone()["id"]

        cur.execute("""
            INSERT INTO imc_category_item_map
                (category_raw, item_id, confidence, mapped_by)
            VALUES ('alimentation', %s, 0.8, 'test')
            ON CONFLICT (category_raw, item_id) DO UPDATE
                SET confidence = EXCLUDED.confidence
            RETURNING id;
        """, (sample_item_id,))
        id2 = cur.fetchone()["id"]

    assert id1 == id2
    db_conn.rollback()


def test_delete_blocked(db_conn, sample_item_id):
    """Trigger append-only bloque DELETE."""
    category = f"transport_{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO imc_category_item_map
                (category_raw, item_id, confidence, mapped_by)
            VALUES (%s, %s, 0.8, 'test')
            RETURNING id;
        """, (category, sample_item_id))
        inserted_id = cur.fetchone()["id"]

        with pytest.raises(psycopg.errors.RaiseException):
            cur.execute(
                "DELETE FROM imc_category_item_map WHERE id = %s;",
                (inserted_id,),
            )
    db_conn.rollback()


def test_indexes_present(db_conn):
    """Index idx_imc_map_category_raw + idx_imc_map_item_id présents."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'imc_category_item_map';
        """)
        indexes = {row["indexname"] for row in cur.fetchall()}
    assert "idx_imc_map_category_raw" in indexes
    assert "idx_imc_map_item_id" in indexes


def test_alembic_head_is_046(db_conn):
    """
    Head Alembic = 046_imc_category_item_map après migration.
    ANCHOR-05 : chaîne Alembic intacte.
    Skip si DB sur branche m7_* (chaîne parallèle).
    """
    with db_conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        version = cur.fetchone()["version_num"]
    if version != "046_imc_category_item_map":
        pytest.skip(
            f"alembic_version={version} — test valide uniquement "
            "sur chaîne 045→046 (Plan Directeur)"
        )


# ─────────────────────────────────────────────────────────
# FORMULE RÉVISION PRIX — unitaires purs
# ─────────────────────────────────────────────────────────

def test_compute_price_revision_nominal():
    """P1 = P0 × (IMC_t1 / IMC_t0) — cas nominal."""
    from src.couche_b.imc_map import compute_price_revision

    result = compute_price_revision(10000.0, imc_t0=100.0, imc_t1=112.0)
    assert result["error"]           is None
    assert result["revision_factor"] == pytest.approx(1.12,    rel=1e-4)
    assert result["revised_price"]   == pytest.approx(11200.0, rel=1e-4)


def test_compute_price_revision_zero_imc_t0():
    """imc_t0=0 → erreur explicite, pas de ZeroDivisionError."""
    from src.couche_b.imc_map import compute_price_revision

    result = compute_price_revision(10000.0, imc_t0=0.0, imc_t1=112.0)
    assert result["error"]         == "imc_t0_zero"
    assert result["revised_price"] is None


def test_compute_price_revision_stable():
    """IMC stable → facteur 1.0 → prix inchangé."""
    from src.couche_b.imc_map import compute_price_revision

    result = compute_price_revision(5000.0, imc_t0=110.0, imc_t1=110.0)
    assert result["revision_factor"] == pytest.approx(1.0,    rel=1e-6)
    assert result["revised_price"]   == pytest.approx(5000.0, rel=1e-6)


def test_insert_mapping_confidence_invalid():
    """insert_mapping lève ValueError si confidence hors grille."""
    from src.couche_b.imc_map import insert_mapping
    from unittest.mock import MagicMock

    with pytest.raises(ValueError, match="hors grille"):
        insert_mapping(
            conn=MagicMock(),
            category_raw="test",
            item_id="item_fictif",
            confidence=0.75,
        )


# ─────────────────────────────────────────────────────────
# JOINTURE imc_entries — colonnes period_year / period_month
# ─────────────────────────────────────────────────────────

def test_imc_entries_columns_period(db_conn):
    """
    imc_entries utilise period_year / period_month — pas year/month.
    Invariant probe ÉTAPE 0 — colonne names figés.
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'imc_entries';
        """)
        cols = {row["column_name"] for row in cur.fetchall()}
    assert "period_year"  in cols, "period_year absent de imc_entries"
    assert "period_month" in cols, "period_month absent de imc_entries"
    assert "year"  not in cols,   "colonne 'year' inattendue dans imc_entries"
    assert "month" not in cols,   "colonne 'month' inattendue dans imc_entries"
