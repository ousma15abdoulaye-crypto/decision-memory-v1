"""M-EXTRACTION-CORRECTIONS — table append-only + vues + triggers.

Revision ID: 015_m_extraction_corrections
Revises: 014_ensure_extraction_tables
Create Date: 2026-02-20

ADR-0007 : Corrections humaines append-only, vue structured_data_effective,
           trigger immuabilité extraction_corrections.
"""

from alembic import op

revision = "015_m_extraction_corrections"
down_revision = "014_ensure_extraction_tables"
branch_labels = None
depends_on = None


def upgrade():
    # pgcrypto déjà en 012 — gen_random_uuid() disponible
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── Aligner extraction_errors : error_detail→error_message, requires_human→requires_human_review ──
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='extraction_errors' AND column_name='error_detail') THEN
                ALTER TABLE extraction_errors RENAME COLUMN error_detail TO error_message;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='extraction_errors' AND column_name='requires_human') THEN
                ALTER TABLE extraction_errors RENAME COLUMN requires_human TO requires_human_review;
            END IF;
        END $$;
    """)

    # ── Table extraction_corrections (append-only) ─────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS extraction_corrections (
            id                   VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            extraction_id         TEXT NOT NULL,
            structured_data       JSONB NOT NULL,
            confidence_override   REAL,
            correction_reason     TEXT,
            corrected_by          TEXT NOT NULL,
            corrected_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    # FK extraction_id si extractions existe
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='extractions')
               AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='extraction_corrections_extraction_id_fkey' AND table_name='extraction_corrections') THEN
                ALTER TABLE extraction_corrections
                ADD CONSTRAINT extraction_corrections_extraction_id_fkey
                FOREIGN KEY (extraction_id) REFERENCES extractions(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)
    # Supprimer document_id si présent (alignement safety net)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='extraction_corrections' AND column_name='document_id') THEN
                ALTER TABLE extraction_corrections DROP COLUMN document_id;
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extraction_corrections_extraction_id
        ON extraction_corrections(extraction_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extraction_corrections_corrected_at
        ON extraction_corrections(corrected_at DESC)
    """)

    # ── Trigger append-only extraction_corrections ────────────────────
    # NOTE: chaque statement dans un op.execute() séparé (psycopg3 n'exécute
    # qu'une seule instruction par appel cursor.execute()).
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_extraction_corrections_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'VIOLATION INV-6 [table=extraction_corrections op=%] : append-only. Constitution V3.3.2.',
                TG_OP;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_extraction_corrections_append_only"
        " ON extraction_corrections"
    )

    op.execute("""
        CREATE TRIGGER trg_extraction_corrections_append_only
        BEFORE UPDATE OR DELETE ON extraction_corrections
        FOR EACH ROW EXECUTE FUNCTION enforce_extraction_corrections_append_only()
    """)

    # ── Vue structured_data_effective ─────────────────────────────────
    # extractions est créée en migration 002 — toujours présente ici.
    op.execute("""
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
            SELECT *
            FROM extraction_corrections ec2
            WHERE ec2.extraction_id = e.id
            ORDER BY ec2.corrected_at DESC, ec2.id DESC
            LIMIT 1
        ) ec ON true
        ORDER BY e.document_id, e.extracted_at DESC NULLS LAST, e.id
    """)

    # ── Vue extraction_corrections_history ───────────────────────────
    op.execute("""
        CREATE OR REPLACE VIEW extraction_corrections_history AS
        SELECT *
        FROM extraction_corrections
        ORDER BY corrected_at DESC, id
    """)

    # NOTE (Action 2 — RISQUE CI #2) : Trigger immuabilité extractions NE PAS activer
    # en M-EXTRACTION-CORRECTIONS. A0.5 (grep) ne détecte pas ORM/SQLAlchemy.
    # Ouvrir ticket Phase 4/#15 pour activation après preuve béton.


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_extraction_corrections_corrected_at")
    op.execute("DROP INDEX IF EXISTS idx_extraction_corrections_extraction_id")
    op.execute("DROP VIEW IF EXISTS extraction_corrections_history")
    op.execute("DROP VIEW IF EXISTS structured_data_effective")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_extraction_corrections_append_only"
        " ON extraction_corrections"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_extraction_corrections_append_only()")
    op.execute("DROP TABLE IF EXISTS extraction_corrections")
