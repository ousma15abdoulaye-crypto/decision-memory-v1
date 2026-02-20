"""Add M-EXTRACTION-ENGINE columns to documents and create extractions table.

Revision ID: 013_add_m_extraction_engine_documents_columns
Revises: 012_m_extraction_engine
Create Date: 2026-02-19

M-EXTRACTION-ENGINE — Colonnes manquantes pour documents et extractions.
"""
from alembic import op

revision = "013_m_extraction_docs"
down_revision = "012_m_extraction_engine"
branch_labels = None
depends_on = None


def upgrade():
    # ── Réintégrer FKs reportées de 012 (si documents existe) ──
    # Supprimer orphelins avant d'ajouter les FKs
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='documents') THEN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='extraction_errors') THEN
                    DELETE FROM extraction_errors WHERE document_id NOT IN (SELECT id FROM documents);
                    DELETE FROM extraction_errors WHERE job_id IN (SELECT id FROM extraction_jobs WHERE document_id NOT IN (SELECT id FROM documents));
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='extraction_jobs') THEN
                    DELETE FROM extraction_jobs WHERE document_id NOT IN (SELECT id FROM documents);
                    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='extraction_jobs_document_id_fkey' AND table_name='extraction_jobs') THEN
                        ALTER TABLE extraction_jobs ADD CONSTRAINT extraction_jobs_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents(id);
                    END IF;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='extraction_errors')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='extraction_errors_document_id_fkey' AND table_name='extraction_errors') THEN
                    ALTER TABLE extraction_errors ADD CONSTRAINT extraction_errors_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents(id);
                END IF;
            END IF;
        END $$;
    """)

    # ── Ajouter colonnes à documents / extractions (si tables existent) ──
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='documents') THEN
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT;
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_uri TEXT;
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'pending';
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_method TEXT;
                UPDATE documents SET storage_uri = path WHERE storage_uri IS NULL;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='extractions') THEN
                ALTER TABLE extractions ALTER COLUMN artifact_id DROP NOT NULL;
                ALTER TABLE extractions ALTER COLUMN extraction_type DROP NOT NULL;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='extractions' AND column_name='document_id') THEN
                    ALTER TABLE extractions ADD COLUMN document_id TEXT;
                    ALTER TABLE extractions ADD COLUMN raw_text TEXT;
                    ALTER TABLE extractions ADD COLUMN structured_data JSONB;
                    ALTER TABLE extractions ADD COLUMN extraction_method TEXT;
                    ALTER TABLE extractions ADD COLUMN confidence_score REAL;
                    ALTER TABLE extractions ADD COLUMN extracted_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
                CREATE INDEX IF NOT EXISTS idx_extractions_document_id ON extractions(document_id);
            END IF;
        END $$;
    """)


def downgrade():
    # Supprimer FKs reportées de 012
    op.execute("ALTER TABLE extraction_errors DROP CONSTRAINT IF EXISTS extraction_errors_document_id_fkey")
    op.execute("ALTER TABLE extraction_jobs DROP CONSTRAINT IF EXISTS extraction_jobs_document_id_fkey")
    # Supprimer index
    op.execute("DROP INDEX IF EXISTS idx_extractions_document_id")
    # Colonnes ajoutées à extractions
    op.execute("""
        ALTER TABLE extractions
        DROP COLUMN IF EXISTS document_id,
        DROP COLUMN IF EXISTS raw_text,
        DROP COLUMN IF EXISTS structured_data,
        DROP COLUMN IF EXISTS extraction_method,
        DROP COLUMN IF EXISTS confidence_score,
        DROP COLUMN IF EXISTS extracted_at;
    """)
    # Colonnes ajoutées à documents
    op.execute("""
        ALTER TABLE documents
        DROP COLUMN IF EXISTS mime_type,
        DROP COLUMN IF EXISTS storage_uri,
        DROP COLUMN IF EXISTS extraction_status,
        DROP COLUMN IF EXISTS extraction_method;
    """)
    # Restaurer NOT NULL sur artifact_id et extraction_type
    op.execute("""
        ALTER TABLE extractions
        ALTER COLUMN artifact_id SET NOT NULL,
        ALTER COLUMN extraction_type SET NOT NULL
    """)
