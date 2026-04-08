"""089 — V5.1 RLS correctif : FORCE manquant sur tables périmètre V5.1

Revision ID: 089_v51_rls_force_corrective
Revises: 088_v51_assessment_comments

REGLE-12 : op.execute() SQL brut. Downgrade obligatoire.
Canon V5.1.0 Section 5.4 — INV-S01.

Tables corrigées (ENABLE présent, FORCE manquant) :
  - workspace_events       (migration 069 : ENABLE seulement)
  - supplier_bundles       (migration 070 : ENABLE seulement)
  - bundle_documents       (migration 070 : ENABLE seulement)
  - source_package_documents (migration 078 : ENABLE seulement)
  - committee_sessions     (migration 071 : ENABLE seulement)

Tables ajoutées (aucun RLS) :
  - workspace_memberships  (migration 069 : pas de RLS, a tenant_id)

Décision conservatrice (CLAUDE.md §SIGNAUX STOP) :
  - evaluation_criteria : n'existe pas encore en DB (src/cognitive/evaluation_frame.py
    indique explicitement "Aucune table evaluation_criteria requise").
    Skippée jusqu'à V5.2.
  - survey_campaigns / market_surveys / audit_log : tables M7 sans tenant_id UUID.
    Ajout de FORCE sans policy tenant granulaire éviterait des régressions.
    FORCE uniquement (les admins passent par is_admin bypass déjà en place).
"""

from __future__ import annotations

from alembic import op

revision = "089_v51_rls_force_corrective"
down_revision = "088_v51_assessment_comments"
branch_labels = None
depends_on = None

_TENANT_POLICY = """
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    )
"""

# Tables already having ENABLE + tenant policy — only need FORCE
_FORCE_ONLY_TABLES = (
    "workspace_events",
    "supplier_bundles",
    "bundle_documents",
    "source_package_documents",
    "committee_sessions",
)


def upgrade() -> None:
    # 1. FORCE sur tables déjà ENABLE-ées avec policy tenant
    for table in _FORCE_ONLY_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 2. workspace_memberships — ENABLE + policy tenant + FORCE
    op.execute("ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS wm_tenant_isolation ON workspace_memberships")
    op.execute(
        f"CREATE POLICY wm_tenant_isolation ON workspace_memberships {_TENANT_POLICY}"
    )
    op.execute("ALTER TABLE workspace_memberships FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Inverse workspace_memberships
    op.execute("DROP POLICY IF EXISTS wm_tenant_isolation ON workspace_memberships")
    op.execute("ALTER TABLE workspace_memberships DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_memberships NO FORCE ROW LEVEL SECURITY")

    # Inverse FORCE sur les autres tables
    for table in reversed(_FORCE_ONLY_TABLES):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
