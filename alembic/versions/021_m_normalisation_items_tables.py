"""021_m_normalisation_items_tables

M-NORMALISATION-ITEMS — Étape 1 (ADR-0003 §2.2)
- Schéma couche_b + tables procurement dictionary
- Vues public.dict_* pour découplage tests/schéma
- SQL explicite, zéro ORM
"""

from alembic import op

revision = "021_m_normalisation_items_tables"
down_revision = "019_consolidate_ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS couche_b;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS couche_b.procurement_dict_families (
            family_id   TEXT PRIMARY KEY,
            label_fr    TEXT NOT NULL,
            criticite   TEXT NOT NULL
                CHECK (criticite IN ('CRITIQUE','HAUTE','MOYENNE'))
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS couche_b.procurement_dict_units (
            unit_id     TEXT PRIMARY KEY,
            label_fr    TEXT NOT NULL,
            unit_kind   TEXT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS couche_b.procurement_dict_items (
            item_id       TEXT PRIMARY KEY,
            family_id     TEXT NOT NULL
                REFERENCES couche_b.procurement_dict_families(family_id)
                ON DELETE RESTRICT,
            label_fr      TEXT NOT NULL,
            label_en      TEXT NULL,
            default_unit  TEXT NOT NULL
                REFERENCES couche_b.procurement_dict_units(unit_id)
                ON DELETE RESTRICT,
            active        BOOLEAN NOT NULL DEFAULT TRUE
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS couche_b.procurement_dict_aliases (
            alias_id          BIGSERIAL PRIMARY KEY,
            item_id           TEXT NOT NULL
                REFERENCES couche_b.procurement_dict_items(item_id)
                ON DELETE CASCADE,
            alias_raw         TEXT NOT NULL,
            normalized_alias  TEXT NOT NULL,
            source            TEXT NOT NULL,
            CONSTRAINT uq_procurement_dict_normalized_alias
                UNIQUE (normalized_alias)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS couche_b.procurement_dict_unit_conversions (
            from_unit  TEXT NOT NULL
                REFERENCES couche_b.procurement_dict_units(unit_id)
                ON DELETE RESTRICT,
            to_unit    TEXT NOT NULL
                REFERENCES couche_b.procurement_dict_units(unit_id)
                ON DELETE RESTRICT,
            factor     NUMERIC NOT NULL,
            CONSTRAINT pk_procurement_dict_unit_conversions
                PRIMARY KEY (from_unit, to_unit)
        );
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW public.dict_families AS
        SELECT * FROM couche_b.procurement_dict_families;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW public.dict_units AS
        SELECT * FROM couche_b.procurement_dict_units;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW public.dict_items AS
        SELECT * FROM couche_b.procurement_dict_items;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW public.dict_aliases AS
        SELECT * FROM couche_b.procurement_dict_aliases;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW public.dict_unit_conversions AS
        SELECT * FROM couche_b.procurement_dict_unit_conversions;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.dict_unit_conversions;")
    op.execute("DROP VIEW IF EXISTS public.dict_aliases;")
    op.execute("DROP VIEW IF EXISTS public.dict_items;")
    op.execute("DROP VIEW IF EXISTS public.dict_units;")
    op.execute("DROP VIEW IF EXISTS public.dict_families;")
    op.execute(
        "DROP TABLE IF EXISTS couche_b.procurement_dict_unit_conversions;"
    )
    op.execute("DROP TABLE IF EXISTS couche_b.procurement_dict_aliases;")
    op.execute("DROP TABLE IF EXISTS couche_b.procurement_dict_items;")
    op.execute("DROP TABLE IF EXISTS couche_b.procurement_dict_units;")
    op.execute("DROP TABLE IF EXISTS couche_b.procurement_dict_families;")
