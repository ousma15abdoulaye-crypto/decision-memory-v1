"""geo_master_mali

Revision ID: 040_geo_master_mali
Revises: 039_created_at_timestamptz
Create Date: 2026-03-01

Scope M3 : création du référentiel géographique canonique Mali (7 tables).
Schéma agnostique — aucun DEFAULT organisationnel.
NOTE-ARCH-M3-001 : schéma normalisé 7 tables remplace geo_master monolithique.
SQL brut uniquement — zéro autogenerate (RÈGLE-12).
"""

from alembic import op

revision = "040_geo_master_mali"
down_revision = "039_created_at_timestamptz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Tables géographiques ──────────────────────────────────────────────

    op.execute("""
        CREATE TABLE geo_countries (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            iso2        CHAR(2)  NOT NULL UNIQUE,
            iso3        CHAR(3)  NOT NULL UNIQUE,
            name_fr     TEXT     NOT NULL,
            name_en     TEXT     NOT NULL,
            is_active   BOOLEAN  NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE geo_regions (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            country_id  UUID NOT NULL REFERENCES geo_countries(id),
            code        TEXT NOT NULL,
            name_fr     TEXT NOT NULL,
            name_en     TEXT,
            capitale    TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (country_id, code)
        )
    """)

    op.execute("""
        CREATE TABLE geo_cercles (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            region_id   UUID NOT NULL REFERENCES geo_regions(id),
            code        TEXT NOT NULL,
            name_fr     TEXT NOT NULL,
            capitale    TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (region_id, code)
        )
    """)

    op.execute("""
        CREATE TABLE geo_communes (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cercle_id    UUID NOT NULL REFERENCES geo_cercles(id),
            code_instat  TEXT NOT NULL UNIQUE,
            name_fr      TEXT NOT NULL,
            type_commune TEXT NOT NULL
                         CHECK (type_commune IN ('urbaine', 'rurale')),
            chef_lieu    TEXT,
            is_active    BOOLEAN NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE geo_localites (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            commune_id     UUID NOT NULL REFERENCES geo_communes(id),
            name_fr        TEXT NOT NULL,
            type_localite  TEXT NOT NULL
                           CHECK (type_localite IN (
                               'village', 'quartier', 'hameau',
                               'site_deplacement', 'site_humanitaire', 'autre'
                           )),
            latitude       NUMERIC(10, 7),
            longitude      NUMERIC(10, 7),
            is_active      BOOLEAN NOT NULL DEFAULT TRUE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE geo_zones_operationnelles (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code              TEXT NOT NULL,
            name_fr           TEXT NOT NULL,
            description       TEXT,
            organisation_code TEXT NOT NULL,
            type_zone         TEXT NOT NULL
                              CHECK (type_zone IN (
                                  'intervention', 'logistique',
                                  'securite', 'administrative'
                              )),
            is_active         BOOLEAN NOT NULL DEFAULT TRUE,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (code, organisation_code)
        )
    """)

    op.execute("""
        CREATE TABLE geo_zone_commune_mapping (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            zone_id     UUID NOT NULL REFERENCES geo_zones_operationnelles(id),
            commune_id  UUID NOT NULL REFERENCES geo_communes(id),
            valid_from  TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_until TIMESTAMPTZ,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (zone_id, commune_id, valid_from)
        )
    """)

    # ── 2. Index ─────────────────────────────────────────────────────────────
    # UNIQUE(code_instat) sur geo_communes crée déjà l'index utile — pas d'index redondant.

    op.execute("CREATE INDEX idx_geo_regions_country ON geo_regions(country_id)")
    op.execute("CREATE INDEX idx_geo_cercles_region ON geo_cercles(region_id)")
    op.execute("CREATE INDEX idx_geo_communes_cercle ON geo_communes(cercle_id)")
    op.execute("CREATE INDEX idx_geo_localites_commune ON geo_localites(commune_id)")
    op.execute("""
        CREATE INDEX idx_geo_localites_coords
            ON geo_localites(latitude, longitude)
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX idx_zone_commune_active
            ON geo_zone_commune_mapping(zone_id, commune_id)
            WHERE valid_until IS NULL
    """)

    # ── 3. Fonction updated_at ────────────────────────────────────────────────

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$
    """)

    # ── 4. Triggers updated_at ────────────────────────────────────────────────

    for table in (
        "geo_countries",
        "geo_regions",
        "geo_cercles",
        "geo_communes",
        "geo_localites",
        "geo_zones_operationnelles",
    ):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()
        """)


def downgrade() -> None:
    # Ordre : enfants avant parents, fonction en dernier
    op.execute("DROP TABLE IF EXISTS geo_zone_commune_mapping CASCADE")
    op.execute("DROP TABLE IF EXISTS geo_localites CASCADE")
    op.execute("DROP TABLE IF EXISTS geo_communes CASCADE")
    op.execute("DROP TABLE IF EXISTS geo_cercles CASCADE")
    op.execute("DROP TABLE IF EXISTS geo_regions CASCADE")
    op.execute("DROP TABLE IF EXISTS geo_zones_operationnelles CASCADE")
    op.execute("DROP TABLE IF EXISTS geo_countries CASCADE")
    op.execute("DROP FUNCTION IF EXISTS fn_set_updated_at() CASCADE")
