"""098 — Compte admin principal : email propriétaire (mandat explicite).

Revision ID: 098_primary_admin_email_owner_mandate
Revises: 097_fix_test_user_role_supply_chain

ADMIN_EMAIL_TARGET (exact, aucune substitution) :
``ousma15abdoulaye@gmail.com``

Règles
------
- Le compte joignable avec cet email devient l’admin principal (role legacy
  ``admin``, ``is_superuser`` TRUE, actif).
- Si ``username = 'admin'`` (seed 004) et un autre utilisateur portent déjà
  l’email cible : le hash mot de passe du seed est copié vers la ligne cible,
  celle-ci reçoit ``username = 'admin'`` ; l’ancienne ligne seed est renommée
  (username / email uniques) et rétrogradée viewer — les tests CI gardent
  ``admin`` / ``admin123`` sur l’identité admin.
- Si seul le seed existe : mise à jour de l’email vers la cible.
- Si seule une ligne avec l’email cible existe : promotion admin + superuser.

REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "098_primary_admin_email_owner_mandate"
down_revision = "097_fix_test_user_role_supply_chain"
branch_labels = None
depends_on = None

_ADMIN_EMAIL_TARGET = "ousma15abdoulaye@gmail.com"


def upgrade() -> None:
    op.execute(f"""
        DO $$
        DECLARE
            tmail TEXT := '{_ADMIN_EMAIL_TARGET}';
            aid INTEGER;
            ua INTEGER;
            ug INTEGER;
            pwd TEXT;
            vid INTEGER;
        BEGIN
            SELECT id INTO aid FROM roles WHERE name = 'admin' LIMIT 1;
            IF aid IS NULL THEN
                RAISE NOTICE '098 skip — rôle legacy admin absent';
                RETURN;
            END IF;

            SELECT id INTO ua FROM users WHERE username = 'admin' LIMIT 1;
            SELECT id INTO ug FROM users WHERE lower(trim(email)) = lower(tmail) LIMIT 1;

            IF ua IS NULL AND ug IS NULL THEN
                RAISE NOTICE '098 skip — ni seed admin ni email cible';
                RETURN;
            END IF;

            SELECT id INTO vid FROM roles WHERE name = 'viewer' LIMIT 1;
            IF vid IS NULL THEN
                vid := aid;
            END IF;

            IF ua IS NOT NULL AND ug IS NOT NULL AND ua <> ug THEN
                SELECT hashed_password INTO pwd FROM users WHERE id = ua;
                UPDATE users
                SET username = 'retired_seed_' || id::text,
                    email = 'retired_seed_' || id::text || '@dms.local',
                    is_superuser = FALSE,
                    role_id = vid
                WHERE id = ua;

                UPDATE users
                SET username = 'admin',
                    email = tmail,
                    hashed_password = COALESCE(pwd, hashed_password),
                    is_superuser = TRUE,
                    is_active = TRUE,
                    role_id = aid
                WHERE id = ug;

                RAISE NOTICE '098 OK — fusion seed admin → email cible (id=%)', ug;

            ELSIF ua IS NOT NULL THEN
                UPDATE users
                SET email = tmail,
                    is_superuser = TRUE,
                    is_active = TRUE,
                    role_id = aid
                WHERE id = ua;
                RAISE NOTICE '098 OK — seed admin email → cible (id=%)', ua;

            ELSIF ug IS NOT NULL THEN
                UPDATE users
                SET is_superuser = TRUE,
                    is_active = TRUE,
                    role_id = aid
                WHERE id = ug;
                RAISE NOTICE '098 OK — promotion email cible seul (id=%)', ug;
            END IF;
        END;
        $$
        """)  # noqa: S608 — SQL migration ; email constant mandat propriétaire


def downgrade() -> None:
    """Best-effort : ne pas casser les bases où l’email a toujours été la cible."""
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE '098 downgrade — no-op (état admin/email non réversible automatiquement)';
        END;
        $$
        """)
