"""
Tests M7.4 · RÈGLE-17
Invariant : trigger quality_score O(1) + pg_trigger_depth guard.
  · HEAD = m7_4_dict_vivant
  · fn_compute_quality_score contient pg_trigger_depth
  · fn_compute_quality_score sans sous-requête
  · quality_score 0-100 (SMALLINT)
"""

from __future__ import annotations

import uuid


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TestM74DictVivant:

    def test_head_alembic_est_m7_4(self, tx):
        """HEAD Alembic = m7_4_dict_vivant."""
        r = tx.execute("SELECT version_num FROM alembic_version").fetchone()
        assert r["version_num"] == "m7_4_dict_vivant"

    def test_fn_compute_quality_score_has_guard(self, tx):
        """RÈGLE-TRG : pg_trigger_depth guard présent."""
        r = tx.execute("""
            SELECT prosrc FROM pg_proc
            WHERE proname = 'fn_compute_quality_score'
              AND pronamespace = (
                SELECT oid FROM pg_namespace WHERE nspname = 'couche_b'
              )
        """).fetchone()
        assert r, "fn_compute_quality_score absente"
        assert "pg_trigger_depth" in r["prosrc"]

    def test_fn_compute_quality_score_o1(self, tx):
        """RÈGLE-QS : zéro sous-requête."""
        r = tx.execute("""
            SELECT prosrc FROM pg_proc
            WHERE proname = 'fn_compute_quality_score'
              AND pronamespace = (
                SELECT oid FROM pg_namespace WHERE nspname = 'couche_b'
              )
        """).fetchone()
        assert r, "fn_compute_quality_score absente"
        assert "dict_price_references" not in r["prosrc"]
        assert "SELECT EXISTS" not in r["prosrc"]

    def test_insert_sets_quality_score_0_100(self, tx):
        """quality_score 0-100 (SMALLINT) sur INSERT."""
        item_id = _uid("_m74_qs")
        tx.execute(
            """
            INSERT INTO couche_b.procurement_dict_items
                (item_id, label_fr, canonical_slug, default_unit, active)
            VALUES (%s, %s, %s, 'unite', TRUE)
            ON CONFLICT (item_id) DO NOTHING
            """,
            (item_id, "Test M7.4 quality", item_id),
        )
        r = tx.execute(
            """
            SELECT quality_score, needs_review
            FROM couche_b.procurement_dict_items
            WHERE item_id = %s
            """,
            (item_id,),
        ).fetchone()
        assert r is not None
        assert 0 <= r["quality_score"] <= 100
        assert isinstance(r["needs_review"], bool)
