"""
Badge activité fournisseur.
Statut de vérification terrain — pas du scoring.

Revision ID: 043_vendor_activity_badge
Revises: 042_vendor_fixes
Create Date: 2026-03-02

Colonnes ajoutées :
  activity_status      : statut activité · valeurs canoniques contraintes
  last_verified_at     : date dernière vérification terrain
  verified_by          : agent ou équipe ayant vérifié
  verification_source  : source de la vérification · valeurs canoniques

DÉCISION CTO :
  Les 102 vendors EXCEL_M4 sont marqués VERIFIED_ACTIVE.
  Ils proviennent de listes SCI de visites terrain réelles.
  La base doit refléter cette vérité opérationnelle.
"""

from alembic import op

revision = "043_vendor_activity_badge"
down_revision = "042_vendor_fixes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Colonne statut activité — valeurs canoniques contraintes
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS activity_status TEXT
            NOT NULL DEFAULT 'UNVERIFIED'
            CONSTRAINT chk_activity_status
            CHECK (activity_status IN (
                'VERIFIED_ACTIVE',
                'UNVERIFIED',
                'INACTIVE',
                'GHOST_SUSPECTED'
            ));
    """)

    # Date dernière vérification terrain
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;
    """)

    # Agent ou équipe ayant vérifié (TEXT libre en M4)
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS verified_by TEXT;
    """)

    # Source de la vérification — valeurs canoniques contraintes
    op.execute("""
        ALTER TABLE vendor_identities
        ADD COLUMN IF NOT EXISTS verification_source TEXT
            CONSTRAINT chk_verification_source
            CHECK (verification_source IN (
                'SCI_FIELD_VISIT',
                'PHONE_CONFIRMATION',
                'DOCUMENT_REVIEW',
                'LEGACY_IMPORT',
                'MANUAL_ENTRY'
            ));
    """)

    # Index filtre badge
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vendor_activity "
        "ON vendor_identities(activity_status);"
    )

    # DÉCISION CTO : les vendors EXCEL_M4 actifs sont VERIFIED_ACTIVE.
    # Ils proviennent de listes SCI de visites terrain réelles.
    op.execute("""
        UPDATE vendor_identities
        SET
            activity_status     = 'VERIFIED_ACTIVE',
            last_verified_at    = '2026-03-01T00:00:00+00:00',
            verified_by         = 'SCI_FIELD_TEAM_MALI',
            verification_source = 'SCI_FIELD_VISIT'
        WHERE source = 'EXCEL_M4'
          AND is_active = TRUE;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_vendor_activity;")
    op.execute("""
        ALTER TABLE vendor_identities
        DROP COLUMN IF EXISTS verification_source,
        DROP COLUMN IF EXISTS verified_by,
        DROP COLUMN IF EXISTS last_verified_at,
        DROP COLUMN IF EXISTS activity_status;
    """)
