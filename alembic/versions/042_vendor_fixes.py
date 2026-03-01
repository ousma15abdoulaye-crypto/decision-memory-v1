"""
Correctifs techniques M4 post-merge.

Revision ID: 042_vendor_fixes
Revises: 041_vendor_identities
Create Date: 2026-03-02

Fixes :
  FIX-1 : CHECK vendor_id étendu de LIKE à regex complète
  FIX-2 : Trigger rebuilt proprement sans OR REPLACE
  FIX-3 : Extension unaccent retirée (normalisation Python uniquement)
"""

from alembic import op

revision = "042_vendor_fixes"
down_revision = "041_vendor_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FIX-1 : Regex complète sur vendor_id
    # Remplace LIKE 'DMS-VND-%' insuffisant
    op.execute(
        "ALTER TABLE vendor_identities "
        "DROP CONSTRAINT IF EXISTS chk_vendor_id_format;"
    )
    op.execute(
        "ALTER TABLE vendor_identities "
        "ADD CONSTRAINT chk_vendor_id_format "
        "CHECK (vendor_id ~ '^DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]$');"
    )

    # FIX-2 : Trigger rebuilt sans OR REPLACE (PG12+ compatible)
    op.execute("DROP TRIGGER IF EXISTS trg_vendor_updated_at " "ON vendor_identities;")
    op.execute("""
        CREATE TRIGGER trg_vendor_updated_at
            BEFORE UPDATE ON vendor_identities
            FOR EACH ROW
            EXECUTE FUNCTION fn_set_updated_at();
    """)

    # FIX-3 : Supprimer unaccent si présente
    # Non utilisée en M4 · normalisation applicative Python
    # RESTRICT : ne pas supprimer si d'autres objets en dépendent
    op.execute("DROP EXTENSION IF EXISTS unaccent RESTRICT;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_vendor_updated_at " "ON vendor_identities;")
    op.execute(
        "ALTER TABLE vendor_identities "
        "DROP CONSTRAINT IF EXISTS chk_vendor_id_format;"
    )
    # Restaure la contrainte originale LIKE
    op.execute(
        "ALTER TABLE vendor_identities "
        "ADD CONSTRAINT chk_vendor_id_format "
        "CHECK (vendor_id LIKE 'DMS-VND-%');"
    )
    # Trigger original — idempotent (drop + create)
    op.execute("""
        CREATE OR REPLACE TRIGGER trg_vendor_updated_at
            BEFORE UPDATE ON vendor_identities
            FOR EACH ROW
            EXECUTE FUNCTION fn_set_updated_at();
    """)
