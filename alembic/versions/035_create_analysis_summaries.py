"""
035_create_analysis_summaries

Revision ID : 035_create_analysis_summaries
Revises     : 034_pipeline_force_recompute
Create Date : 2026-02-24

Table append-only des résumés d'analyse générés par le moteur agnostique.
Contrat d'entrée M13 (renderer CBA).

INV-AS3  : append-only — UPDATE/DELETE interdits par trigger DB-level
INV-AS5  : result_jsonb = SummaryDocument v1 complet sérialisé
INV-AS9b : UNIQUE(result_hash) — idempotence DB-level
FK réelle : pipeline_run_id → pipeline_runs(pipeline_run_id) ON DELETE RESTRICT
triggered_by : CHECK 1–255 (alignement convention M10 INV-P11)
ADR-0015
"""
from alembic import op

revision = "035_create_analysis_summaries"
down_revision = "034_pipeline_force_recompute"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.analysis_summaries (
            summary_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

            -- FK logique vers cases.id (TEXT — règle universelle types §4.3)
            -- Contrôle applicatif dans generate_summary()
            case_id             TEXT        NOT NULL,

            -- FK DB réelle vers pipeline_runs (UUID — ON DELETE RESTRICT)
            -- NULL autorisé uniquement pour imports manuels / migrations historiques
            pipeline_run_id     UUID        NULL
                                REFERENCES public.pipeline_runs(pipeline_run_id)
                                ON DELETE RESTRICT,

            summary_version     TEXT        NOT NULL
                                CHECK (summary_version <> ''),

            summary_status      TEXT        NOT NULL
                                CHECK (summary_status IN (
                                    'ready', 'partial', 'blocked', 'failed'
                                )),

            source_pipeline_status TEXT     NULL,
            source_cas_version     TEXT     NULL,

            -- INV-AS5 : SummaryDocument v1 complet sérialisé
            result_jsonb        JSONB       NOT NULL,

            error_jsonb         JSONB       NOT NULL DEFAULT '[]'::jsonb,

            -- INV-AS9/AS9b : hash déterministe — UNIQUE pour idempotence DB-level
            result_hash         TEXT        NOT NULL,

            -- INV-P11 alignement M10 : non-vide et ≤ 255 caractères
            triggered_by        TEXT        NOT NULL
                                CHECK (char_length(triggered_by) BETWEEN 1 AND 255),

            generated_at        TIMESTAMPTZ NOT NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- INV-AS9b : idempotence DB-level
            CONSTRAINT uq_analysis_summaries_result_hash UNIQUE (result_hash)
        )
    """)

    op.execute("""
        COMMENT ON TABLE public.analysis_summaries IS
        'Journal append-only des résumés d''analyse générés par le moteur agnostique.
         result_jsonb = SummaryDocument v1 complet.
         result_hash = SHA-256 déterministe (INV-AS9) — UNIQUE pour idempotence (INV-AS9b).
         Contrat d''entrée M13 (renderer CBA). ADR-0015.'
    """)

    op.execute("""
        COMMENT ON COLUMN public.analysis_summaries.result_hash IS
        'SHA-256 du SummaryDocument canonicalisé (json.dumps sort_keys=True default=str).
         UNIQUE — idempotence DB-level (INV-AS9b).
         Même CAS v1 → même hash → une seule ligne max.
         Convention MG-01 : result_hash partout (source_result_hash banni).'
    """)

    op.execute("""
        COMMENT ON COLUMN public.analysis_summaries.pipeline_run_id IS
        'FK réelle vers pipeline_runs(pipeline_run_id) — UUID — ON DELETE RESTRICT.
         NULL autorisé uniquement pour imports manuels / migrations historiques.
         Contrôle applicatif dans generate_summary() si fourni.
         Décision GAP-02/MG : FK DB réelle.'
    """)

    op.execute("""
        COMMENT ON COLUMN public.analysis_summaries.case_id IS
        'FK logique vers cases.id (TEXT).
         Contrôle applicatif dans generate_summary().
         Règle universelle types §4.3.'
    """)

    op.execute("""
        COMMENT ON COLUMN public.analysis_summaries.result_jsonb IS
        'SummaryDocument v1 sérialisé complet (INV-AS5).
         Récupérable sans recalcul.
         Contenu : json.dumps(summary.model_dump(), default=str, sort_keys=True).
         Interdit : winner, rank, recommendation, best_offer, stc_*.'
    """)

    # Index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_analysis_summaries_case_created
        ON public.analysis_summaries (case_id, created_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_analysis_summaries_pipeline_run
        ON public.analysis_summaries (pipeline_run_id)
        WHERE pipeline_run_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_analysis_summaries_status
        ON public.analysis_summaries (summary_status)
    """)

    # Trigger append-only — INV-AS3
    op.execute("""
        CREATE OR REPLACE FUNCTION analysis_summaries_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'analysis_summaries is immutable (append-only) — '
                'UPDATE/DELETE forbidden. INV-AS3. ADR-0015.';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_analysis_summaries_append_only
        BEFORE UPDATE OR DELETE ON public.analysis_summaries
        FOR EACH ROW EXECUTE FUNCTION analysis_summaries_append_only()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_analysis_summaries_append_only "
        "ON public.analysis_summaries"
    )
    op.execute("DROP FUNCTION IF EXISTS analysis_summaries_append_only()")
    op.execute("DROP TABLE IF EXISTS public.analysis_summaries")
