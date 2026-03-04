"""
040_mercuriale_ingest

Crée les tables Couche B fondation mercuriale :
  - mercuriale_sources  : registre sources (SHA256 idempotent)
  - mercurials          : articles de prix officiels bruts

Décisions M5 (ingestion brute · RÈGLE-29) :
  - Pas de zone_id dans mercuriale_sources (zone varie par ligne)
  - Pas de FK vers units ou procurement_references (M6)
  - Pas de CHECK price_order en DB (violations tracées via review_required)
  - unit_price = colonne normale = price_avg (pas GENERATED ALWAYS)
  - Index btree simples · pas GIN tsvector (M6/M11 · TD-002)
  - unit_id et item_id = UUID nullable SANS FK (résolus en M6)

Révision     : 040_mercuriale_ingest
Down revision: m5_geo_fix_master
"""

revision = "040_mercuriale_ingest"
down_revision = "m5_geo_fix_master"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:

    # ── mercuriale_sources ─────────────────────────────────────────────
    # IF NOT EXISTS : idempotent — safe si tables créées hors migration
    op.execute("""
        CREATE TABLE IF NOT EXISTS mercuriale_sources (
            id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            filename          TEXT        NOT NULL,
            sha256            TEXT        NOT NULL,
            year              INTEGER     NOT NULL
                CHECK (year BETWEEN 2000 AND 2100),
            source_type       TEXT        NOT NULL
                CHECK (source_type IN (
                    'official_dgmp',
                    'official_ministry',
                    'ong_reference',
                    'corporate_survey',
                    'custom'
                )),
            imported_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            row_count         INTEGER,
            parse_status      TEXT        NOT NULL DEFAULT 'pending'
                CHECK (parse_status IN (
                    'pending', 'processing', 'done', 'failed', 'partial'
                )),
            extraction_engine TEXT        NOT NULL DEFAULT 'llamacloud',
            notes             TEXT,
            CONSTRAINT uq_mercuriale_sources_sha256 UNIQUE (sha256)
        );
    """)

    # ── mercurials ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS mercurials (
            id                   UUID          PRIMARY KEY
                DEFAULT gen_random_uuid(),
            source_id            UUID          NOT NULL
                REFERENCES mercuriale_sources(id) ON DELETE CASCADE,

            -- Identification article
            item_code            TEXT,
            item_canonical       TEXT          NOT NULL,
            group_label          TEXT,

            -- 3 prix officiels (source mercuriale DGMP Mali)
            price_min            NUMERIC(15,4) NOT NULL CHECK (price_min >= 0),
            price_avg            NUMERIC(15,4) NOT NULL CHECK (price_avg >= 0),
            price_max            NUMERIC(15,4) NOT NULL CHECK (price_max >= 0),

            -- unit_price = price_avg (référence marché · colonne normale)
            unit_price           NUMERIC(15,4) NOT NULL,

            currency             TEXT          NOT NULL DEFAULT 'XOF'
                CHECK (currency IN ('XOF', 'USD', 'EUR')),

            -- Unité brute (normalisée en M6)
            unit_raw             TEXT,
            -- Sans FK : résolus en M6
            unit_id              UUID,
            item_id              UUID,

            -- Géographie (zone_id TEXT car geo_master.id est VARCHAR)
            zone_raw             TEXT,
            zone_id              TEXT REFERENCES geo_master(id),
            year                 INTEGER       NOT NULL
                CHECK (year BETWEEN 2000 AND 2100),

            -- Qualité extraction
            confidence           FLOAT         NOT NULL DEFAULT 1.0
                CHECK (confidence BETWEEN 0.0 AND 1.0),
            review_required      BOOLEAN       NOT NULL DEFAULT FALSE,

            -- Métadonnées brutes (violations prix_order tracées ici)
            extraction_metadata  JSONB         NOT NULL DEFAULT '{}',

            created_at           TIMESTAMPTZ   NOT NULL DEFAULT now()
        );
    """)

    # ── Index btree (pas GIN tsvector en M5 · TD-002 · M6/M11) ──────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercurials_source_id
            ON mercurials(source_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercurials_year_zone
            ON mercurials(year, zone_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercurials_item_canonical
            ON mercurials(item_canonical);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercurials_review_required
            ON mercurials(review_required)
            WHERE review_required = TRUE;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercurials_year
            ON mercurials(year);
    """)

    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE
                'M5 · mercuriale_sources + mercurials créées · '
                'index btree · ingestion brute RÈGLE-29';
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mercurials CASCADE;")
    op.execute("DROP TABLE IF EXISTS mercuriale_sources CASCADE;")
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'DOWNGRADE 040 · mercurials + sources supprimées';
        END $$;
    """)
