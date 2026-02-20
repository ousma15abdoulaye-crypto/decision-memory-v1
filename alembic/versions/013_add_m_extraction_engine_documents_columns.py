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
    # ── Ajouter colonnes à documents ──────────────────────────────────
    op.execute("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS mime_type TEXT,
        ADD COLUMN IF NOT EXISTS storage_uri TEXT,
        ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'pending',
        ADD COLUMN IF NOT EXISTS extraction_method TEXT;
    """)
    
    # Mettre à jour storage_uri depuis path si NULL
    op.execute("""
        UPDATE documents
        SET storage_uri = path
        WHERE storage_uri IS NULL;
    """)
    
    # ── Créer table extractions pour M-EXTRACTION-ENGINE ──────────────
    # Rendre colonnes existantes nullable pour M-EXTRACTION-ENGINE
    op.execute("""
        ALTER TABLE extractions
        ALTER COLUMN artifact_id DROP NOT NULL,
        ALTER COLUMN extraction_type DROP NOT NULL;
    """)
    
    # Ajouter les colonnes manquantes à la table existante
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'extractions'
                AND column_name = 'document_id'
            ) THEN
                ALTER TABLE extractions
                ADD COLUMN document_id TEXT REFERENCES documents(id),
                ADD COLUMN raw_text TEXT,
                ADD COLUMN structured_data JSONB,
                ADD COLUMN extraction_method TEXT,
                ADD COLUMN confidence_score REAL,
                ADD COLUMN extracted_at TIMESTAMPTZ DEFAULT NOW();
            END IF;
        END $$;
    """)
    
    # Créer index sur document_id
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extractions_document_id
        ON extractions(document_id);
    """)


def downgrade():
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
