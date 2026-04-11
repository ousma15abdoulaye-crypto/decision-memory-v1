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
    # 1. DROP la FK vers artifacts
    op.execute("""
        ALTER TABLE offer_extractions
        DROP CONSTRAINT IF EXISTS offer_extractions_artifact_id_fkey
    """)

    # 2. Changer artifact_id de TEXT à UUID
    # Si la table contient des données, on doit d'abord caster
    op.execute("""
        ALTER TABLE offer_extractions
        ALTER COLUMN artifact_id TYPE uuid USING artifact_id::uuid
    """)

    # 3. Ajouter FK vers bundle_documents
    op.execute("""
        ALTER TABLE offer_extractions
        ADD CONSTRAINT offer_extractions_artifact_id_fkey
        FOREIGN KEY (artifact_id) REFERENCES bundle_documents(id)
        ON DELETE CASCADE
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
