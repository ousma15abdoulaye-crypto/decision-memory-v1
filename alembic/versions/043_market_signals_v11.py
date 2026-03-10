"""
043 - Market Signals V1.1

Cree market_signals_v2 (table propre M9).
NE TOUCHE PAS market_signals legacy (items.id INTEGER).
Cree signal_computation_log.
Cree 3 vues intelligence sur market_signals_v2.
Trigger formula_version immuable.

Decisions ADR-M9-FORMULA-V1.1 :
  market_signals legacy (15 lignes) = READ-ONLY
  market_signals_v2 = table propre M9
    item_id TEXT -> procurement_dict_items(item_id)
    zone_id TEXT -> geo_master(id)

Revision  : 043_market_signals_v11
Down      : 042_market_surveys
"""

from alembic import op

revision = "043_market_signals_v11"
down_revision = "042_market_surveys"
branch_labels = None
depends_on = None

FORMULA_VERSION = "1.1"


def upgrade() -> None:

    # ══════════════════════════════════════════════════
    # PHASE 1 -- market_signals_v2 (table propre M9)
    # ══════════════════════════════════════════════════

    op.execute("""
    CREATE TABLE IF NOT EXISTS public.market_signals_v2 (
        id                          UUID PRIMARY KEY
                                    DEFAULT gen_random_uuid(),
        item_id                     TEXT NOT NULL
                                    REFERENCES
                                    couche_b.procurement_dict_items(item_id),
        zone_id                     TEXT NOT NULL
                                    REFERENCES public.geo_master(id),
        price_avg                   NUMERIC(15,4),
        price_crisis_adj            NUMERIC(15,4),
        price_seasonal_adj          NUMERIC(15,4),
        residual_pct                NUMERIC(8,2),
        alert_level                 TEXT
                                    CHECK (alert_level IN (
                                      'CRITICAL','WARNING','WATCH',
                                      'CONTEXT_NORMAL','SEASONAL_NORMAL',
                                      'NORMAL'
                                    )),
        signal_quality              TEXT
                                    CHECK (signal_quality IN (
                                      'strong','moderate','weak',
                                      'empty','propagated'
                                    )),
        formula_version             TEXT NOT NULL DEFAULT '1.1',
        structural_markup_applied   NUMERIC(5,2) DEFAULT 0.00,
        seasonal_deviation_applied  NUMERIC(6,3) DEFAULT 0.000,
        context_type_at_computation TEXT,
        source_mercuriale_count     INTEGER DEFAULT 0,
        source_survey_count         INTEGER DEFAULT 0,
        source_decision_count       INTEGER DEFAULT 0,
        is_propagated               BOOLEAN DEFAULT FALSE,
        propagated_from_zone        TEXT,
        updated_at                  TIMESTAMPTZ DEFAULT now(),
        created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE UNIQUE INDEX IF NOT EXISTS uq_market_signals_v2_item_zone
      ON public.market_signals_v2(item_id, zone_id);

    CREATE INDEX IF NOT EXISTS idx_msv2_alert
      ON public.market_signals_v2(alert_level)
      WHERE alert_level IN ('CRITICAL','WARNING');

    CREATE INDEX IF NOT EXISTS idx_msv2_residual
      ON public.market_signals_v2(residual_pct DESC)
      WHERE residual_pct IS NOT NULL;

    CREATE INDEX IF NOT EXISTS idx_msv2_propagated
      ON public.market_signals_v2(is_propagated)
      WHERE is_propagated = TRUE;
    """)

    # ══════════════════════════════════════════════════
    # PHASE 2 -- signal_computation_log
    # ══════════════════════════════════════════════════

    op.execute("""
    CREATE TABLE IF NOT EXISTS public.signal_computation_log (
        id                  UUID PRIMARY KEY
                            DEFAULT gen_random_uuid(),
        item_id             TEXT NOT NULL,
        zone_id             TEXT NOT NULL,
        computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
        formula_version     TEXT NOT NULL DEFAULT '1.1',
        price_raw           NUMERIC(15,4),
        price_crisis_adj    NUMERIC(15,4),
        price_seasonal_adj  NUMERIC(15,4),
        residual_pct        NUMERIC(8,2),
        alert_level         TEXT,
        signal_quality      TEXT CHECK (signal_quality IN (
                              'strong','moderate','weak',
                              'empty','propagated'
                            )),
        source_count        INTEGER,
        sources_detail      JSONB,
        context_snapshot    JSONB,
        computation_ms      INTEGER,
        error_message       TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_scl_item_zone_date
      ON public.signal_computation_log
      (item_id, zone_id, computed_at DESC);

    CREATE INDEX IF NOT EXISTS idx_scl_alert
      ON public.signal_computation_log(alert_level)
      WHERE alert_level IN ('CRITICAL','WARNING');
    """)

    # ══════════════════════════════════════════════════
    # PHASE 3 -- Trigger formula_version immuable
    # ══════════════════════════════════════════════════

    op.execute("""
    CREATE OR REPLACE FUNCTION
    public.fn_market_signals_v2_formula_immutable()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        IF OLD.formula_version IS NOT NULL
           AND NEW.formula_version
               IS DISTINCT FROM OLD.formula_version
        THEN
            RAISE EXCEPTION
                '[M9] market_signals_v2.formula_version '
                'immuable apres INSERT. '
                'Valeur : %. Modification interdite.',
                OLD.formula_version;
        END IF;
        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS
      trg_market_signals_v2_formula_immutable
      ON public.market_signals_v2;
    CREATE TRIGGER
      trg_market_signals_v2_formula_immutable
    BEFORE UPDATE ON public.market_signals_v2
    FOR EACH ROW
    EXECUTE FUNCTION
    public.fn_market_signals_v2_formula_immutable();
    """)

    # ══════════════════════════════════════════════════
    # PHASE 4 -- Vues intelligence sur market_signals_v2
    # ══════════════════════════════════════════════════

    op.execute("""
    CREATE OR REPLACE VIEW public.price_series AS
    SELECT
        ms.item_id,
        ms.zone_id,
        date_trunc('month', ms.date_surveyed) AS month,
        AVG(ms.price_per_unit)                AS avg_price,
        MIN(ms.price_per_unit)                AS min_price,
        MAX(ms.price_per_unit)                AS max_price,
        COUNT(*)                              AS datapoints,
        STDDEV(ms.price_per_unit)             AS volatility
    FROM public.market_surveys ms
    WHERE ms.validation_status = 'validated'
      AND ms.price_per_unit IS NOT NULL
    GROUP BY ms.item_id, ms.zone_id,
             date_trunc('month', ms.date_surveyed);
    """)

    op.execute("""
    CREATE OR REPLACE VIEW
    public.vendor_price_positioning AS
    SELECT
        v.id                                  AS vendor_id,
        v.canonical_name,
        ms.item_id,
        ms.zone_id,
        AVG(ms.price_per_unit)                AS vendor_avg,
        sig.price_avg                         AS market_avg,
        sig.price_seasonal_adj                AS market_adj,
        ROUND(
          AVG(ms.price_per_unit)
          / NULLIF(sig.price_avg, 0), 3)      AS price_ratio,
        COUNT(ms.id)                          AS quote_count,
        sig.alert_level,
        CASE
          WHEN AVG(ms.price_per_unit)
               / NULLIF(sig.price_avg, 0) < 0.90
          THEN 'cheaper'
          WHEN AVG(ms.price_per_unit)
               / NULLIF(sig.price_avg, 0) > 1.20
          THEN 'premium'
          ELSE 'market_rate'
        END                                   AS positioning
    FROM public.market_surveys ms
    JOIN public.vendors v
      ON v.id        = ms.vendor_id
    JOIN public.market_signals_v2 sig
      ON sig.item_id = ms.item_id
     AND sig.zone_id = ms.zone_id
    WHERE ms.validation_status = 'validated'
      AND ms.vendor_id IS NOT NULL
    GROUP BY v.id, v.canonical_name,
             ms.item_id, ms.zone_id,
             sig.price_avg, sig.price_seasonal_adj,
             sig.alert_level;
    """)

    op.execute("""
    CREATE OR REPLACE VIEW public.basket_cost_by_zone AS
    SELECT
        mb.id               AS basket_id,
        mb.name             AS basket_name,
        mb.basket_type,
        sig.zone_id,
        gm.name             AS zone_name,
        zcr.context_type,
        zcr.severity_level,
        COUNT(mbi.item_id)  AS items_in_basket,
        COUNT(sig.item_id)  AS items_with_signal,
        SUM(
          sig.price_avg * mbi.default_quantity
        )                   AS total_cost_raw,
        SUM(
          COALESCE(sig.price_seasonal_adj, sig.price_avg)
          * mbi.default_quantity
        )                   AS total_cost_adj,
        MIN(sig.signal_quality) AS weakest_signal,
        COUNT(
          CASE WHEN sig.signal_quality = 'empty'
               THEN 1 END
        )                   AS missing_items,
        COUNT(
          CASE WHEN sig.alert_level
               IN ('CRITICAL','WARNING')
               THEN 1 END
        )                   AS alert_items
    FROM public.market_baskets mb
    JOIN public.market_basket_items mbi
      ON mbi.basket_id = mb.id
    LEFT JOIN public.market_signals_v2 sig
      ON sig.item_id = mbi.item_id
    LEFT JOIN public.geo_master gm
      ON gm.id = sig.zone_id
    LEFT JOIN public.zone_context_registry zcr
      ON zcr.zone_id    = sig.zone_id
     AND zcr.valid_until IS NULL
    GROUP BY mb.id, mb.name, mb.basket_type,
             sig.zone_id, gm.name,
             zcr.context_type, zcr.severity_level;
    """)

    # ══════════════════════════════════════════════════
    # PHASE 5 -- Refresh market_coverage
    # ══════════════════════════════════════════════════

    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM pg_matviews
            WHERE matviewname = 'market_coverage'
        ) THEN
            REFRESH MATERIALIZED VIEW CONCURRENTLY
                public.market_coverage;
        END IF;
    END;
    $$;
    """)

    # ══════════════════════════════════════════════════
    # FAIL-LOUD
    # ══════════════════════════════════════════════════

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name   = 'market_signals_v2'
              AND table_schema = 'public'
        ) THEN
            RAISE EXCEPTION
                '043 FAIL -- market_signals_v2 absente';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name   = 'signal_computation_log'
              AND table_schema = 'public'
        ) THEN
            RAISE EXCEPTION
                '043 FAIL -- signal_computation_log absente';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.views
            WHERE table_name   = 'price_series'
              AND table_schema = 'public'
        ) THEN
            RAISE EXCEPTION
                '043 FAIL -- price_series absente';
        END IF;

        RAISE NOTICE '043 UPGRADE OK -- V1.1 activee';
    END;
    $$;
    """)


def downgrade() -> None:
    """
    Inverse exact -- vues -> trigger -> tables.
    NE TOUCHE PAS market_signals legacy.
    """
    op.execute("""
    DROP VIEW IF EXISTS public.basket_cost_by_zone CASCADE;
    DROP VIEW IF EXISTS public.vendor_price_positioning CASCADE;
    DROP VIEW IF EXISTS public.price_series CASCADE;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS
      trg_market_signals_v2_formula_immutable
      ON public.market_signals_v2;
    DROP FUNCTION IF EXISTS
      public.fn_market_signals_v2_formula_immutable()
      CASCADE;
    """)

    op.execute("""
    DROP TABLE IF EXISTS public.signal_computation_log CASCADE;
    DROP TABLE IF EXISTS public.market_signals_v2 CASCADE;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name   = 'market_signals_v2'
              AND table_schema = 'public'
        ) THEN
            RAISE EXCEPTION
                '043 DOWNGRADE FAIL -- '
                'market_signals_v2 encore presente';
        END IF;
        RAISE NOTICE '043 DOWNGRADE OK';
    END;
    $$;
    """)
