"""
Réconciliation structurelle vendor_identities — V4.1.0 enrichie terrain.

Revision ID: m4_patch_a_vendor_structure_v410
Revises: 043_vendor_activity_badge
Create Date: 2026-03-02

OPTION B CTO (2026-03-02) :
  Table vendor_identities conserve son nom.
  Une table 'vendors' legacy (4 colonnes, FK vers geo_master / market_signals)
  préexiste hors alembic — collision de nommage → RENAME exclu.
  Ce patch enrichit vendor_identities en place.

NOTES ARCHITECTURE :
  Ce patch est hors séquence numérique gelée.
  044 = réservé M11 · 045 = réservé M14 (V4.1.0 Partie XI).

  INACTIVE → registered (PAS suspended).
  suspended = acte explicite de compliance · jamais auto-mappé terrain.

  Extension pg_trgm déjà créée en amont (ex: 005_add_couche_b) ;
  hors scope ici = index GIN trigram sur canonical_name / matching vendor.

  Probe P3 garantit l'absence de doublons name_normalized
  avant que cette migration pose UNIQUE(canonical_name).
"""

from alembic import op

revision = "m4_patch_a_vendor_structure_v410"
down_revision = "043_vendor_activity_badge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Garde défensive : vendor_identities doit exister
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'vendor_identities'
            ) THEN
                RAISE EXCEPTION
                    'vendor_identities introuvable · '
                    'migration impossible · vérifier état DB';
            END IF;
            -- Garde doublon canonical_name (défense en profondeur)
            -- canonical_name = name_normalized || '|' || region_code
            -- On vérifie donc les doublons sur (name_normalized, region_code)
            IF EXISTS (
                SELECT name_normalized, region_code
                FROM vendor_identities
                GROUP BY name_normalized, region_code
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Doublons (name_normalized, region_code) détectés · '
                    'UNIQUE(canonical_name) impossible · '
                    'résoudre avant migration';
            END IF;
        END $$;
    """)

    # ── 1. canonical_name (V4.1.0) ───────────────────────────
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS canonical_name TEXT;
    """)
    op.execute("""
        UPDATE vendor_identities
        SET canonical_name = name_normalized || '|' || region_code
        WHERE canonical_name IS NULL;
    """)
    op.execute("""
        ALTER TABLE vendor_identities
        ALTER COLUMN canonical_name SET NOT NULL;
    """)
    op.execute("""
        ALTER TABLE vendor_identities
        ADD CONSTRAINT uq_vi_canonical_name
        UNIQUE (canonical_name);
    """)

    # ── 2. aliases (V4.1.0) ──────────────────────────────────
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS aliases TEXT[]
        NOT NULL DEFAULT '{}';
    """)

    # ── 3. nif · rccm · rib (V4.1.0 · null M4 · peuplés M13+)
    for col in ["nif", "rccm", "rib"]:
        op.execute(
            f"ALTER TABLE vendor_identities "
            f"ADD COLUMN IF NOT EXISTS {col} TEXT;"
        )

    # ── 4. verification_status (V4.1.0) ──────────────────────
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS verification_status TEXT
            NOT NULL DEFAULT 'registered'
            CONSTRAINT chk_vi_verification_status
            CHECK (verification_status IN (
                'registered', 'qualified', 'approved', 'suspended'
            ));
    """)
    # DÉCISION CTO :
    #   VERIFIED_ACTIVE  → qualified
    #   UNVERIFIED       → registered  (DEFAULT · déjà appliqué)
    #   INACTIVE         → registered  (PAS suspended)
    #   GHOST_SUSPECTED  → registered  (PAS suspended)
    #   suspended = acte explicite compliance · jamais auto-mappé terrain
    op.execute("""
        UPDATE vendor_identities
        SET verification_status = 'qualified'
        WHERE activity_status = 'VERIFIED_ACTIVE';
    """)

    # ── 5. vcrn (V4.1.0 · généré M13+) ──────────────────────
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS vcrn TEXT UNIQUE;
    """)

    # ── 6. zones_covered · category_ids (peuplés M5+/M6+) ───
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS zones_covered UUID[]
        NOT NULL DEFAULT '{}';
    """)
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS category_ids UUID[]
        NOT NULL DEFAULT '{}';
    """)

    # ── 7. Champs compliance (V4.1.0 · peuplés M13+) ─────────
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS has_sanctions_cert BOOLEAN
        NOT NULL DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS has_sci_conditions BOOLEAN
        NOT NULL DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS key_personnel_verified BOOLEAN
        NOT NULL DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS suspension_reason TEXT;
    """)
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
    """)

    # ── 8. Renommer last_verified_at → verified_at (V4.1.0) ──
    op.execute("""
        ALTER TABLE vendor_identities
        RENAME COLUMN last_verified_at TO verified_at;
    """)

    # ── 9. Index Couche B ─────────────────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vi_verification
        ON vendor_identities(verification_status);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vi_canonical
        ON vendor_identities(canonical_name);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_vi_verification;")
    op.execute("DROP INDEX IF EXISTS idx_vi_canonical;")
    op.execute("""
        ALTER TABLE vendor_identities
        RENAME COLUMN verified_at TO last_verified_at;
    """)
    for col in [
        "suspended_at", "suspension_reason",
        "key_personnel_verified", "has_sci_conditions",
        "has_sanctions_cert", "category_ids", "zones_covered",
        "vcrn", "verification_status",
        "rib", "rccm", "nif",
        "aliases", "canonical_name",
    ]:
        op.execute(
            f"ALTER TABLE vendor_identities DROP COLUMN IF EXISTS {col};"
        )
