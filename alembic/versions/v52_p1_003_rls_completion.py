"""v52_p1_003 — Complétion RLS Phase P1.4.

Résout les trois catégories de défauts détectés lors de l'audit P1.4 :

CATÉGORIE 1 — RLS activé mais ZÉRO policy (bug bloquant — accès total refusé)
  - score_history        : policy via workspace_id → process_workspaces.tenant_id
  - evaluation_documents : policy via committee_id → committee_sessions.tenant_id
  - elimination_log      : policy via workspace_id → process_workspaces.tenant_id

CATÉGORIE 2 — RLS activé mais FORCE ROW LEVEL SECURITY manquant (risque sécurité)
  - committee_deliberation_events : tenant_id présent, FORCE ajouté + policy
  - signal_relevance_log          : tenant_id présent, FORCE ajouté + policy
  - user_tenant_roles             : tenant_id présent, FORCE ajouté + policy

CATÉGORIE 3 — Tables canon SANS tenant_id (architecturalement hors scope RLS standard)
  Documentées, NON modifiées dans cette migration (décision architecturale requise) :
  - survey_campaigns  : org_id TEXT, pas de tenant_id → différer P2
  - market_surveys    : zone_id TEXT, pas de tenant_id → différer P2
  - audit_log         : table de chaîne de hachage cross-tenant → RLS non applicable
  - evaluation_criteria : ABSENTE de la base (table renommée ou non créée)

Toutes les opérations sont idempotentes (DO $$ BEGIN ... EXCEPTION WHEN ... END $$).

Revision ID: v52_p1_003_rls_completion
Revises: v52_p1_002_assessment_auto_history
Create Date: 2026-04-09
"""

from alembic import op

revision = "v52_p1_003_rls_completion"
down_revision = "v52_p1_002_assessment_auto_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════════════
    # CATÉGORIE 1 — Ajout des policies manquantes sur tables sans tenant_id
    # Ces tables ont RLS+FORCE déjà actifs mais ZÉRO policy → accès bloqué
    # pour tous. Résolution via sous-requête sur la table mère (tenant_id).
    # ══════════════════════════════════════════════════════════════════════

    # score_history : workspace_id → process_workspaces.tenant_id
    op.execute("""
        DO $$ BEGIN
            CREATE POLICY score_history_tenant_isolation ON score_history
                USING (
                    workspace_id IN (
                        SELECT id FROM process_workspaces
                        WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
                    )
                );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # elimination_log : workspace_id → process_workspaces.tenant_id
    op.execute("""
        DO $$ BEGIN
            CREATE POLICY elimination_log_tenant_isolation ON elimination_log
                USING (
                    workspace_id IN (
                        SELECT id FROM process_workspaces
                        WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
                    )
                );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # evaluation_documents : committee_id → committee_sessions.tenant_id
    op.execute("""
        DO $$ BEGIN
            CREATE POLICY evaluation_documents_tenant_isolation ON evaluation_documents
                USING (
                    committee_id IN (
                        SELECT id FROM committee_sessions
                        WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
                    )
                );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ══════════════════════════════════════════════════════════════════════
    # CATÉGORIE 2 — Ajout de FORCE ROW LEVEL SECURITY + policy sur tables
    # qui ont tenant_id mais auxquelles il manque FORCE (risque bypass pour
    # propriétaires de table / roles SUPERUSER non explicitement exclus).
    # ══════════════════════════════════════════════════════════════════════

    # committee_deliberation_events
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE committee_deliberation_events FORCE ROW LEVEL SECURITY;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE POLICY committee_deliberation_events_tenant_isolation
                ON committee_deliberation_events
                USING (
                    tenant_id = current_setting('app.current_tenant', true)::uuid
                );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # signal_relevance_log
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE signal_relevance_log FORCE ROW LEVEL SECURITY;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE POLICY signal_relevance_log_tenant_isolation
                ON signal_relevance_log
                USING (
                    tenant_id = current_setting('app.current_tenant', true)::uuid
                );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # user_tenant_roles
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE user_tenant_roles FORCE ROW LEVEL SECURITY;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE POLICY user_tenant_roles_tenant_isolation
                ON user_tenant_roles
                USING (
                    tenant_id = current_setting('app.current_tenant', true)::uuid
                );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)


def downgrade() -> None:
    # Catégorie 1 — suppression des policies ajoutées (tables sans tenant_id)
    op.execute(
        "DROP POLICY IF EXISTS score_history_tenant_isolation ON score_history"
    )
    op.execute(
        "DROP POLICY IF EXISTS elimination_log_tenant_isolation ON elimination_log"
    )
    op.execute(
        "DROP POLICY IF EXISTS evaluation_documents_tenant_isolation"
        " ON evaluation_documents"
    )

    # Catégorie 2 — suppression FORCE + policies sur tables avec tenant_id
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE committee_deliberation_events NO FORCE ROW LEVEL SECURITY;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$
    """)
    op.execute(
        "DROP POLICY IF EXISTS committee_deliberation_events_tenant_isolation"
        " ON committee_deliberation_events"
    )

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE signal_relevance_log NO FORCE ROW LEVEL SECURITY;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$
    """)
    op.execute(
        "DROP POLICY IF EXISTS signal_relevance_log_tenant_isolation"
        " ON signal_relevance_log"
    )

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE user_tenant_roles NO FORCE ROW LEVEL SECURITY;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$
    """)
    op.execute(
        "DROP POLICY IF EXISTS user_tenant_roles_tenant_isolation"
        " ON user_tenant_roles"
    )
