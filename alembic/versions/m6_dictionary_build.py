"""
alembic/versions/m6_dictionary_build.py

M6 Dictionary Build · Extension schéma couche_b existant

Architecture réelle confirmée par probe 2026-03-XX :
  couche_b.procurement_dict_items    → 51 items curatés · PK = item_id
  couche_b.procurement_dict_aliases  → 157 aliases · UNIQUE normalized_alias
  couche_b.procurement_dict_families → 9 familles · criticité
  couche_b.procurement_dict_units    → 15 unités

Ce que cette migration fait :
  1. Étend procurement_dict_items (colonnes M6 manquantes)
  2. Peuple canonical_slug depuis item_id (déjà slugs stables)
  3. Ajoute index trgm sur couche_b (matching fuzzy)
  4. Crée couche_b.dict_proposals (file validation humaine)
  5. Étend dict_collision_log public (colonnes M6)
  6. Recrée vues public.dict_items + public.dict_aliases
     (supprimées accidentellement par migration M6 erronée)
  7. unaccent si absente

Ce que cette migration NE FAIT PAS :
  · Pas de CREATE TABLE pour procurement_dict_*
    (tables existantes · données intactes)
  · Pas de modification de procurement_references
    (table métier active · hors scope)
  · Pas de tables dict_* dans public
    (public = vues uniquement · source de vérité = couche_b)

RÈGLE-12  : SQL brut · op.execute("...") · zéro sa.text()
RÈGLE-41  : import sqlalchemy interdit
PIÈGE-09  : down_revision = alembic heads réel
"""

from alembic import op

revision      = "m6_dictionary_build"
down_revision = "m5_patch_imc_ingest_v410"
branch_labels = None
depends_on    = None

_HAS_TRGM = True  # confirmé probe P10 · pg_trgm 1.6


def _add_col(
    schema: str, table: str,
    column: str, definition: str,
) -> None:
    """Ajoute une colonne si absente · idempotent."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = '{schema}'
                  AND table_name   = '{table}'
                  AND column_name  = '{column}'
            ) THEN
                ALTER TABLE {schema}.{table}
                ADD COLUMN {column} {definition};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:

    # ------------------------------------------------------------------
    # ÉTAPE 0 · Extensions
    # unaccent absente confirmée · pg_trgm présente
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    if _HAS_TRGM:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # ------------------------------------------------------------------
    # ÉTAPE 1 · Étendre couche_b.procurement_dict_items
    # Colonnes M6 manquantes confirmées par probe
    # ------------------------------------------------------------------
    _add_col("couche_b", "procurement_dict_items",
             "canonical_slug", "TEXT")

    _add_col("couche_b", "procurement_dict_items",
             "dict_version", "TEXT NOT NULL DEFAULT '1.0.0'")

    _add_col("couche_b", "procurement_dict_items",
             "confidence_score", "NUMERIC(5,4) NOT NULL DEFAULT 0.5")

    _add_col("couche_b", "procurement_dict_items",
             "human_validated", "BOOLEAN NOT NULL DEFAULT FALSE")

    _add_col("couche_b", "procurement_dict_items",
             "validated_by", "TEXT")

    _add_col("couche_b", "procurement_dict_items",
             "validated_at", "TIMESTAMPTZ")

    _add_col("couche_b", "procurement_dict_items",
             "sources", "JSONB NOT NULL DEFAULT '[]'")

    _add_col("couche_b", "procurement_dict_items",
             "last_seen", "DATE")

    _add_col("couche_b", "procurement_dict_items",
             "updated_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()")

    # ------------------------------------------------------------------
    # ÉTAPE 2 · Peupler canonical_slug depuis item_id
    # item_id est déjà un slug stable (ex: 'gasoil' · 'ciment_cpa_42_5')
    # canonical_slug = item_id pour les 51 items existants
    # ------------------------------------------------------------------
    op.execute("""
        UPDATE couche_b.procurement_dict_items
        SET canonical_slug = item_id
        WHERE canonical_slug IS NULL;
    """)

    # Contrainte UNIQUE sur canonical_slug
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'couche_b'
                  AND tablename  = 'procurement_dict_items'
                  AND indexname  = 'uq_dict_items_canonical_slug'
            ) THEN
                CREATE UNIQUE INDEX uq_dict_items_canonical_slug
                ON couche_b.procurement_dict_items(canonical_slug)
                WHERE canonical_slug IS NOT NULL;
            END IF;
        END $$;
    """)

    # confidence_score = 0.9 pour les items seed_sahel curatés
    op.execute("""
        UPDATE couche_b.procurement_dict_items
        SET confidence_score = 0.9,
            human_validated  = TRUE,
            sources          = '["seed_sahel"]'
        WHERE confidence_score = 0.5;
    """)

    # ------------------------------------------------------------------
    # ÉTAPE 3 · Étendre couche_b.procurement_dict_aliases
    # Ajouter confidence · normalized_alias déjà présent
    # ------------------------------------------------------------------
    _add_col("couche_b", "procurement_dict_aliases",
             "confidence", "NUMERIC(5,4)")

    # Index trgm sur normalized_alias (matching fuzzy M6)
    if _HAS_TRGM:
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = 'couche_b'
                      AND tablename  = 'procurement_dict_aliases'
                      AND indexname  = 'idx_dict_aliases_trgm'
                ) THEN
                    CREATE INDEX idx_dict_aliases_trgm
                    ON couche_b.procurement_dict_aliases
                    USING GIN (normalized_alias gin_trgm_ops);
                END IF;
            END $$;
        """)

        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = 'couche_b'
                      AND tablename  = 'procurement_dict_items'
                      AND indexname  = 'idx_dict_items_trgm'
                ) THEN
                    CREATE INDEX idx_dict_items_trgm
                    ON couche_b.procurement_dict_items
                    USING GIN (canonical_slug gin_trgm_ops)
                    WHERE canonical_slug IS NOT NULL;
                END IF;
            END $$;
        """)

    # Index is_active (active column existante)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'couche_b'
                  AND tablename  = 'procurement_dict_items'
                  AND indexname  = 'idx_dict_items_active'
            ) THEN
                CREATE INDEX idx_dict_items_active
                ON couche_b.procurement_dict_items(active)
                WHERE active = TRUE;
            END IF;
        END $$;
    """)

    # Index review queue
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'couche_b'
                  AND tablename  = 'procurement_dict_items'
                  AND indexname  = 'idx_dict_items_review'
            ) THEN
                CREATE INDEX idx_dict_items_review
                ON couche_b.procurement_dict_items(human_validated)
                WHERE human_validated = FALSE
                  AND active = TRUE;
            END IF;
        END $$;
    """)

    # ------------------------------------------------------------------
    # ÉTAPE 4 · Créer couche_b.dict_proposals
    # File validation humaine · RÈGLE-25
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.dict_proposals (
            id            TEXT         PRIMARY KEY,
            item_id       TEXT
                          REFERENCES
                          couche_b.procurement_dict_items(item_id)
                          ON DELETE RESTRICT,
            proposed_form TEXT         NOT NULL,
            confidence    NUMERIC(5,4),
            status        TEXT         NOT NULL DEFAULT 'pending'
                                       CHECK (status IN (
                                           'pending',
                                           'approved',
                                           'rejected'
                                       )),
            reviewed_by   TEXT,
            reviewed_at   TIMESTAMPTZ,
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'couche_b'
                  AND tablename  = 'dict_proposals'
                  AND indexname  = 'idx_dict_proposals_pending'
            ) THEN
                CREATE INDEX idx_dict_proposals_pending
                ON couche_b.dict_proposals(status)
                WHERE status = 'pending';
            END IF;
        END $$;
    """)

    # ------------------------------------------------------------------
    # ÉTAPE 5 · Étendre public.dict_collision_log (colonnes M6)
    # Schéma existant conservé intégralement · RÈGLE-40
    # detected_at = created_at existant · pas de doublon
    # ------------------------------------------------------------------
    _add_col("public", "dict_collision_log",
             "collision_type", "TEXT")
    _add_col("public", "dict_collision_log",
             "item_a_id", "TEXT")
    _add_col("public", "dict_collision_log",
             "item_b_id", "TEXT")
    _add_col("public", "dict_collision_log",
             "alias_conflicted", "TEXT")

    # ------------------------------------------------------------------
    # ÉTAPE 6 · Recréer vues public.dict_items + public.dict_aliases
    # Supprimées accidentellement par migration M6 erronée
    # Miroirs de couche_b · colonnes étendues M6 incluses
    # ------------------------------------------------------------------
    op.execute("DROP VIEW IF EXISTS public.dict_items;")
    op.execute("""
        CREATE VIEW public.dict_items AS
        SELECT
            item_id,
            family_id,
            label_fr,
            label_en,
            default_unit,
            active,
            canonical_slug,
            dict_version,
            confidence_score,
            human_validated,
            validated_by,
            validated_at,
            sources,
            last_seen,
            updated_at
        FROM couche_b.procurement_dict_items;
    """)

    op.execute("DROP VIEW IF EXISTS public.dict_aliases;")
    op.execute("""
        CREATE VIEW public.dict_aliases AS
        SELECT
            alias_id,
            item_id,
            alias_raw,
            normalized_alias,
            source,
            confidence
        FROM couche_b.procurement_dict_aliases;
    """)

    # ------------------------------------------------------------------
    # ÉTAPE 7 · Vérification post-migration (fail-loud)
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        DECLARE
            v_items    INTEGER;
            v_aliases  INTEGER;
            v_slug_ok  INTEGER;
        BEGIN
            -- 51 items intacts
            SELECT COUNT(*) INTO v_items
            FROM couche_b.procurement_dict_items;
            IF v_items < 51 THEN
                RAISE EXCEPTION
                    'procurement_dict_items : % lignes · attendu ≥ 51',
                    v_items;
            END IF;

            -- 157 aliases intacts
            SELECT COUNT(*) INTO v_aliases
            FROM couche_b.procurement_dict_aliases;
            IF v_aliases < 157 THEN
                RAISE EXCEPTION
                    'procurement_dict_aliases : % lignes · attendu ≥ 157',
                    v_aliases;
            END IF;

            -- canonical_slug peuplé
            SELECT COUNT(*) INTO v_slug_ok
            FROM couche_b.procurement_dict_items
            WHERE canonical_slug IS NOT NULL;
            IF v_slug_ok < 51 THEN
                RAISE EXCEPTION
                    'canonical_slug NULL sur % items', 51 - v_slug_ok;
            END IF;

            RAISE NOTICE
                'M6 OK · % items · % aliases · slugs complets',
                v_items, v_aliases;
        END $$;
    """)


def downgrade() -> None:
    # Vues recréées
    op.execute("DROP VIEW IF EXISTS public.dict_aliases;")
    op.execute("DROP VIEW IF EXISTS public.dict_items;")

    # Index ajoutés
    op.execute(
        "DROP INDEX IF EXISTS couche_b.idx_dict_aliases_trgm;"
    )
    op.execute(
        "DROP INDEX IF EXISTS couche_b.idx_dict_items_trgm;"
    )
    op.execute(
        "DROP INDEX IF EXISTS couche_b.idx_dict_items_active;"
    )
    op.execute(
        "DROP INDEX IF EXISTS couche_b.idx_dict_items_review;"
    )
    op.execute(
        "DROP INDEX IF EXISTS couche_b.uq_dict_items_canonical_slug;"
    )
    op.execute(
        "DROP INDEX IF EXISTS couche_b.idx_dict_proposals_pending;"
    )

    # Table créée
    op.execute(
        "DROP TABLE IF EXISTS couche_b.dict_proposals;"
    )

    # Colonnes ALTER TABLE : rollback = backup Railway (PIÈGE-04)
    # Les colonnes ajoutées à procurement_dict_items
    # et dict_collision_log ne sont pas retirées
    # pour éviter la perte des données enrichies
