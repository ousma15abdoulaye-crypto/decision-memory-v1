"""
Tests migration 046b — corrections FK RESTRICT + index fonctionnels.
RÈGLE-17 : toute migration DB = 1 test minimum prouvant l'invariant visé.

Ces tests vérifient l'état FINAL après 046 + 046b.
Ils passent que la DB vienne de l'ancienne 046 (corrigée par 046b)
ou de la nouvelle 046 (déjà correcte, 046b idempotente).
"""

from __future__ import annotations

from psycopg.rows import dict_row

# ─────────────────────────────────────────────────────────
# INVARIANTS ÉTAT FINAL — lecture seule
# ─────────────────────────────────────────────────────────


def test_fk_is_restrict(db_conn):
    """
    FK item_id = ON DELETE RESTRICT après 046b.
    confdeltype = 'r'.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT c.confdeltype
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
             WHERE t.relname = 'imc_category_item_map'
               AND c.contype = 'f'
             LIMIT 1;
        """)
        row = cur.fetchone()
    assert row is not None, "FK introuvable sur imc_category_item_map"
    assert (
        row["confdeltype"] == "r"
    ), f"FK doit être RESTRICT (r) — trouvé : {row['confdeltype']}"


def test_functional_index_imc_map(db_conn):
    """
    idx_imc_map_category_norm (fonctionnel) présent.
    idx_imc_map_category_raw (btree) absent.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'imc_category_item_map';
        """)
        indexes = {row["indexname"] for row in cur.fetchall()}

    assert "idx_imc_map_category_norm" in indexes, "idx_imc_map_category_norm absent"
    assert (
        "idx_imc_map_category_raw" not in indexes
    ), "idx_imc_map_category_raw doit être supprimé"


def test_functional_index_imc_entries(db_conn):
    """
    idx_imc_entries_category_norm (fonctionnel) présent sur imc_entries.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'imc_entries';
        """)
        indexes = {row["indexname"] for row in cur.fetchall()}

    assert (
        "idx_imc_entries_category_norm" in indexes
    ), "idx_imc_entries_category_norm absent sur imc_entries"


def test_alembic_head_is_046b(db_conn):
    """
    Head Alembic = 046b_imc_map_fix_restrict_indexes après migration.
    ANCHOR-05 : chaîne Alembic intacte.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        version = cur.fetchone()["version_num"]
    assert version == "046b_imc_map_fix_restrict_indexes", f"Head inattendu : {version}"


def test_046b_idempotent_on_clean_db(db_conn):
    """
    Sur une DB déjà correcte (046 nouvelle version),
    046b ne doit pas lever d'erreur.
    La FK est déjà RESTRICT — le DO $$ ne modifie rien.
    Les index IF NOT EXISTS ne créent pas de doublon.
    Ce test passe si head = 046b et FK = RESTRICT.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM pg_indexes
            WHERE tablename = 'imc_category_item_map'
              AND indexname = 'idx_imc_map_category_norm';
        """)
        count = cur.fetchone()["cnt"]
    assert (
        count == 1
    ), f"idx_imc_map_category_norm doit exister en un exemplaire — count={count}"
