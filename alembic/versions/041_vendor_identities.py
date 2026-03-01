"""
vendor_identities — M4 Vendor Importer Mali

Revision ID: 041_vendor_identities
Revises: 040_geo_master_mali
Create Date: 2026-03-01

Règles :
- SQL brut uniquement · zéro autogenerate
- Pas de GENERATED COLUMN · normalisation applicative Python (normalizer.py)
- Pas de séquences SQL · génération ID en couche repository (repository.py)
- Garde défensive fn_set_updated_at() en tête de upgrade()
- IF NOT EXISTS / OR REPLACE sur tous les DDL pour idempotence prod
"""

from alembic import op

revision = "041_vendor_identities"
down_revision = "040_geo_master_mali"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Garde défensive — échoue proprement si prérequis absent
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_proc WHERE proname = 'fn_set_updated_at'
            ) THEN
                RAISE EXCEPTION
                    'PREREQUIS MANQUANT : fn_set_updated_at() '
                    'introuvable. Migration 040 requise.';
            END IF;
        END $$;
    """)

    # Extension unaccent — disponibilité confirmée par probe B0.4
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # Table principale
    # zone_normalized = colonne ordinaire · calculée par normalizer.py
    # Pas de GENERATED COLUMN → source de vérité unique = Python
    op.execute("""
        CREATE TABLE IF NOT EXISTS vendor_identities (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            vendor_id        TEXT        NOT NULL UNIQUE,
            fingerprint      TEXT        NOT NULL UNIQUE,
            name_raw         TEXT        NOT NULL,
            name_normalized  TEXT        NOT NULL,
            zone_raw         TEXT,
            zone_normalized  TEXT,
            region_code      TEXT        NOT NULL,
            category_raw     TEXT,
            email            TEXT,
            phone            TEXT,
            email_verified   BOOLEAN     NOT NULL DEFAULT FALSE,
            is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
            source           TEXT        NOT NULL DEFAULT 'MANUAL',
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_vendor_id_format
                CHECK (vendor_id LIKE 'DMS-VND-%'),
            CONSTRAINT chk_region_code
                CHECK (region_code IN (
                    'BKO','MPT','SGO','SKS',
                    'GAO','TBK','MNK','KYS','KLK','INT'
                ))
        );
    """)

    # Index opérationnels
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vendor_region "
        "ON vendor_identities(region_code);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vendor_name_norm "
        "ON vendor_identities(name_normalized);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vendor_zone_norm "
        "ON vendor_identities(zone_normalized);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vendor_active "
        "ON vendor_identities(is_active) "
        "WHERE is_active = TRUE;"
    )

    # Trigger updated_at
    op.execute("""
        CREATE OR REPLACE TRIGGER trg_vendor_updated_at
        BEFORE UPDATE ON vendor_identities
        FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_vendor_updated_at "
        "ON vendor_identities;"
    )
    op.execute("DROP TABLE IF EXISTS vendor_identities CASCADE;")
