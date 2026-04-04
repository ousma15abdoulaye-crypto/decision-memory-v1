"""076 — Index unique evaluation_documents (workspace_id, version) post-074

Revision ID: 076_evaluation_documents_workspace_unique
Revises: 075_rbac_permissions_roles
Create Date: 2026-04-04

La migration 074 supprime case_id ; l'index uix_evaluation_documents_case_version
disparaît avec la colonne. Rétablit l'invariant « une version par workspace ».

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "076_evaluation_documents_workspace_unique"
down_revision = "075_rbac_permissions_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uix_evaluation_documents_workspace_version
        ON public.evaluation_documents (workspace_id, version);
        """)


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS public.uix_evaluation_documents_workspace_version;"
    )
