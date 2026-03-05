"""
m5_patch_imc_ingest_v410

Patch post-M5 : tables IMC (Indice Prix Matériaux Construction)
Série temporelle 2018→2026 · trous tracés · ingestion brute

Schéma minimal délibéré (critique CTO 2026-03-03) :
  · category_normalized NULL en M5 patch → normalisation future
  · confidence/evidence ajoutés uniquement si extraction instable
  · base_year au niveau source · pas par ligne

RÈGLE-12  : SQL brut op.execute() · zéro autogenerate
PIÈGE-09  : down_revision copié depuis alembic heads · jamais supposé
DA-009    : trous tracés dans gaps_detected · pas interpolés

Révision     : m5_patch_imc_ingest_v410
Down revision: m5_geo_patch_koutiala
"""

from alembic import op

revision = "m5_patch_imc_ingest_v410"
down_revision = "m5_geo_patch_koutiala"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # TABLE 1 : imc_sources — registre fichiers
    # Schéma minimal · sha256 pour cache-first
    # IF NOT EXISTS : idempotent — safe si tables créées hors migration
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS imc_sources (
            id              VARCHAR         PRIMARY KEY
                DEFAULT gen_random_uuid()::text,

            sha256          VARCHAR(64)     NOT NULL UNIQUE,
            filename        VARCHAR(512)    NOT NULL,
            source_year     INTEGER         NOT NULL,
            source_month    INTEGER,

            period_start    DATE,
            period_end      DATE,

            base_year       INTEGER,

            gaps_detected   JSONB           NOT NULL DEFAULT '[]',

            parse_method    VARCHAR(32)     NOT NULL DEFAULT 'native_pdf',
            parse_status    VARCHAR(16)     NOT NULL DEFAULT 'pending'
                CHECK (parse_status IN (
                    'pending', 'success',
                    'partial', 'failed'
                )),
            raw_page_count  INTEGER,
            imported_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

            CONSTRAINT imc_sources_year_check
                CHECK (source_year BETWEEN 2015 AND 2030)
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_sources_year
            ON imc_sources(source_year);
    """)

    # ------------------------------------------------------------------
    # TABLE 2 : imc_entries — une ligne = indice · catégorie · mois
    # RÈGLE-34 : period_month NOT NULL (série temporelle)
    # IF NOT EXISTS : idempotent
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS imc_entries (
            id              VARCHAR         PRIMARY KEY
                DEFAULT gen_random_uuid()::text,

            source_id       VARCHAR         NOT NULL
                REFERENCES imc_sources(id)
                ON DELETE RESTRICT,

            category_raw        VARCHAR(512)    NOT NULL,
            category_normalized VARCHAR(512),

            period_year     INTEGER         NOT NULL,
            period_month    INTEGER         NOT NULL,

            index_value     NUMERIC(10,4),
            variation_mom   NUMERIC(8,4),
            variation_yoy   NUMERIC(8,4),

            review_required BOOLEAN         NOT NULL DEFAULT FALSE,

            created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

            CONSTRAINT imc_entries_unique
                UNIQUE (source_id, category_raw, period_year, period_month),

            CONSTRAINT imc_entries_year_check
                CHECK (period_year BETWEEN 2015 AND 2030),

            CONSTRAINT imc_entries_month_check
                CHECK (period_month BETWEEN 1 AND 12)
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_entries_period
            ON imc_entries(period_year, period_month);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_entries_source
            ON imc_entries(source_id);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_imc_entries_category
            ON imc_entries(category_normalized)
            WHERE category_normalized IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS imc_entries;")
    op.execute("DROP TABLE IF EXISTS imc_sources;")
