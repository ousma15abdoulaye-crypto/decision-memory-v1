"""094 — tenant_id UUID + RLS FORCE sur marché, mercuriale, offres, extractions, analyses.

Mandat sécurité multi-tenant : tables précédemment sans isolation par tenant.

Tables :
  - survey_campaigns, survey_campaign_items, survey_campaign_zones
  - market_surveys, price_anomaly_alerts
  - mercuriale_sources, mercurials
  - market_signals_v2
  - offers, extractions, analysis_summaries

Politique : tenant_id = current_setting('app.current_tenant', true)::uuid
           OR COALESCE(current_setting('app.is_admin', true), '') = 'true'

Backfill : priorité au tenant ``sci_mali`` si présent ; sinon premier tenant par ordre de ``code``.

Revision ID: 094_security_market_mercurial_tenant_rls
Revises: 6ce2036bd346
"""

from __future__ import annotations

from alembic import op

revision = "094_security_market_mercurial_tenant_rls"
down_revision = "6ce2036bd346"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $body$
        DECLARE
            v_default uuid;
        BEGIN
            SELECT id INTO v_default FROM public.tenants WHERE code = 'sci_mali' LIMIT 1;
            IF v_default IS NULL THEN
                SELECT id INTO v_default FROM public.tenants ORDER BY code LIMIT 1;
            END IF;
            IF v_default IS NULL THEN
                RAISE EXCEPTION '094_security: aucune ligne dans public.tenants — impossible de backfiller tenant_id';
            END IF;

            -- survey_campaigns
            ALTER TABLE public.survey_campaigns
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.survey_campaigns SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.survey_campaigns ALTER COLUMN tenant_id SET NOT NULL;

            -- survey_campaign_items / zones : même tenant que la campagne
            ALTER TABLE public.survey_campaign_items
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.survey_campaign_items sci
            SET tenant_id = sc.tenant_id
            FROM public.survey_campaigns sc
            WHERE sci.campaign_id = sc.id AND sci.tenant_id IS NULL;
            UPDATE public.survey_campaign_items SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.survey_campaign_items ALTER COLUMN tenant_id SET NOT NULL;

            ALTER TABLE public.survey_campaign_zones
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.survey_campaign_zones scz
            SET tenant_id = sc.tenant_id
            FROM public.survey_campaigns sc
            WHERE scz.campaign_id = sc.id AND scz.tenant_id IS NULL;
            UPDATE public.survey_campaign_zones SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.survey_campaign_zones ALTER COLUMN tenant_id SET NOT NULL;

            -- market_surveys
            ALTER TABLE public.market_surveys
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.market_surveys ms
            SET tenant_id = pw.tenant_id
            FROM public.process_workspaces pw
            WHERE ms.workspace_id = pw.id AND ms.tenant_id IS NULL;
            UPDATE public.market_surveys SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.market_surveys ALTER COLUMN tenant_id SET NOT NULL;

            -- price_anomaly_alerts
            ALTER TABLE public.price_anomaly_alerts
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.price_anomaly_alerts SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.price_anomaly_alerts ALTER COLUMN tenant_id SET NOT NULL;

            -- mercuriale_sources + mercurials (prix de référence — assignation tenant par défaut)
            ALTER TABLE public.mercuriale_sources
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.mercuriale_sources SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.mercuriale_sources ALTER COLUMN tenant_id SET NOT NULL;

            ALTER TABLE public.mercurials
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.mercurials m
            SET tenant_id = ms.tenant_id
            FROM public.mercuriale_sources ms
            WHERE m.source_id = ms.id AND m.tenant_id IS NULL;
            UPDATE public.mercurials SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.mercurials ALTER COLUMN tenant_id SET NOT NULL;

            -- market_signals_v2
            ALTER TABLE public.market_signals_v2
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.market_signals_v2 SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.market_signals_v2 ALTER COLUMN tenant_id SET NOT NULL;

            -- offers / extractions / analysis_summaries
            -- NB : cases.tenant_id est historiquement TEXT (souvent != tenants.code) ;
            -- backfill conservateur = tenant par défaut. Affiner par mandat données (carto case→tenant UUID).
            ALTER TABLE public.offers
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.offers SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.offers ALTER COLUMN tenant_id SET NOT NULL;

            ALTER TABLE public.extractions
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.extractions SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.extractions ALTER COLUMN tenant_id SET NOT NULL;

            ALTER TABLE public.analysis_summaries
                ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
            UPDATE public.analysis_summaries SET tenant_id = v_default WHERE tenant_id IS NULL;
            ALTER TABLE public.analysis_summaries ALTER COLUMN tenant_id SET NOT NULL;
        END
        $body$;
    """)

    _tables = (
        "survey_campaigns",
        "survey_campaign_items",
        "survey_campaign_zones",
        "market_surveys",
        "price_anomaly_alerts",
        "mercuriale_sources",
        "mercurials",
        "market_signals_v2",
        "offers",
        "extractions",
        "analysis_summaries",
    )
    for tbl in _tables:
        op.execute(f"ALTER TABLE public.{tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE public.{tbl} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"DROP POLICY IF EXISTS {tbl}_tenant_uuid_isolation ON public.{tbl};"
        )
        op.execute(f"""
            CREATE POLICY {tbl}_tenant_uuid_isolation ON public.{tbl}
            FOR ALL
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.current_tenant', true)::uuid
            )
            WITH CHECK (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.current_tenant', true)::uuid
            );
        """)

    # Append-only sur score_history si trigger manquant (idempotent)
    op.execute("""
        DO $body$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE p.proname = 'fn_reject_mutation' AND n.nspname = 'public'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_trigger t
                JOIN pg_class c ON c.oid = t.tgrelid
                WHERE c.relname = 'score_history' AND t.tgname = 'trg_score_history_append_only'
            ) THEN
                CREATE TRIGGER trg_score_history_append_only
                    BEFORE DELETE OR UPDATE ON public.score_history
                    FOR EACH ROW
                    EXECUTE FUNCTION public.fn_reject_mutation();
            END IF;
        END
        $body$;
    """)


def downgrade() -> None:
    _tables = (
        "survey_campaigns",
        "survey_campaign_items",
        "survey_campaign_zones",
        "market_surveys",
        "price_anomaly_alerts",
        "mercuriale_sources",
        "mercurials",
        "market_signals_v2",
        "offers",
        "extractions",
        "analysis_summaries",
    )
    for tbl in _tables:
        op.execute(
            f"DROP POLICY IF EXISTS {tbl}_tenant_uuid_isolation ON public.{tbl};"
        )
        op.execute(f"ALTER TABLE public.{tbl} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE public.{tbl} DISABLE ROW LEVEL SECURITY;")

    # Ne pas DROP trg_score_history_append_only : créé par 059_m14_score_history_elimination_log
    # si fn_reject_mutation existe ; 094 ne fait qu'un CREATE IF NOT EXISTS côté upgrade.

    op.execute("ALTER TABLE public.analysis_summaries DROP COLUMN IF EXISTS tenant_id;")
    op.execute("ALTER TABLE public.extractions DROP COLUMN IF EXISTS tenant_id;")
    op.execute("ALTER TABLE public.offers DROP COLUMN IF EXISTS tenant_id;")
    op.execute("ALTER TABLE public.market_signals_v2 DROP COLUMN IF EXISTS tenant_id;")
    op.execute("ALTER TABLE public.mercurials DROP COLUMN IF EXISTS tenant_id;")
    op.execute("ALTER TABLE public.mercuriale_sources DROP COLUMN IF EXISTS tenant_id;")
    op.execute(
        "ALTER TABLE public.price_anomaly_alerts DROP COLUMN IF EXISTS tenant_id;"
    )
    op.execute("ALTER TABLE public.market_surveys DROP COLUMN IF EXISTS tenant_id;")
    op.execute(
        "ALTER TABLE public.survey_campaign_zones DROP COLUMN IF EXISTS tenant_id;"
    )
    op.execute(
        "ALTER TABLE public.survey_campaign_items DROP COLUMN IF EXISTS tenant_id;"
    )
    op.execute("ALTER TABLE public.survey_campaigns DROP COLUMN IF EXISTS tenant_id;")
