from __future__ import annotations

import os
from importlib import util
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import inspect

_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


def _load_migration() -> object:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "002_add_couche_a.py"
    )
    spec = util.spec_from_file_location("migration_002_add_couche_a", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Migration introuvable.")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _restore_schema(engine) -> None:
    """Restaure le schéma complet après un downgrade direct (hors Alembic).

    002.downgrade() bypasse alembic_version et drop documents/offers/extractions/etc
    avec DROP TABLE ... CASCADE. Le CASCADE supprime aussi les vues dépendantes
    (structured_data_effective) et les FK contraintes vers ces tables.
    Les migrations 015+ contiennent des DDL non-idempotents (CREATE TYPE enum)
    qui empêchent un re-run Alembic complet.

    Séquence :
    1. Recréer les tables 002 via upgrade() (CREATE TABLE IF NOT EXISTS)
    2. Stamp alembic_version = 036_db_hardening
    3. Réappliquer les colonnes critiques sur documents et extractions
    4. Recréer la vue structured_data_effective (droppée par CASCADE sur extractions)
    """
    migration_002 = _load_migration()
    migration_002.upgrade(engine)

    with engine.begin() as cx:
        cx.execute(sa.text("DELETE FROM alembic_version"))
        cx.execute(
            sa.text("INSERT INTO alembic_version (version_num) VALUES ('036_db_hardening')")
        )

        # ── documents : colonnes ajoutées par migrations 013 et 036
        for col_sql in [
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_uri TEXT",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'pending'",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_method TEXT",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256 TEXT",
        ]:
            cx.execute(sa.text(col_sql))

        # ── extractions : colonnes ajoutées par migrations 013/014
        # artifact_id et extraction_type deviennent nullable (migration 013)
        for nullable_col in ["artifact_id", "extraction_type"]:
            try:
                cx.execute(sa.text(
                    f"ALTER TABLE extractions ALTER COLUMN {nullable_col} DROP NOT NULL"
                ))
            except Exception:
                pass
        for col_sql in [
            "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS document_id TEXT",
            "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS raw_text TEXT",
            "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS structured_data JSONB",
            "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS extraction_method TEXT",
            "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS confidence_score REAL",
            "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ DEFAULT NOW()",
        ]:
            cx.execute(sa.text(col_sql))

        # ── Vue structured_data_effective
        # Droppée par CASCADE quand extractions a été supprimée — à recréer
        cx.execute(sa.text("""
            CREATE OR REPLACE VIEW structured_data_effective AS
            SELECT DISTINCT ON (e.document_id)
                e.id AS extraction_id,
                e.document_id,
                COALESCE(ec.structured_data, e.structured_data) AS structured_data,
                COALESCE(ec.confidence_override, e.confidence_score) AS confidence_score,
                e.extraction_method,
                e.extracted_at,
                ec.corrected_at,
                ec.corrected_by,
                ec.correction_reason
            FROM extractions e
            LEFT JOIN LATERAL (
                SELECT * FROM extraction_corrections ec2
                WHERE ec2.extraction_id = e.id
                ORDER BY ec2.corrected_at DESC, ec2.id DESC
                LIMIT 1
            ) ec ON true
            ORDER BY e.document_id, e.extracted_at DESC NULLS LAST, e.id
        """))

        # ── Index et contrainte unique de 036
        cx.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id)"
        ))
        cx.execute(sa.text("""
            DO $$ BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'uq_documents_case_sha256'
                  AND table_name = 'documents'
              ) THEN
                ALTER TABLE documents
                  ADD CONSTRAINT uq_documents_case_sha256 UNIQUE (case_id, sha256);
              END IF;
            END $$;
        """))


def test_upgrade_downgrade(db_engine) -> None:
    """Run migration upgrade/downgrade against PostgreSQL."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set – skipping PostgreSQL tests")
    engine = db_engine

    migration = _load_migration()
    try:
        migration.upgrade(engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "cases" in tables
        assert "offers" in tables
        assert "audits" in tables

        migration.downgrade(engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        # La table 'cases' doit être préservée
        assert "cases" in tables
        # Les autres tables de Couche A doivent être supprimées
        assert "offers" not in tables
        assert "audits" not in tables
        assert "lots" not in tables
        assert "documents" not in tables
        assert "extractions" not in tables
        assert "analyses" not in tables
    finally:
        _restore_schema(engine)
