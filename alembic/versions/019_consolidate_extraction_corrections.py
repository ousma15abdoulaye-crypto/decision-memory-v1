# -*- coding: utf-8 -*-
"""Consolidation finale M-EXTRACTION-CORRECTIONS.

Revision ID: 019_consolidate_extraction_corrections
Revises: 016_fix_015_views_triggers
Create Date: 2026-02-21

Objectif : migration de consolidation idempotente.
  - Garantit que la table extraction_corrections existe avec le bon schema
  - Garantit que les triggers append-only existent physiquement en DB
  - Garantit que les vues structured_data_effective et
    extraction_corrections_history existent
  - Supprime la colonne fantome document_id si presente

ADR-0006 : append-only global, views current_, triggers DB-level.
Constitution V3.3.2 : INV-6 (immutabilite), INV-9 (fidelite au reel).

Note : 018_fix_alembic_heads etait une migration vide avec down_revision
incorrect — remplacee par cette migration de consolidation.
"""
from __future__ import annotations

from alembic import op


revision = "019_consolidate_ec"
down_revision = "016_fix_015_views_triggers"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # 1. Extension pgcrypto
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 2. Table extraction_corrections
    op.execute("""
        CREATE TABLE IF NOT EXISTS extraction_corrections (
            id                  VARCHAR PRIMARY KEY
                                    DEFAULT gen_random_uuid()::text,
            extraction_id       TEXT        NOT NULL,
            structured_data     JSONB       NOT NULL,
            confidence_override REAL,
            correction_reason   TEXT,
            corrected_by        TEXT        NOT NULL,
            corrected_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # 3. Supprimer colonne fantome document_id si elle existe
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE  table_schema = 'public'
                AND    table_name   = 'extraction_corrections'
                AND    column_name  = 'document_id'
            ) THEN
                ALTER TABLE extraction_corrections DROP COLUMN document_id;
            END IF;
        END $$;
    """)

    # 4. Contrainte FK vers extractions si la table existe
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE  table_schema = 'public'
                AND    table_name   = 'extractions'
            )
            AND NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE  constraint_name = 'extraction_corrections_extraction_id_fkey'
                AND    table_name      = 'extraction_corrections'
            ) THEN
                ALTER TABLE extraction_corrections
                    ADD CONSTRAINT extraction_corrections_extraction_id_fkey
                    FOREIGN KEY (extraction_id)
                    REFERENCES extractions(id)
                    ON DELETE CASCADE;
            END IF;
        END $$;
    """)

    # 5. Index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extraction_corrections_extraction_id
        ON extraction_corrections(extraction_id);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extraction_corrections_corrected_at
        ON extraction_corrections(corrected_at DESC);
    """)

    # 6. Fonction trigger append-only
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_extraction_corrections_append_only()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION
                'VIOLATION INV-6 [table=extraction_corrections op=%] : append-only. Constitution V3.3.2.',
                TG_OP;
        END;
        $$;
    """)

    # 7. Trigger UPDATE
    op.execute("""
        DROP TRIGGER IF EXISTS trg_extraction_corrections_no_update
        ON extraction_corrections;
    """)

    op.execute("""
        CREATE TRIGGER trg_extraction_corrections_no_update
        BEFORE UPDATE ON extraction_corrections
        FOR EACH ROW
        EXECUTE FUNCTION enforce_extraction_corrections_append_only();
    """)

    # 8. Trigger DELETE
    op.execute("""
        DROP TRIGGER IF EXISTS trg_extraction_corrections_no_delete
        ON extraction_corrections;
    """)

    op.execute("""
        CREATE TRIGGER trg_extraction_corrections_no_delete
        BEFORE DELETE ON extraction_corrections
        FOR EACH ROW
        EXECUTE FUNCTION enforce_extraction_corrections_append_only();
    """)

    # 9. Vue structured_data_effective
    op.execute("DROP VIEW IF EXISTS structured_data_effective;")

    op.execute("""
        CREATE VIEW structured_data_effective AS
        SELECT DISTINCT ON (e.document_id)
            e.id                                                    AS extraction_id,
            e.document_id,
            COALESCE(ec.structured_data,     e.structured_data)    AS structured_data,
            COALESCE(ec.confidence_override, e.confidence_score)   AS confidence_score,
            e.extraction_method,
            e.extracted_at,
            ec.corrected_at,
            ec.corrected_by,
            ec.correction_reason
        FROM extractions e
        LEFT JOIN LATERAL (
            SELECT *
            FROM   extraction_corrections ec2
            WHERE  ec2.extraction_id = e.id
            ORDER  BY ec2.corrected_at DESC, ec2.id DESC
            LIMIT  1
        ) ec ON true
        ORDER BY e.document_id, e.extracted_at DESC NULLS LAST, e.id;
    """)

    # 10. Vue extraction_corrections_history
    op.execute("DROP VIEW IF EXISTS extraction_corrections_history;")

    op.execute("""
        CREATE VIEW extraction_corrections_history AS
        SELECT
            id,
            extraction_id,
            structured_data,
            confidence_override,
            correction_reason,
            corrected_by,
            corrected_at
        FROM extraction_corrections
        ORDER BY corrected_at DESC, id;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS extraction_corrections_history;")
    op.execute("DROP VIEW IF EXISTS structured_data_effective;")
    op.execute("""
        DROP TRIGGER IF EXISTS trg_extraction_corrections_no_delete
        ON extraction_corrections;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_extraction_corrections_no_update
        ON extraction_corrections;
    """)
    op.execute(
        "DROP FUNCTION IF EXISTS enforce_extraction_corrections_append_only();"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_extraction_corrections_corrected_at;"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_extraction_corrections_extraction_id;"
    )
    op.execute("DROP TABLE IF EXISTS extraction_corrections;")
