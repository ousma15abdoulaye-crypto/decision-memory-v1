"""Add columns required by Couche A services (PHASE 1B).

Revision ID: 047_couche_a_service_columns
Revises: 046b_imc_map_fix_restrict_indexes
Create Date: 2026-03-11

Adds columns used by analysis, cba, pv, extraction services after ORM→psycopg migration.
All ADD COLUMN IF NOT EXISTS for idempotency.
"""
from alembic import op

revision = "047_couche_a_service_columns"
down_revision = "046b_imc_map_fix_restrict_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='offers') THEN
                ALTER TABLE offers ADD COLUMN IF NOT EXISTS lot_id TEXT;
                ALTER TABLE offers ADD COLUMN IF NOT EXISTS amount REAL;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='documents') THEN
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS lot_id TEXT;
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type TEXT;
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path TEXT;
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata_json TEXT;
                UPDATE documents SET storage_path = path WHERE storage_path IS NULL AND path IS NOT NULL;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='extractions') THEN
                ALTER TABLE extractions ADD COLUMN IF NOT EXISTS offer_id TEXT;
                ALTER TABLE extractions ADD COLUMN IF NOT EXISTS document_id TEXT;
                ALTER TABLE extractions ADD COLUMN IF NOT EXISTS extracted_json TEXT;
                ALTER TABLE extractions ADD COLUMN IF NOT EXISTS missing_json TEXT;
                ALTER TABLE extractions ADD COLUMN IF NOT EXISTS used_llm BOOLEAN DEFAULT FALSE;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='analyses') THEN
                ALTER TABLE analyses ADD COLUMN IF NOT EXISTS offer_id TEXT;
                ALTER TABLE analyses ADD COLUMN IF NOT EXISTS status TEXT;
                ALTER TABLE analyses ADD COLUMN IF NOT EXISTS essentials_score REAL;
                ALTER TABLE analyses ADD COLUMN IF NOT EXISTS capacity_score REAL;
                ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sustainability_score REAL;
                ALTER TABLE analyses ADD COLUMN IF NOT EXISTS commercial_score REAL;
                ALTER TABLE analyses ADD COLUMN IF NOT EXISTS total_score REAL;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='audits') THEN
                ALTER TABLE audits ADD COLUMN IF NOT EXISTS entity_type TEXT;
                ALTER TABLE audits ADD COLUMN IF NOT EXISTS entity_id TEXT;
                ALTER TABLE audits ADD COLUMN IF NOT EXISTS actor TEXT;
                ALTER TABLE audits ADD COLUMN IF NOT EXISTS details_json TEXT;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='lots') THEN
                ALTER TABLE lots ADD COLUMN IF NOT EXISTS name TEXT;
            END IF;
        END $$;
    """)
    # Backfill lots.name from lot_number if empty
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lots' AND column_name='name')
               AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lots' AND column_name='lot_number') THEN
                UPDATE lots SET name = lot_number WHERE name IS NULL AND lot_number IS NOT NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='offers') THEN
                ALTER TABLE offers DROP COLUMN IF EXISTS lot_id;
                ALTER TABLE offers DROP COLUMN IF EXISTS amount;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='documents') THEN
                ALTER TABLE documents DROP COLUMN IF EXISTS lot_id;
                ALTER TABLE documents DROP COLUMN IF EXISTS document_type;
                ALTER TABLE documents DROP COLUMN IF EXISTS storage_path;
                ALTER TABLE documents DROP COLUMN IF EXISTS metadata_json;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='extractions') THEN
                ALTER TABLE extractions DROP COLUMN IF EXISTS offer_id;
                ALTER TABLE extractions DROP COLUMN IF EXISTS document_id;
                ALTER TABLE extractions DROP COLUMN IF EXISTS extracted_json;
                ALTER TABLE extractions DROP COLUMN IF EXISTS missing_json;
                ALTER TABLE extractions DROP COLUMN IF EXISTS used_llm;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='analyses') THEN
                ALTER TABLE analyses DROP COLUMN IF EXISTS offer_id;
                ALTER TABLE analyses DROP COLUMN IF EXISTS status;
                ALTER TABLE analyses DROP COLUMN IF EXISTS essentials_score;
                ALTER TABLE analyses DROP COLUMN IF EXISTS capacity_score;
                ALTER TABLE analyses DROP COLUMN IF EXISTS sustainability_score;
                ALTER TABLE analyses DROP COLUMN IF EXISTS commercial_score;
                ALTER TABLE analyses DROP COLUMN IF EXISTS total_score;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='audits') THEN
                ALTER TABLE audits DROP COLUMN IF EXISTS entity_type;
                ALTER TABLE audits DROP COLUMN IF EXISTS entity_id;
                ALTER TABLE audits DROP COLUMN IF EXISTS actor;
                ALTER TABLE audits DROP COLUMN IF EXISTS details_json;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='lots') THEN
                ALTER TABLE lots DROP COLUMN IF EXISTS name;
            END IF;
        END $$;
    """)
