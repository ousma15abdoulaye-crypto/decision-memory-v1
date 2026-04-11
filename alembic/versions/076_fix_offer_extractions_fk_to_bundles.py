"""076 - Fix offer_extractions FK to supplier_bundles

Revision ID: 076_fix_offer_extractions_fk_to_bundles
Revises: 075_fix_offer_extractions_artifact_fk
Create Date: 2026-04-10

Le pipeline V5 concatène tous les documents d'un bundle et extrait UNE offre
par bundle (supplier_bundles.id), pas par document.

Migration 075 a pointé vers bundle_documents.id mais c'est incorrect.
On corrige pour pointer vers supplier_bundles.id qui est ce que le code utilise.

Renomme aussi artifact_id -> bundle_id pour clarifier la sémantique.
"""

from __future__ import annotations

from alembic import op

revision = "076_fix_offer_extractions_fk_to_bundles"
down_revision = "075_fix_offer_extractions_artifact_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $body$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'offer_extractions'
            ) THEN
                RETURN;
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'offer_extractions'
                  AND column_name = 'bundle_id'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'offer_extractions_bundle_id_fkey'
                ) THEN
                    ALTER TABLE offer_extractions
                    ADD CONSTRAINT offer_extractions_bundle_id_fkey
                    FOREIGN KEY (bundle_id) REFERENCES supplier_bundles(id)
                    ON DELETE CASCADE;
                END IF;
                RETURN;
            END IF;

            ALTER TABLE offer_extractions
            DROP CONSTRAINT IF EXISTS offer_extractions_artifact_id_fkey;

            ALTER TABLE offer_extractions
            RENAME COLUMN artifact_id TO bundle_id;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'offer_extractions_bundle_id_fkey'
            ) THEN
                ALTER TABLE offer_extractions
                ADD CONSTRAINT offer_extractions_bundle_id_fkey
                FOREIGN KEY (bundle_id) REFERENCES supplier_bundles(id)
                ON DELETE CASCADE;
            END IF;
        END
        $body$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE offer_extractions
        DROP CONSTRAINT IF EXISTS offer_extractions_bundle_id_fkey
    """)

    op.execute("""
        ALTER TABLE offer_extractions
        RENAME COLUMN bundle_id TO artifact_id
    """)

    op.execute("""
        ALTER TABLE offer_extractions
        ADD CONSTRAINT offer_extractions_artifact_id_fkey
        FOREIGN KEY (artifact_id) REFERENCES bundle_documents(id)
        ON DELETE CASCADE
    """)
