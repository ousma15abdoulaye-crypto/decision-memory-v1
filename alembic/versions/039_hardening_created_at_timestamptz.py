"""hardening_created_at_timestamptz

Revision ID: 039
Revises: 038_audit_hash_chain
Create Date: 2026-02-26

Scope M2B : conversion users.created_at TEXT -> TIMESTAMPTZ
Décision  : ADR-M2B-001_hardening_db_scope.md
Formulation : USING created_at::timestamp AT TIME ZONE 'UTC'
             déterministe entre environnements (pas de dépendance TimeZone session)

Note downgrade : le downgrade restaure users.created_at en TEXT via to_char.
Le format restitué est 'YYYY-MM-DDThh:mm:ss.uuuuuu' pour toutes les lignes.
Les valeurs originalement en format date-only ('2026-02-21') seront restituées
comme '2026-02-21T00:00:00.000000' — précision non récupérable après upgrade.
"""

from alembic import op

revision = "039"
down_revision = "038_audit_hash_chain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
          ALTER COLUMN created_at TYPE TIMESTAMPTZ
          USING created_at::timestamp AT TIME ZONE 'UTC';
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
          ALTER COLUMN created_at TYPE TEXT
          USING to_char(
            created_at AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US'
          );
    """)
