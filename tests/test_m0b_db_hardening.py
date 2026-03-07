"""
Tests M0B — DB Hardening
Fixtures : db_transaction (cursor psycopg dict_row, rollback automatique).
Accès lignes : row["column_name"] (dict_row — pas d'index numérique).
"""

import pytest


def test_fk_pipeline_runs_case_id_not_valid(db_transaction):
    """
    FK pipeline_runs → cases créée avec NOT VALID.
    Contrainte présente dans le schéma.
    Nouvelle insertion avec case_id fantôme = rejet immédiat.
    """
    db_transaction.execute("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.table_constraints
          WHERE constraint_name = 'fk_pipeline_runs_case_id'
            AND table_name = 'pipeline_runs'
        ) AS exists
    """)
    row = db_transaction.fetchone()
    assert row["exists"] is True, "FK fk_pipeline_runs_case_id absente"

    with pytest.raises(Exception):
        db_transaction.execute("""
            INSERT INTO pipeline_runs (case_id)
            VALUES ('00000000-0000-0000-0000-000000000000')
        """)


def test_committee_delegations_created(db_transaction):
    """committee_delegations existe après migration."""
    db_transaction.execute("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_name = 'committee_delegations'
            AND table_schema = 'public'
        ) AS exists
    """)
    row = db_transaction.fetchone()
    assert row["exists"] is True


def test_dict_collision_log_created(db_transaction):
    """dict_collision_log existe après migration."""
    db_transaction.execute("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_name = 'dict_collision_log'
            AND table_schema = 'public'
        ) AS exists
    """)
    row = db_transaction.fetchone()
    assert row["exists"] is True


def test_annotation_registry_created(db_transaction):
    """annotation_registry existe après migration."""
    db_transaction.execute("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_name = 'annotation_registry'
            AND table_schema = 'public'
        ) AS exists
    """)
    row = db_transaction.fetchone()
    assert row["exists"] is True


def test_extraction_jobs_all_async_columns(db_transaction):
    """
    RÈGLE-24 : les 5 colonnes async sont présentes sur extraction_jobs.
    retry_count + max_retries + queued_at préexistants (PROBE).
    next_retry_at + fallback_used ajoutés par 036.
    """
    db_transaction.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'extraction_jobs'
    """)
    rows = db_transaction.fetchall()
    columns = {r["column_name"] for r in rows}
    required = {
        "retry_count",
        "max_retries",
        "next_retry_at",
        "queued_at",
        "fallback_used",
    }
    missing = required - columns
    assert not missing, f"Colonnes manquantes : {missing}"


def test_documents_sha256_column_added(db_transaction):
    """documents.sha256 ajouté nullable par 036."""
    db_transaction.execute("""
        SELECT column_name, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'sha256'
    """)
    row = db_transaction.fetchone()
    assert row is not None, "Colonne documents.sha256 absente"
    assert row["is_nullable"] == "YES", "sha256 devrait être nullable (backfill requis)"


def test_documents_unique_case_sha256_constraint(db_transaction):
    """Contrainte UNIQUE (case_id, sha256) présente sur documents."""
    db_transaction.execute("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.table_constraints
          WHERE constraint_name = 'uq_documents_case_sha256'
            AND table_name = 'documents'
        ) AS exists
    """)
    row = db_transaction.fetchone()
    assert row["exists"] is True, "Contrainte uq_documents_case_sha256 absente"


def test_append_only_trigger_on_dict_collision_log(db_transaction):
    """
    dict_collision_log créée et trigger append-only actif.
    FOR EACH ROW : insert une ligne d'abord, puis DELETE déclenche le trigger.
    """
    db_transaction.execute("""
        INSERT INTO dict_collision_log
          (raw_text_1, raw_text_2, fuzzy_score, category_match, unit_match, resolution)
        VALUES
          ('test_a', 'test_b', 0.85, true, true, 'unresolved')
    """)
    with pytest.raises(Exception, match="append-only"):
        db_transaction.execute(
            "DELETE FROM dict_collision_log WHERE raw_text_1 = 'test_a'"
        )


def test_append_only_conditional_absent_tables(db_transaction):
    """
    Tables absentes (PROBE) → pas de trigger fantôme créé par 036.
    """
    absent_tables = [
        "audit_log",
        "score_history",
        "elimination_log",
        "decision_history",
    ]
    for table in absent_tables:
        db_transaction.execute(f"""
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_name = '{table}' AND table_schema = 'public'
            ) AS exists
        """)
        row = db_transaction.fetchone()
        if row["exists"]:
            pytest.skip(f"{table} présente — trigger actif, hors scope ici")
        db_transaction.execute(f"""
            SELECT EXISTS (
              SELECT 1 FROM information_schema.triggers
              WHERE event_object_table = '{table}'
                AND trigger_name = 'trg_{table}_append_only'
            ) AS exists
        """)
        trigger_row = db_transaction.fetchone()
        assert not trigger_row["exists"], f"Trigger fantôme sur table absente : {table}"


def test_fn_sre_functions_created(db_transaction):
    """Fonctions SRE créées — triggers s'attachent à M16A."""
    functions = [
        "fn_sre_append_only",
        "fn_sre_reject_after_close",
        "fn_sync_registry_on_committee_lock",
    ]
    for fn in functions:
        db_transaction.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'public' AND p.proname = %s
            ) AS exists
        """,
            (fn,),
        )
        row = db_transaction.fetchone()
        assert row["exists"], f"Fonction manquante : {fn}"


def test_indexes_created(db_transaction):
    """Indexes sur tables présentes créés par 036."""
    expected = ["idx_documents_case_id", "idx_extraction_jobs_doc"]
    for idx in expected:
        db_transaction.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM pg_indexes
              WHERE schemaname = 'public' AND indexname = %s
            ) AS exists
        """,
            (idx,),
        )
        row = db_transaction.fetchone()
        assert row["exists"], f"Index manquant : {idx}"


def test_alembic_head_is_current(db_transaction):
    """Head = m7_3b_deprecate_legacy_families (head courante après M7.3b)."""
    db_transaction.execute("SELECT version_num FROM alembic_version")
    row = db_transaction.fetchone()
    assert (
        row["version_num"] == "m7_3b_deprecate_legacy_families"
    ), f"Head attendu : m7_3b_deprecate_legacy_families — réel : {row['version_num']}"
