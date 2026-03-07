"""
M7.4 · Dict Vivant.

Contenu :
  1. ADD COLUMN updated_at sur procurement_dict_items (si absent)
  2. ADD COLUMNs métriques + audit sur taxo_proposals_v2
  3. Patch fn_compute_quality_score → O(1) + pg_trigger_depth guard
  4. Vue dict_classification_metrics
  5. Vérification fail-loud

RÈGLE-T04  : zéro DROP
RÈGLE-12   : SQL brut uniquement
RÈGLE-QS   : trigger O(1) · zéro sous-requête
RÈGLE-TRG  : pg_trigger_depth guard
RÈGLE-AUD  : approved_by + approved_at présents
"""
from alembic import op

revision = "m7_4_dict_vivant"
down_revision = "m7_3b_deprecate_legacy_families"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # 1 · updated_at sur procurement_dict_items
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMPTZ NOT NULL DEFAULT NOW()
    """)

    # 1b · quality_score : NUMERIC(5,4) 0-1 → SMALLINT 0-100
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_items
        ALTER COLUMN quality_score TYPE SMALLINT
        USING LEAST(COALESCE(quality_score, 0) * 100, 100)::INTEGER
    """)

    # 2 · Colonnes métriques + audit sur taxo_proposals_v2
    op.execute("""
        ALTER TABLE couche_b.taxo_proposals_v2
        ADD COLUMN IF NOT EXISTS token_entropy
            NUMERIC(6,4),
        ADD COLUMN IF NOT EXISTS confidence_source
            TEXT NOT NULL DEFAULT 'llm_self_report'
            CHECK (confidence_source IN (
                'llm_self_report','logprob','human_ao'
            )),
        ADD COLUMN IF NOT EXISTS calibrated_confidence
            NUMERIC(5,4),
        ADD COLUMN IF NOT EXISTS batch_job_id
            TEXT,
        ADD COLUMN IF NOT EXISTS batch_custom_id
            TEXT,
        ADD COLUMN IF NOT EXISTS approved_by
            INTEGER REFERENCES users(id),
        ADD COLUMN IF NOT EXISTS approved_at
            TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS reviewed_by
            INTEGER REFERENCES users(id),
        ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMPTZ DEFAULT NOW()
    """)

    # 3 · Patch fn_compute_quality_score → O(1) + guard (RÈGLE-QS + RÈGLE-TRG)
    #
    # FAILLE COMBLÉE : ancienne version faisait SELECT EXISTS sur
    # dict_price_references dans le trigger = N requêtes pour N items.
    # Nouvelle version = O(1) · colonnes locales uniquement.
    # Les champs dérivés de tables externes (prix, UNSPSC) sont
    # recalculés par scripts/recompute_quality.py (batch séparé).
    #
    # Score O(1) :
    #   domain_id non null          → 30 pts (taxonomie)
    #   default_uom non null        → 20 pts (UOM)
    #   classification_confidence   → 10 pts si ≥ 0.75
    #   human_validated             → 10 pts
    #   label_fr long ≥ 10 chars    → 10 pts (qualité libellé)
    #   canonical_slug propre       → 10 pts (slug non numérique)
    #   aliases : skip (procurement_dict_aliases séparé) · max 90 pts
    op.execute("""
        CREATE OR REPLACE FUNCTION couche_b.fn_compute_quality_score()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            v_score INTEGER := 0;
        BEGIN
            -- GUARD ANTI-RÉCURSION · RÈGLE-TRG
            IF pg_trigger_depth() > 1 THEN
                RETURN NEW;
            END IF;

            -- Taxonomie L1/L2/L3 complète (30 pts)
            IF NEW.domain_id IS NOT NULL
               AND NEW.family_l2_id IS NOT NULL
               AND NEW.subfamily_id IS NOT NULL
            THEN
                v_score := v_score + 30;
            END IF;

            -- UOM renseigné (20 pts)
            IF NEW.default_uom IS NOT NULL
               AND TRIM(NEW.default_uom) != ''
            THEN
                v_score := v_score + 20;
            END IF;

            -- Confidence classification ≥ 0.75 (10 pts)
            IF COALESCE(NEW.classification_confidence, 0) >= 0.75 THEN
                v_score := v_score + 10;
            END IF;

            -- Validé humain (10 pts)
            IF NEW.human_validated THEN
                v_score := v_score + 10;
            END IF;

            -- Label fr ≥ 10 chars (10 pts)
            IF LENGTH(TRIM(COALESCE(NEW.label_fr, ''))) >= 10 THEN
                v_score := v_score + 10;
            END IF;

            -- Slug non numérique et ≥ 4 chars (10 pts)
            IF COALESCE(NEW.canonical_slug, '') !~ '^[0-9]+$'
               AND LENGTH(COALESCE(NEW.canonical_slug, '')) >= 4
            THEN
                v_score := v_score + 10;
            END IF;

            -- Aliases : procurement_dict_items n'a pas de colonne aliases
            -- (aliases dans procurement_dict_aliases). O(1) = skip. Max 90 pts.

            NEW.quality_score := v_score;
            NEW.needs_review  := (v_score < 70);
            NEW.updated_at    := NOW();
            RETURN NEW;
        END;
        $$
    """)

    # 4 · Vue métriques classification
    op.execute("""
        CREATE OR REPLACE VIEW couche_b.dict_classification_metrics AS
        SELECT
            ROUND(confidence::NUMERIC, 1)              AS conf_bucket,
            COUNT(*)                                   AS total,
            COUNT(*) FILTER (WHERE status='approved')  AS approved,
            COUNT(*) FILTER (WHERE status='rejected')  AS rejected,
            COUNT(*) FILTER (WHERE status='pending')   AS pending,
            COUNT(*) FILTER (WHERE status='flagged')   AS flagged,
            ROUND(
                COUNT(*) FILTER (WHERE status='approved')::NUMERIC
                / NULLIF(
                    COUNT(*) FILTER (
                        WHERE status IN ('approved','rejected')
                    ), 0
                ), 3
            )                                          AS empirical_precision
        FROM couche_b.taxo_proposals_v2
        WHERE taxo_version = '2.0.0'
        GROUP BY ROUND(confidence::NUMERIC, 1)
        ORDER BY conf_bucket
    """)

    # 5 · Vérification fail-loud
    op.execute("""
        DO $$
        DECLARE
            v_src TEXT;
        BEGIN
            SELECT prosrc INTO v_src
            FROM pg_proc
            WHERE proname = 'fn_compute_quality_score'
              AND pronamespace = (
                SELECT oid FROM pg_namespace WHERE nspname='couche_b'
              );

            IF v_src NOT LIKE '%pg_trigger_depth%' THEN
                RAISE EXCEPTION
                    'M7.4 ABORT: pg_trigger_depth guard absent · RÈGLE-TRG';
            END IF;

            IF v_src LIKE '%dict_price_references%'
               OR v_src LIKE '%SELECT EXISTS%'
            THEN
                RAISE EXCEPTION
                    'M7.4 ABORT: trigger contient sous-requête · RÈGLE-QS violée';
            END IF;

            RAISE NOTICE 'M7.4 migration OK · trigger O(1) + guard actifs';
        END;
        $$
    """)


def downgrade() -> None:
    op.execute(
        "DROP VIEW IF EXISTS couche_b.dict_classification_metrics"
    )
    for col in [
        "token_entropy", "confidence_source", "calibrated_confidence",
        "batch_job_id", "batch_custom_id",
        "approved_by", "approved_at", "reviewed_by", "updated_at",
    ]:
        op.execute(
            f"ALTER TABLE couche_b.taxo_proposals_v2 "
            f"DROP COLUMN IF EXISTS {col}"
        )
    # updated_at conservée · utile même sans M7.4
    # fn_compute_quality_score : version antérieure non reversée
    # (guard est safe en downgrade · zéro régression)
