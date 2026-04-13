"""100 — ZIP Pass-1 : clés R2 sur process_workspaces

Revision ID: 100_process_workspaces_zip_r2
Revises: 099_fix_admin_roles_seed
Create Date: 2026-04-11

Stockage objet Cloudflare R2 (S3) : l’API enregistre la clé après upload ;
le worker ARQ télécharge le ZIP sans volume filesystem partagé.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "100_process_workspaces_zip_r2"
down_revision = "099_fix_admin_roles_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "process_workspaces",
        sa.Column("zip_r2_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "process_workspaces",
        sa.Column("zip_filename", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("process_workspaces", "zip_filename")
    op.drop_column("process_workspaces", "zip_r2_key")
