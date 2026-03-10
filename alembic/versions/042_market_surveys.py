"""
042 · Market Intelligence Foundation

CLASSIFICATION DES TABLES :
  GLOBAL_CORE   : tracked_market_items,
                  tracked_market_zones,
                  market_baskets,
                  market_basket_items,
                  zone_context_registry,
                  zone_context_audit,
                  seasonal_patterns,
                  geo_price_corridors
  TENANT_SCOPED : survey_campaigns,
                  survey_campaign_items,
                  survey_campaign_zones,
                  market_surveys,
                  price_anomaly_alerts
  MATVIEW       : market_coverage (bornee scope tracked)

Adaptations schema reel confirmes par probe ETAPE 0 :
  item_id    : TEXT  cle existante couche_b.procurement_dict_items
               (pas item_uid — M8 utilise item_id, pas de PHASE 0)
  zone_id    : TEXT  compat geo_master.id VARCHAR(50)
  users.id   : INTEGER
  units.id   : INTEGER
  cases.id   : TEXT

Revision  : 042_market_surveys
Down      : m7_7_genome_stable
"""

from alembic import op

revision = "042_market_surveys"
down_revision = "m7_7_genome_stable"
branch_labels = None
depends_on = None

FN_APPEND_ONLY = "fn_reject_mutation"


def upgrade() -> None:

    # ══════════════════════════════════════════════════
    # PHASE 1 — GLOBAL_CORE sans FK externes
    # ══════════════════════════════════════════════════

    op.execute("""
    -- CLASSIFICATION : GLOBAL_CORE
    CREATE TABLE IF NOT EXISTS public.tracked_market_items (
        id         UUID PRIMARY KEY
                   DEFAULT gen_random_uuid(),
        item_id    TEXT NOT NULL UNIQUE
                   REFERENCES couche_b.procurement_dict_items(item_id),
        priority   TEXT NOT NULL DEFAULT 'strategic'
                   CHECK (priority IN (
                     'strategic','standard','monitoring')),
        notes      TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    -- CLASSIFICATION : GLOBAL_CORE
    CREATE TABLE IF NOT EXISTS public.tracked_market_zones (
        id         UUID PRIMARY KEY
                   DEFAULT gen_random_uuid(),
        zone_id    TEXT NOT NULL UNIQUE
                   REFERENCES public.geo_master(id),
        priority   TEXT NOT NULL DEFAULT 'strategic'
                   CHECK (priority IN (
                     'strategic','standard','monitoring')),
        notes      TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    -- CLASSIFICATION : GLOBAL_CORE
    -- Baskets systeme partages -- zero org_id
    CREATE TABLE IF NOT EXISTS public.market_baskets (
        id          UUID PRIMARY KEY
                    DEFAULT gen_random_uuid(),
        name        TEXT NOT NULL UNIQUE,
        description TEXT,
        basket_type TEXT NOT NULL DEFAULT 'custom'
                    CHECK (basket_type IN (
                      'humanitarian_nfi',
                      'humanitarian_food',
                      'construction_materials',
                      'medical_supplies',
                      'it_equipment',
                      'office_supplies',
                      'mining_operations',
                      'state_procurement',
                      'custom'
                    )),
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    # ══════════════════════════════════════════════════
    # PHASE 2 — GLOBAL_CORE avec FK geo_master
    # ══════════════════════════════════════════════════

    op.execute("""
    -- CLASSIFICATION : GLOBAL_CORE
    CREATE TABLE IF NOT EXISTS public.zone_context_registry (
        id                    UUID PRIMARY KEY
                              DEFAULT gen_random_uuid(),
        zone_id               TEXT NOT NULL
                              REFERENCES public.geo_master(id),
        context_type          TEXT NOT NULL
                              CHECK (context_type IN (
                                'security_crisis',
                                'seasonal_lean',
                                'seasonal_harvest',
                                'flood_disruption',
                                'displacement_shock',
                                'supply_blockade',
                                'normal'
                              )),
        severity_level        TEXT NOT NULL
                              CHECK (severity_level IN (
                                'ipc_1_minimal',
                                'ipc_2_stressed',
                                'ipc_3_crisis',
                                'ipc_4_emergency',
                                'ipc_5_catastrophe'
                              )),
        structural_markup_pct NUMERIC(5,2) NOT NULL
                              DEFAULT 0.00
                              CHECK (structural_markup_pct >= 0),
        access_difficulty     TEXT NOT NULL DEFAULT 'open'
                              CHECK (access_difficulty IN (
                                'open','restricted',
                                'very_restricted','inaccessible'
                              )),
        valid_from            DATE NOT NULL,
        valid_until           DATE,
        source                TEXT NOT NULL,
        source_url            TEXT,
        notes                 TEXT,
        created_by            INTEGER
                              REFERENCES public.users(id),
        created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_zcr_dates
          CHECK (valid_until IS NULL
                 OR valid_until >= valid_from)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_context_one_active
      ON public.zone_context_registry(zone_id)
      WHERE valid_until IS NULL;

    -- CLASSIFICATION : GLOBAL_CORE
    -- Granularite taxo_l3 -- INSTAT via M9 uniquement
    CREATE TABLE IF NOT EXISTS public.seasonal_patterns (
        id                       UUID PRIMARY KEY
                                 DEFAULT gen_random_uuid(),
        zone_id                  TEXT NOT NULL
                                 REFERENCES public.geo_master(id),
        taxo_l1                  TEXT NOT NULL,
        taxo_l2                  TEXT,
        taxo_l3                  TEXT NOT NULL,
        item_id                  TEXT REFERENCES
                                 couche_b.procurement_dict_items(item_id),
        month                    INTEGER NOT NULL
                                 CHECK (month BETWEEN 1 AND 12),
        historical_deviation_pct NUMERIC(6,3) NOT NULL,
        confidence               NUMERIC(3,2)
                                 CHECK (confidence BETWEEN 0 AND 1),
        years_observed           INTEGER,
        crisis_years_excluded    INTEGER DEFAULT 0,
        baseline_method          TEXT NOT NULL DEFAULT 'mean'
                                 CHECK (baseline_method IN (
                                   'mean','median','trimmed_mean'
                                 )),
        data_source              TEXT NOT NULL
                                 DEFAULT 'mercuriale_2023_2026',
        computation_version      TEXT NOT NULL DEFAULT 'v1.0',
        valid_for_year           INTEGER,
        superseded_by            UUID REFERENCES
                                 public.seasonal_patterns(id),
        last_computed            DATE,
        created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (zone_id, taxo_l3, month, computation_version)
    );

    -- CLASSIFICATION : GLOBAL_CORE
    -- Une ligne = un sens strict -- deux sens = deux lignes
    CREATE TABLE IF NOT EXISTS public.geo_price_corridors (
        id                UUID PRIMARY KEY
                          DEFAULT gen_random_uuid(),
        zone_from         TEXT NOT NULL
                          REFERENCES public.geo_master(id),
        zone_to           TEXT NOT NULL
                          REFERENCES public.geo_master(id),
        transport_markup  NUMERIC(5,3) NOT NULL DEFAULT 1.000
                          CHECK (transport_markup >= 1.000),
        reliability       NUMERIC(3,2)
                          CHECK (reliability BETWEEN 0 AND 1),
        route_type        TEXT NOT NULL
                          CHECK (route_type IN (
                            'paved','unpaved','river',
                            'seasonal','air_only'
                          )),
        crisis_multiplier NUMERIC(4,3) NOT NULL DEFAULT 1.000
                          CHECK (crisis_multiplier >= 1.000),
        last_verified     DATE,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (zone_from, zone_to)
    );
    """)

    # ══════════════════════════════════════════════════
    # PHASE 3 — GLOBAL_CORE dependantes
    # ══════════════════════════════════════════════════

    op.execute("""
    -- CLASSIFICATION : GLOBAL_CORE -- APPEND-ONLY
    CREATE TABLE IF NOT EXISTS public.zone_context_audit (
        id                  UUID PRIMARY KEY
                            DEFAULT gen_random_uuid(),
        context_id          UUID NOT NULL
                            REFERENCES public.zone_context_registry(id),
        zone_id             TEXT NOT NULL
                            REFERENCES public.geo_master(id),
        action              TEXT NOT NULL
                            CHECK (action IN (
                              'created','closed','superseded'
                            )),
        old_context_type    TEXT,
        new_context_type    TEXT,
        old_severity_level  TEXT,
        new_severity_level  TEXT,
        old_markup_pct      NUMERIC(5,2),
        new_markup_pct      NUMERIC(5,2),
        changed_by          INTEGER REFERENCES public.users(id),
        changed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
        reason              TEXT
    );

    -- CLASSIFICATION : GLOBAL_CORE
    CREATE TABLE IF NOT EXISTS public.market_basket_items (
        id               UUID PRIMARY KEY
                         DEFAULT gen_random_uuid(),
        basket_id        UUID NOT NULL
                         REFERENCES public.market_baskets(id),
        item_id          TEXT NOT NULL
                         REFERENCES
                         couche_b.procurement_dict_items(item_id),
        default_quantity NUMERIC(10,3) NOT NULL DEFAULT 1.0
                         CHECK (default_quantity > 0),
        unit_notes       TEXT,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (basket_id, item_id)
    );
    """)

    # ══════════════════════════════════════════════════
    # PHASE 4 — TENANT_SCOPED
    # ══════════════════════════════════════════════════

    op.execute("""
    -- CLASSIFICATION : TENANT_SCOPED
    CREATE TABLE IF NOT EXISTS public.survey_campaigns (
        id             UUID PRIMARY KEY
                       DEFAULT gen_random_uuid(),
        org_id         TEXT,
        name           TEXT NOT NULL,
        period         TEXT NOT NULL
                       CHECK (period IN (
                         'weekly','monthly','quarterly',
                         'annual','ad_hoc'
                       )),
        start_date     DATE NOT NULL,
        end_date       DATE,
        status         TEXT NOT NULL DEFAULT 'active'
                       CHECK (status IN (
                         'draft','active','closed'
                       )),
        target_collector_count INTEGER DEFAULT 1,
        notes          TEXT,
        created_by     INTEGER REFERENCES public.users(id),
        created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    -- CLASSIFICATION : TENANT_SCOPED
    CREATE TABLE IF NOT EXISTS public.survey_campaign_items (
        id          UUID PRIMARY KEY
                    DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL
                    REFERENCES public.survey_campaigns(id)
                    ON DELETE CASCADE,
        item_id     TEXT NOT NULL
                    REFERENCES
                    couche_b.procurement_dict_items(item_id),
        org_id      TEXT,
        UNIQUE (campaign_id, item_id)
    );

    -- CLASSIFICATION : TENANT_SCOPED
    CREATE TABLE IF NOT EXISTS public.survey_campaign_zones (
        id          UUID PRIMARY KEY
                    DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL
                    REFERENCES public.survey_campaigns(id)
                    ON DELETE CASCADE,
        zone_id     TEXT NOT NULL
                    REFERENCES public.geo_master(id),
        org_id      TEXT,
        UNIQUE (campaign_id, zone_id)
    );

    -- CLASSIFICATION : TENANT_SCOPED
    -- price_per_unit via trigger BEFORE INSERT
    -- collection_method : valeur mercuriale interdite par CHECK ci-dessous
    CREATE TABLE IF NOT EXISTS public.market_surveys (
        id                     UUID PRIMARY KEY
                               DEFAULT gen_random_uuid(),
        item_id                TEXT NOT NULL
                               REFERENCES
                               couche_b.procurement_dict_items(item_id),
        price_quoted           NUMERIC(15,4) NOT NULL
                               CHECK (price_quoted > 0),
        currency               TEXT NOT NULL DEFAULT 'XOF',
        quantity_surveyed      NUMERIC(10,3) NOT NULL
                               DEFAULT 1.0
                               CHECK (quantity_surveyed > 0),
        unit_id                INTEGER REFERENCES public.units(id),
        price_per_unit         NUMERIC(15,4),
        vendor_id              UUID REFERENCES public.vendors(id),
        supplier_raw           TEXT NOT NULL,
        match_status           TEXT NOT NULL DEFAULT 'unmatched'
                               CHECK (match_status IN (
                                 'matched','unmatched','review'
                               )),
        zone_id                TEXT NOT NULL
                               REFERENCES public.geo_master(id),
        date_surveyed          DATE NOT NULL,
        survey_type            TEXT NOT NULL DEFAULT 'ad_hoc'
                               CHECK (survey_type IN (
                                 'ad_hoc','systematic',
                                 'spot_check','verification'
                               )),
        campaign_id            UUID
                               REFERENCES public.survey_campaigns(id),
        case_id                TEXT REFERENCES public.cases(id),
        collected_by           INTEGER REFERENCES public.users(id),
        collection_method      TEXT NOT NULL DEFAULT 'phone'
                               CHECK (collection_method IN (
                                 'phone','physical',
                                 'written_quote','portal','spot'
                               )),
        validation_status      TEXT NOT NULL DEFAULT 'pending'
                               CHECK (validation_status IN (
                                 'pending','validated',
                                 'rejected','flagged'
                               )),
        validated_by           INTEGER REFERENCES public.users(id),
        validated_at           TIMESTAMPTZ,
        rejection_reason       TEXT,
        is_duplicate_candidate BOOLEAN NOT NULL DEFAULT FALSE,
        duplicate_of           UUID
                               REFERENCES public.market_surveys(id),
        notes                  TEXT,
        org_id                 TEXT,
        created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    -- CLASSIFICATION : TENANT_SCOPED
    -- Secteur-agnostique : ONG / Etat / Mines / Prive
    CREATE TABLE IF NOT EXISTS public.price_anomaly_alerts (
        id                    UUID PRIMARY KEY
                              DEFAULT gen_random_uuid(),
        item_id               TEXT NOT NULL
                              REFERENCES
                              couche_b.procurement_dict_items(item_id),
        zone_id               TEXT
                              REFERENCES public.geo_master(id),
        alert_type            TEXT NOT NULL
                              CHECK (alert_type IN (
                                'dao_above_market',
                                'survey_outlier',
                                'mercuriale_stale',
                                'cross_source_divergence',
                                'price_spike',
                                'vendor_systematic_premium',
                                'residual_post_crisis'
                              )),
        alert_level           TEXT NOT NULL
                              CHECK (alert_level IN (
                                'CRITICAL','WARNING','WATCH',
                                'CONTEXT_NORMAL','SEASONAL_NORMAL'
                              )),
        reference_price       NUMERIC(15,4),
        observed_price        NUMERIC(15,4),
        deviation_pct         NUMERIC(8,2),
        context_type          TEXT,
        structural_markup_pct NUMERIC(5,2),
        residual_pct          NUMERIC(8,2),
        source_survey_id      UUID,
        source_case_id        TEXT REFERENCES public.cases(id),
        status                TEXT NOT NULL DEFAULT 'open'
                              CHECK (status IN (
                                'open','acknowledged',
                                'resolved','false_positive'
                              )),
        org_id                TEXT,
        created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    # ══════════════════════════════════════════════════
    # PHASE 5 — TRIGGERS
    # ══════════════════════════════════════════════════

    op.execute("""
    CREATE OR REPLACE FUNCTION
    public.fn_compute_price_per_unit()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        NEW.price_per_unit :=
            CASE WHEN NEW.quantity_surveyed > 0
                 THEN NEW.price_quoted / NEW.quantity_surveyed
                 ELSE NULL
            END;
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_compute_price_per_unit
      ON public.market_surveys;
    CREATE TRIGGER trg_compute_price_per_unit
    BEFORE INSERT OR UPDATE ON public.market_surveys
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_compute_price_per_unit();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION
    public.fn_zone_context_no_overlap()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    DECLARE existing_id UUID;
    BEGIN
        IF NEW.valid_until IS NULL THEN
            SELECT id INTO existing_id
            FROM public.zone_context_registry
            WHERE zone_id     = NEW.zone_id
              AND valid_until IS NULL
              AND id          IS DISTINCT FROM NEW.id;
            IF existing_id IS NOT NULL THEN
                RAISE EXCEPTION
                    '[M8] Zone % a deja un contexte actif '
                    '(%). Fermer avant insertion.',
                    NEW.zone_id, existing_id;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_zone_context_no_overlap
      ON public.zone_context_registry;
    CREATE TRIGGER trg_zone_context_no_overlap
    BEFORE INSERT OR UPDATE ON public.zone_context_registry
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_zone_context_no_overlap();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION
    public.fn_zone_context_audit_log()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO public.zone_context_audit (
                context_id, zone_id, action,
                new_context_type, new_severity_level,
                new_markup_pct
            ) VALUES (
                NEW.id, NEW.zone_id, 'created',
                NEW.context_type, NEW.severity_level,
                NEW.structural_markup_pct
            );
        ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO public.zone_context_audit (
                context_id, zone_id, action,
                old_context_type, new_context_type,
                old_severity_level, new_severity_level,
                old_markup_pct, new_markup_pct
            ) VALUES (
                NEW.id, NEW.zone_id,
                CASE
                    WHEN NEW.valid_until IS NOT NULL
                     AND OLD.valid_until IS NULL
                    THEN 'closed'
                    ELSE 'superseded'
                END,
                OLD.context_type, NEW.context_type,
                OLD.severity_level, NEW.severity_level,
                OLD.structural_markup_pct,
                NEW.structural_markup_pct
            );
        END IF;
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_zone_context_audit_log
      ON public.zone_context_registry;
    CREATE TRIGGER trg_zone_context_audit_log
    AFTER INSERT OR UPDATE ON public.zone_context_registry
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_zone_context_audit_log();
    """)

    op.execute(f"""
    DROP TRIGGER IF EXISTS trg_zone_context_audit_append_only
      ON public.zone_context_audit;
    CREATE TRIGGER trg_zone_context_audit_append_only
    BEFORE DELETE OR UPDATE ON public.zone_context_audit
    FOR EACH ROW
    EXECUTE FUNCTION public.{FN_APPEND_ONLY}();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION
    public.fn_market_survey_immutable_validated()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        IF OLD.validation_status = 'validated' THEN
            IF NEW.price_quoted  IS DISTINCT FROM OLD.price_quoted
            OR NEW.item_id       IS DISTINCT FROM OLD.item_id
            OR NEW.zone_id       IS DISTINCT FROM OLD.zone_id
            OR NEW.date_surveyed IS DISTINCT FROM OLD.date_surveyed
            OR NEW.supplier_raw  IS DISTINCT FROM OLD.supplier_raw
            THEN
                RAISE EXCEPTION
                    '[M8] Survey % valide -- champs metier '
                    'immuables. Creer nouveau survey.',
                    OLD.id;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_market_survey_immutable_validated
      ON public.market_surveys;
    CREATE TRIGGER trg_market_survey_immutable_validated
    BEFORE UPDATE ON public.market_surveys
    FOR EACH ROW
    EXECUTE FUNCTION
    public.fn_market_survey_immutable_validated();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION
    public.fn_market_survey_flag_duplicate()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    DECLARE dup_id UUID;
    BEGIN
        SELECT id INTO dup_id
        FROM public.market_surveys
        WHERE item_id       = NEW.item_id
          AND zone_id       = NEW.zone_id
          AND date_surveyed = NEW.date_surveyed
          AND supplier_raw  = NEW.supplier_raw
          AND ABS(price_quoted - NEW.price_quoted)
              / NULLIF(NEW.price_quoted, 0) < 0.01
          AND id != COALESCE(NEW.id,
              '00000000-0000-0000-0000-000000000000')
        LIMIT 1;
        IF dup_id IS NOT NULL THEN
            NEW.is_duplicate_candidate := TRUE;
            NEW.duplicate_of           := dup_id;
        END IF;
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_market_survey_flag_duplicate
      ON public.market_surveys;
    CREATE TRIGGER trg_market_survey_flag_duplicate
    BEFORE INSERT ON public.market_surveys
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_market_survey_flag_duplicate();
    """)

    # ══════════════════════════════════════════════════
    # PHASE 6 — MATVIEW bornee scope tracked
    # ══════════════════════════════════════════════════

    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS public.market_coverage AS
    SELECT
        di.item_id,
        di.label_fr,
        gm.id   AS zone_id,
        gm.name AS zone_name,
        COUNT(ms.id)              AS survey_count,
        MAX(ms.date_surveyed)     AS last_surveyed,
        zcr.context_type,
        zcr.severity_level,
        zcr.structural_markup_pct,
        CASE
            WHEN COUNT(ms.id) = 0
              THEN 'blank'
            WHEN MAX(ms.date_surveyed) <
                 CURRENT_DATE - INTERVAL '90 days'
              THEN 'stale'
            WHEN COUNT(ms.id) < 3
              THEN 'sparse'
            WHEN zcr.context_type = 'security_crisis'
              THEN 'crisis_covered'
            ELSE 'covered'
        END AS coverage_status
    FROM public.tracked_market_items tmi
    JOIN couche_b.procurement_dict_items di
      ON di.item_id = tmi.item_id
    JOIN public.tracked_market_zones tmz
      ON TRUE
    JOIN public.geo_master gm
      ON gm.id = tmz.zone_id
    LEFT JOIN public.market_surveys ms
      ON  ms.item_id           = di.item_id
      AND ms.zone_id           = gm.id
      AND ms.validation_status = 'validated'
    LEFT JOIN public.zone_context_registry zcr
      ON  zcr.zone_id    = gm.id
      AND zcr.valid_from <= CURRENT_DATE
      AND (zcr.valid_until IS NULL
           OR zcr.valid_until >= CURRENT_DATE)
    GROUP BY
        di.item_id, di.label_fr,
        gm.id, gm.name,
        zcr.context_type,
        zcr.severity_level,
        zcr.structural_markup_pct;

    REFRESH MATERIALIZED VIEW public.market_coverage;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_market_coverage_pk
      ON public.market_coverage(item_id, zone_id);
    """)

    # ══════════════════════════════════════════════════
    # PHASE 7 — INDEXES
    # ══════════════════════════════════════════════════

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_ms_item_zone
      ON public.market_surveys(item_id, zone_id);
    CREATE INDEX IF NOT EXISTS idx_ms_date
      ON public.market_surveys(date_surveyed DESC);
    CREATE INDEX IF NOT EXISTS idx_ms_validation
      ON public.market_surveys(validation_status);
    CREATE INDEX IF NOT EXISTS idx_ms_org
      ON public.market_surveys(org_id);
    CREATE INDEX IF NOT EXISTS idx_ms_vendor
      ON public.market_surveys(vendor_id);
    CREATE INDEX IF NOT EXISTS idx_ms_campaign
      ON public.market_surveys(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_zcr_zone
      ON public.zone_context_registry(zone_id);
    CREATE INDEX IF NOT EXISTS idx_sp_zone_taxo
      ON public.seasonal_patterns(zone_id, taxo_l3);
    CREATE INDEX IF NOT EXISTS idx_gpc_from_to
      ON public.geo_price_corridors(zone_from, zone_to);
    CREATE INDEX IF NOT EXISTS idx_paa_item_zone
      ON public.price_anomaly_alerts(item_id, zone_id);
    CREATE INDEX IF NOT EXISTS idx_paa_level
      ON public.price_anomaly_alerts(alert_level);
    CREATE INDEX IF NOT EXISTS idx_paa_org
      ON public.price_anomaly_alerts(org_id);
    """)

    # ══════════════════════════════════════════════════
    # VERIFICATION FAIL-LOUD
    # ══════════════════════════════════════════════════

    op.execute("""
    DO $$
    DECLARE
        missing TEXT := '';
        tbl     TEXT;
    BEGIN
        FOREACH tbl IN ARRAY ARRAY[
            'tracked_market_items','tracked_market_zones',
            'market_baskets','zone_context_registry',
            'seasonal_patterns','geo_price_corridors',
            'zone_context_audit','market_basket_items',
            'survey_campaigns','survey_campaign_items',
            'survey_campaign_zones','market_surveys',
            'price_anomaly_alerts'
        ] LOOP
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name  = tbl
                  AND table_schema = 'public'
            ) THEN
                missing := missing || tbl || ' ';
            END IF;
        END LOOP;
        IF missing != '' THEN
            RAISE EXCEPTION
                '042 UPGRADE FAIL -- tables manquantes : %',
                missing;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_matviews
            WHERE matviewname = 'market_coverage'
        ) THEN
            RAISE EXCEPTION
                '042 UPGRADE FAIL -- market_coverage absente';
        END IF;
        RAISE NOTICE '042 UPGRADE OK -- 13 tables + matview';
    END;
    $$;
    """)


def downgrade() -> None:
    """
    Inverse exact -- triggers -> fonctions -> matview
    -> TENANT_SCOPED -> GLOBAL_CORE dep -> GLOBAL_CORE FK
    -> GLOBAL_CORE sans FK
    M8 ne modifie pas procurement_dict_items : aucun DROP COLUMN.
    """
    op.execute("""
    DROP TRIGGER IF EXISTS trg_zone_context_audit_append_only
      ON public.zone_context_audit;
    DROP TRIGGER IF EXISTS trg_market_survey_flag_duplicate
      ON public.market_surveys;
    DROP TRIGGER IF EXISTS trg_market_survey_immutable_validated
      ON public.market_surveys;
    DROP TRIGGER IF EXISTS trg_zone_context_audit_log
      ON public.zone_context_registry;
    DROP TRIGGER IF EXISTS trg_zone_context_no_overlap
      ON public.zone_context_registry;
    DROP TRIGGER IF EXISTS trg_compute_price_per_unit
      ON public.market_surveys;

    DROP FUNCTION IF EXISTS
      public.fn_market_survey_flag_duplicate() CASCADE;
    DROP FUNCTION IF EXISTS
      public.fn_market_survey_immutable_validated() CASCADE;
    DROP FUNCTION IF EXISTS
      public.fn_zone_context_audit_log() CASCADE;
    DROP FUNCTION IF EXISTS
      public.fn_zone_context_no_overlap() CASCADE;
    DROP FUNCTION IF EXISTS
      public.fn_compute_price_per_unit() CASCADE;

    DROP MATERIALIZED VIEW IF EXISTS
      public.market_coverage CASCADE;

    DROP TABLE IF EXISTS public.price_anomaly_alerts  CASCADE;
    DROP TABLE IF EXISTS public.market_surveys        CASCADE;
    DROP TABLE IF EXISTS public.survey_campaign_zones CASCADE;
    DROP TABLE IF EXISTS public.survey_campaign_items CASCADE;
    DROP TABLE IF EXISTS public.survey_campaigns      CASCADE;

    DROP TABLE IF EXISTS public.market_basket_items   CASCADE;
    DROP TABLE IF EXISTS public.zone_context_audit    CASCADE;

    DROP TABLE IF EXISTS public.geo_price_corridors   CASCADE;
    DROP TABLE IF EXISTS public.seasonal_patterns     CASCADE;
    DROP TABLE IF EXISTS public.zone_context_registry CASCADE;

    DROP TABLE IF EXISTS public.market_baskets        CASCADE;
    DROP TABLE IF EXISTS public.tracked_market_zones  CASCADE;
    DROP TABLE IF EXISTS public.tracked_market_items  CASCADE;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name  = 'market_surveys'
              AND table_schema = 'public'
        ) THEN
            RAISE EXCEPTION
                '042 DOWNGRADE FAIL -- '
                'market_surveys encore presente';
        END IF;
        RAISE NOTICE '042 DOWNGRADE OK';
    END;
    $$;
    """)
