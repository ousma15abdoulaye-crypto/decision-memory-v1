"""
Tests M7.3b · RÈGLE-17
Invariant : family_id bloqué en écriture · lectures OK.
"""

from __future__ import annotations

import psycopg
import pytest


@pytest.fixture
def conn(db_conn):
    """Connexion DB pour tests M7.3b."""
    return db_conn


class TestLegacyFamilyBlock:

    def test_insert_avec_family_id_bloque(self, conn):
        """INSERT avec family_id non null → exception LEGACY."""
        with pytest.raises(psycopg.errors.RaiseException) as exc:
            conn.execute("""
                INSERT INTO couche_b.procurement_dict_items
                    (item_id, label_fr, canonical_slug,
                     active, family_id)
                VALUES
                    ('_test_insert_legacy_block',
                     'Test trigger insert',
                     '_test_insert_legacy_block',
                     TRUE, 'equipements')
                """)
        assert "LEGACY family_id interdit" in str(exc.value)

    def test_insert_sans_family_id_passe(self, conn):
        """INSERT sans family_id → OK."""
        conn.execute("""
            INSERT INTO couche_b.procurement_dict_items
                (item_id, label_fr, canonical_slug, default_unit, active)
            VALUES
                ('_test_insert_no_family',
                 'Test sans family',
                 '_test_insert_no_family',
                 'unite',
                 TRUE)
            ON CONFLICT (item_id) DO NOTHING
            """)
        r = conn.execute("""
            SELECT item_id FROM couche_b.procurement_dict_items
            WHERE item_id = '_test_insert_no_family'
            """).fetchone()
        assert r is not None

    def test_update_family_id_bloque(self, conn):
        """UPDATE family_id vers nouvelle valeur → exception LEGACY."""
        conn.execute("""
            INSERT INTO couche_b.procurement_dict_items
                (item_id, label_fr, canonical_slug, default_unit, active)
            VALUES
                ('_test_update_legacy_block',
                 'Test update legacy',
                 '_test_update_legacy_block',
                 'unite',
                 TRUE)
            ON CONFLICT (item_id) DO NOTHING
            """)
        with pytest.raises(psycopg.errors.RaiseException) as exc:
            conn.execute("""
                UPDATE couche_b.procurement_dict_items
                SET family_id = 'carburants'
                WHERE item_id = '_test_update_legacy_block'
                """)
        assert "LEGACY family_id interdit" in str(exc.value)

    def test_lecture_family_id_autorisee(self, conn):
        """SELECT family_id existant → OK · lectures non bloquées."""
        r = conn.execute("""
            SELECT family_id
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
            LIMIT 1
            """).fetchone()
        assert r is not None

    def test_vue_legacy_lisible(self, conn):
        """Vue legacy_procurement_families accessible · status_note correct."""
        rows = conn.execute("""
            SELECT family_id, status_note
            FROM couche_b.legacy_procurement_families
            LIMIT 1
            """).fetchall()
        assert isinstance(rows, list)
        if rows:
            assert rows[0]["status_note"] == "DEPRECATED_M7.3b_ADR-0016"

    def test_deux_triggers_actifs(self, conn):
        """Deux triggers INSERT + UPDATE actifs · invariant M7.3b."""
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name IN (
                'trg_block_legacy_family_insert',
                'trg_block_legacy_family_update'
              )
            """).fetchone()
        assert r["n"] == 2

    def test_alembic_head(self, conn):
        """HEAD = m7_3b_deprecate_legacy_families."""
        r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        assert r["version_num"] == "m7_3b_deprecate_legacy_families"
