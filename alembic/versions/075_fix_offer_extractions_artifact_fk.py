"""075 - Fix offer_extractions FK to bundle_documents

Revision ID: 075_fix_offer_extractions_artifact_fk
Revises: 076_evaluation_documents_workspace_unique
Create Date: 2026-04-10

Le pipeline V5 passe bundle_documents.id comme artifact_id, mais la FK pointe
vers artifacts.id où ces IDs n'existent pas. On corrige:

1. DROP FK offer_extractions.artifact_id -> artifacts.id
2. ALTER artifact_id: TEXT -> UUID
3. ADD FK offer_extractions.artifact_id -> bundle_documents.id

Cette migration suppose que offer_extractions est vide ou contient uniquement
des artifact_id qui existent dans bundle_documents.
"""

from __future__ import annotations

from alembic import op

revision = "075_fix_offer_extractions_artifact_fk"
down_revision = "076_evaluation_documents_workspace_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent : après tests/couche_a/test_migration (002.downgrade + stamp +
    # alembic upgrade head), la table peut déjà être au schéma post-076
    # (colonne bundle_id) alors que alembic_version repart de m4_patch_a_fix.
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
                RETURN;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'offer_extractions'
                  AND column_name = 'artifact_id'
            ) THEN
                RETURN;
            END IF;

            ALTER TABLE offer_extractions
            DROP CONSTRAINT IF EXISTS offer_extractions_artifact_id_fkey;

            ALTER TABLE offer_extractions
            ALTER COLUMN artifact_id TYPE uuid USING artifact_id::uuid;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'offer_extractions_artifact_id_fkey'
            ) THEN
                ALTER TABLE offer_extractions
                ADD CONSTRAINT offer_extractions_artifact_id_fkey
                FOREIGN KEY (artifact_id) REFERENCES bundle_documents(id)
                ON DELETE CASCADE;
            END IF;
        END
        $body$;
    """)


def downgrade() -> None:
    # Retour arrière
    op.execute("""
        ALTER TABLE offer_extractions
        DROP CONSTRAINT IF EXISTS offer_extractions_artifact_id_fkey
    """)

    op.execute("""
        ALTER TABLE offer_extractions
        ALTER COLUMN artifact_id TYPE text
    """)

    op.execute("""
        ALTER TABLE offer_extractions
        ADD CONSTRAINT offer_extractions_artifact_id_fkey
        FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
    """)
