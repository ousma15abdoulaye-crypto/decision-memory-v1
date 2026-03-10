"""
Tests M7.3b · RÈGLE-17
Invariant : family_id READ-ONLY total après migration.
  · INSERT avec family_id → bloqué
  · UPDATE family_id vers valeur → bloqué
  · UPDATE family_id vers NULL → bloqué (D3 corrigé)
  · INSERT sans family_id → autorisé
  · SELECT family_id → autorisé

Isolation : chaque test utilise un item_id unique (uuid suffix).
Pas de pollution inter-runs.
"""

from __future__ import annotations

import uuid

import psycopg
import psycopg.errors
import pytest


def _uid(prefix: str) -> str:
    """item_id unique par run · évite conflits PK."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TestLegacyFamilyBlockM73b:

    def test_head_alembic_est_m7_4a(self, tx):
        """HEAD Alembic DB = head repo courant (dynamique)."""
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
        r = tx.execute("SELECT version_num FROM alembic_version").fetchone()
        assert (
            r["version_num"] == repo_head
        ), f"Head repo={repo_head} — DB={r['version_num']} — désaligné"

    def test_deux_triggers_actifs(self, tx):
        """Deux triggers INSERT + UPDATE présents · invariant M7.3b."""
        r = tx.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name IN (
                'trg_block_legacy_family_insert',
                'trg_block_legacy_family_update'
              )
        """).fetchone()
        assert r["n"] == 2, f"Attendu 2 triggers · trouvé {r['n']}"

    def test_insert_avec_family_id_bloque(self, tx):
        """INSERT avec family_id non null → exception LEGACY."""
        item_id = _uid("_t_ins_blk")
        with pytest.raises(psycopg.errors.RaiseException) as exc:
            tx.execute(
                """
                INSERT INTO couche_b.procurement_dict_items
                    (item_id, label_fr, canonical_slug,
                     default_unit, active, family_id)
                VALUES (%s, %s, %s, 'unite', TRUE, 'equipements')
                """,
                (item_id, "Test insert block", item_id),
            )
        assert "LEGACY family_id interdit" in str(exc.value)

    def test_insert_sans_family_id_autorise(self, tx):
        """INSERT sans family_id → autorisé."""
        item_id = _uid("_t_ins_ok")
        tx.execute(
            """
            INSERT INTO couche_b.procurement_dict_items
                (item_id, label_fr, canonical_slug, default_unit, active)
            VALUES (%s, %s, %s, 'unite', TRUE)
            ON CONFLICT (item_id) DO NOTHING
            """,
            (item_id, "Test insert ok", item_id),
        )
        r = tx.execute(
            """
            SELECT item_id
            FROM couche_b.procurement_dict_items
            WHERE item_id = %s
            """,
            (item_id,),
        ).fetchone()
        assert r is not None

    def test_update_family_id_vers_valeur_bloque(self, tx):
        """UPDATE family_id vers valeur non-null → bloqué."""
        item_id = _uid("_t_upd_blk")
        tx.execute(
            """
            INSERT INTO couche_b.procurement_dict_items
                (item_id, label_fr, canonical_slug, default_unit, active)
            VALUES (%s, %s, %s, 'unite', TRUE)
            ON CONFLICT (item_id) DO NOTHING
            """,
            (item_id, "Test update block", item_id),
        )
        with pytest.raises(psycopg.errors.RaiseException) as exc:
            tx.execute(
                """
                UPDATE couche_b.procurement_dict_items
                SET family_id = 'carburants'
                WHERE item_id = %s
                """,
                (item_id,),
            )
        assert "LEGACY family_id interdit" in str(exc.value)

    def test_update_family_id_vers_null_bloque(self, tx):
        """
        UPDATE family_id vers NULL → bloqué (D3 corrigé).
        Effacement historique interdit · READ-ONLY total.
        Utilise un item existant avec family_id (legacy) · pas d'INSERT.
        """
        r = tx.execute("""
            SELECT item_id FROM couche_b.procurement_dict_items
            WHERE active = TRUE AND family_id IS NOT NULL
            LIMIT 1
            """).fetchone()
        if not r:
            pytest.skip("Aucun item avec family_id (seed manquant)")
        item_id = r["item_id"]
        with pytest.raises(psycopg.errors.RaiseException) as exc:
            tx.execute(
                """
                UPDATE couche_b.procurement_dict_items
                SET family_id = NULL
                WHERE item_id = %s
                """,
                (item_id,),
            )
        assert "LEGACY family_id interdit" in str(exc.value)

    def test_lecture_family_id_autorisee(self, tx):
        """SELECT family_id → autorisé · lectures non bloquées."""
        r = tx.execute("""
            SELECT family_id
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
            LIMIT 1
        """).fetchone()
        assert r is not None

    def test_vue_legacy_lisible_et_correcte(self, tx):
        """Vue legacy_procurement_families lisible · status_note correct."""
        rows = tx.execute("""
            SELECT family_id, status_note
            FROM couche_b.legacy_procurement_families
            LIMIT 1
        """).fetchall()
        assert isinstance(rows, list)
        if rows:
            assert rows[0]["status_note"] == "DEPRECATED_M7.3b_ADR-0016"
