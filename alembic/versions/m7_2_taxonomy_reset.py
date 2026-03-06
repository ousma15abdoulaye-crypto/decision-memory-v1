"""
alembic/versions/m7_2_taxonomy_reset.py

M7.2 Taxonomy Reset · Hierarchie L1/L2/L3 enterprise grade
Architecture : couche_b · ADD ONLY · zero DROP en prod

Tables creees :
  couche_b.taxo_l1_domains      -> 15 domaines stables
  couche_b.taxo_l2_families     -> familles par domaine
  couche_b.taxo_l3_subfamilies  -> sous-familles par famille
  couche_b.taxo_proposals_v2    -> propositions LLM · append-only

Colonnes ajoutees a procurement_dict_items :
  domain_id          L1 FK
  family_l2_id       L2 FK
  subfamily_id       L3 FK
  taxo_version       VARCHAR DEFAULT NULL
  taxo_validated     BOOLEAN DEFAULT FALSE
  taxo_validated_by  TEXT
  taxo_validated_at  TIMESTAMPTZ

REGLE-T04 : legacy procurement_dict_families conservee intacte
REGLE-12  : op.execute("SQL brut") uniquement
REGLE-41  : import sqlalchemy interdit
PIEGE-09  : down_revision = alembic heads reel · confirme probe T1
"""

from alembic import op

revision = "m7_2_taxonomy_reset"
down_revision = "m6_dictionary_build"
branch_labels = None
depends_on = None


def _add_col(schema, table, column, definition):
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
    # L1 · Domaines
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.taxo_l1_domains (
            domain_id   TEXT        PRIMARY KEY,
            label_fr    TEXT        NOT NULL,
            label_en    TEXT,
            description TEXT,
            sort_order  INTEGER     NOT NULL DEFAULT 99,
            active      BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # ------------------------------------------------------------------
    # L2 · Familles
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.taxo_l2_families (
            family_l2_id TEXT        PRIMARY KEY,
            domain_id    TEXT        NOT NULL
                                     REFERENCES
                                     couche_b.taxo_l1_domains(domain_id)
                                     ON DELETE RESTRICT,
            label_fr     TEXT        NOT NULL,
            label_en     TEXT,
            description  TEXT,
            sort_order   INTEGER     NOT NULL DEFAULT 99,
            active       BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_taxo_l2_domain
        ON couche_b.taxo_l2_families(domain_id);
    """)

    # ------------------------------------------------------------------
    # L3 · Sous-familles
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.taxo_l3_subfamilies (
            subfamily_id TEXT        PRIMARY KEY,
            family_l2_id TEXT        NOT NULL
                                     REFERENCES
                                     couche_b.taxo_l2_families(family_l2_id)
                                     ON DELETE RESTRICT,
            label_fr     TEXT        NOT NULL,
            label_en     TEXT,
            description  TEXT,
            sort_order   INTEGER     NOT NULL DEFAULT 99,
            active       BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_taxo_l3_family
        ON couche_b.taxo_l3_subfamilies(family_l2_id);
    """)

    # ------------------------------------------------------------------
    # Colonnes L1/L2/L3 sur procurement_dict_items
    # ------------------------------------------------------------------
    _add_col(
        "couche_b",
        "procurement_dict_items",
        "domain_id",
        "TEXT REFERENCES couche_b.taxo_l1_domains(domain_id)",
    )

    _add_col(
        "couche_b",
        "procurement_dict_items",
        "family_l2_id",
        "TEXT REFERENCES couche_b.taxo_l2_families(family_l2_id)",
    )

    _add_col(
        "couche_b",
        "procurement_dict_items",
        "subfamily_id",
        "TEXT REFERENCES couche_b.taxo_l3_subfamilies(subfamily_id)",
    )

    _add_col("couche_b", "procurement_dict_items", "taxo_version", "TEXT")

    _add_col(
        "couche_b",
        "procurement_dict_items",
        "taxo_validated",
        "BOOLEAN NOT NULL DEFAULT FALSE",
    )

    _add_col("couche_b", "procurement_dict_items", "taxo_validated_by", "TEXT")

    _add_col("couche_b", "procurement_dict_items", "taxo_validated_at", "TIMESTAMPTZ")

    # ------------------------------------------------------------------
    # taxo_proposals_v2 · append-only · REGLE-T02
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS couche_b.taxo_proposals_v2 (
            id             UUID        PRIMARY KEY
                                       DEFAULT gen_random_uuid(),
            item_id        TEXT        NOT NULL
                                       REFERENCES
                                       couche_b.procurement_dict_items(item_id)
                                       ON DELETE RESTRICT,
            domain_id      TEXT        NOT NULL
                                       REFERENCES
                                       couche_b.taxo_l1_domains(domain_id),
            family_l2_id   TEXT        NOT NULL
                                       REFERENCES
                                       couche_b.taxo_l2_families(family_l2_id),
            subfamily_id   TEXT        NOT NULL
                                       REFERENCES
                                       couche_b.taxo_l3_subfamilies(subfamily_id),
            confidence     NUMERIC(5,4) NOT NULL
                                        CHECK (confidence BETWEEN 0.0 AND 1.0),
            reason         TEXT        NOT NULL,
            model          TEXT        NOT NULL,
            prompt_hash    TEXT        NOT NULL,
            taxo_version   TEXT        NOT NULL DEFAULT '2.0.0',
            status         TEXT        NOT NULL DEFAULT 'pending'
                                       CHECK (status IN (
                                           'pending',
                                           'flagged',
                                           'approved',
                                           'rejected'
                                       )),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT taxo_proposals_v2_idempotent
                UNIQUE (item_id, taxo_version, model, prompt_hash)
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_taxo_prop_status
        ON couche_b.taxo_proposals_v2(status);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_taxo_prop_item
        ON couche_b.taxo_proposals_v2(item_id);
    """)

    # ------------------------------------------------------------------
    # Vues publiques miroir
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE VIEW public.taxo_l1_domains AS
        SELECT * FROM couche_b.taxo_l1_domains;
    """)
    op.execute("""
        CREATE OR REPLACE VIEW public.taxo_l2_families AS
        SELECT * FROM couche_b.taxo_l2_families;
    """)
    op.execute("""
        CREATE OR REPLACE VIEW public.taxo_l3_subfamilies AS
        SELECT * FROM couche_b.taxo_l3_subfamilies;
    """)

    # ------------------------------------------------------------------
    # Verification fail-loud
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        DECLARE v INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v
            FROM information_schema.tables
            WHERE table_schema = 'couche_b'
              AND table_name   = 'taxo_l1_domains';
            IF v = 0 THEN
                RAISE EXCEPTION 'taxo_l1_domains absent · M7.2 KO';
            END IF;

            SELECT COUNT(*) INTO v
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_items'
              AND column_name  = 'domain_id';
            IF v = 0 THEN
                RAISE EXCEPTION 'domain_id absent de procurement_dict_items · M7.2 KO';
            END IF;

            RAISE NOTICE 'Migration M7.2 OK';
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.taxo_l3_subfamilies;")
    op.execute("DROP VIEW IF EXISTS public.taxo_l2_families;")
    op.execute("DROP VIEW IF EXISTS public.taxo_l1_domains;")
    op.execute("DROP TABLE IF EXISTS couche_b.taxo_proposals_v2;")
    op.execute("DROP TABLE IF EXISTS couche_b.taxo_l3_subfamilies;")
    op.execute("DROP TABLE IF EXISTS couche_b.taxo_l2_families;")
    op.execute("DROP TABLE IF EXISTS couche_b.taxo_l1_domains;")
