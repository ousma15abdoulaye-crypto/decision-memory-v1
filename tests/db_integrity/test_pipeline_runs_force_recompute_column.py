"""L5 — pipeline_runs.force_recompute colonne DB (INV-P18).

Vérifie que la migration 034_pipeline_force_recompute a bien ajouté :
  - colonne force_recompute BOOLEAN NOT NULL DEFAULT FALSE
  - index idx_pipeline_runs_force_recompute
  - commentaire sur la colonne

Pattern : db_conn (autocommit=True, conftest racine).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _column_info(db_conn, table: str, column: str) -> dict | None:
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = %s
              AND column_name  = %s
            """,
            (table, column),
        )
        return cur.fetchone()


def _index_exists(db_conn, index_name: str) -> bool:
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=%s",
            (index_name,),
        )
        return cur.fetchone() is not None


def _column_comment(db_conn, table: str, column: str) -> str | None:
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pg_catalog.col_description(
                (SELECT oid FROM pg_class WHERE relname=%s AND relnamespace='public'::regnamespace),
                (SELECT attnum FROM pg_attribute
                 WHERE attrelid=(SELECT oid FROM pg_class
                                 WHERE relname=%s AND relnamespace='public'::regnamespace)
                   AND attname=%s)
            ) AS comment
            """,
            (table, table, column),
        )
        row = cur.fetchone()
        return row["comment"] if row else None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_force_recompute_column_exists(db_conn):
    """INV-P18 : colonne force_recompute présente dans pipeline_runs."""
    info = _column_info(db_conn, "pipeline_runs", "force_recompute")
    assert info is not None, (
        "Colonne pipeline_runs.force_recompute absente — "
        "migration 034_pipeline_force_recompute non appliquée"
    )


def test_force_recompute_type_boolean(db_conn):
    """pipeline_runs.force_recompute doit être BOOLEAN."""
    info = _column_info(db_conn, "pipeline_runs", "force_recompute")
    assert info is not None
    assert (
        info["data_type"] == "boolean"
    ), f"Type attendu 'boolean', obtenu {info['data_type']!r}"


def test_force_recompute_not_nullable(db_conn):
    """pipeline_runs.force_recompute doit être NOT NULL."""
    info = _column_info(db_conn, "pipeline_runs", "force_recompute")
    assert info is not None
    assert info["is_nullable"] == "NO", "force_recompute doit être NOT NULL (INV-P18)"


def test_force_recompute_default_false(db_conn):
    """pipeline_runs.force_recompute doit avoir DEFAULT FALSE."""
    info = _column_info(db_conn, "pipeline_runs", "force_recompute")
    assert info is not None
    default = (info["column_default"] or "").lower()
    assert (
        "false" in default
    ), f"DEFAULT FALSE attendu, obtenu {info['column_default']!r}"


def test_force_recompute_index_exists(db_conn):
    """Index idx_pipeline_runs_force_recompute doit exister."""
    assert _index_exists(
        db_conn, "idx_pipeline_runs_force_recompute"
    ), "Index idx_pipeline_runs_force_recompute absent"


def test_force_recompute_comment_present(db_conn):
    """Commentaire ADR-0013 présent sur force_recompute."""
    comment = _column_comment(db_conn, "pipeline_runs", "force_recompute")
    assert (
        comment is not None and len(comment) > 10
    ), "Commentaire manquant sur pipeline_runs.force_recompute"
    assert (
        "ADR-0013" in comment
    ), f"Commentaire doit mentionner ADR-0013 — obtenu : {comment!r}"
