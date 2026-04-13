"""100 — ZIP Pass-1 : clés R2 sur process_workspaces

Revision ID: 100_process_workspaces_zip_r2
Revises: 099_fix_admin_roles_seed
Create Date: 2026-04-11

Stockage objet Cloudflare R2 (S3) : l’API enregistre la clé après upload ;
le worker ARQ télécharge le ZIP sans volume filesystem partagé.

Upgrade idempotent (IF NOT EXISTS) : certains tests réinitialisent
``alembic_version`` puis relancent ``upgrade head`` alors que
``process_workspaces`` conserve déjà les colonnes (ex. ``test_migration``).
"""

from __future__ import annotations

from alembic import op

revision = "100_process_workspaces_zip_r2"
down_revision = "099_fix_admin_roles_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE process_workspaces ADD COLUMN IF NOT EXISTS zip_r2_key TEXT"
    )
    op.execute(
        "ALTER TABLE process_workspaces ADD COLUMN IF NOT EXISTS zip_filename TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE process_workspaces DROP COLUMN IF EXISTS zip_filename")
    op.execute("ALTER TABLE process_workspaces DROP COLUMN IF EXISTS zip_r2_key")
