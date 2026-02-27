"""037 — Security Baseline M1

Révision : 037_security_baseline
Parent   : 036_db_hardening

Périmètre :
  1. users          — colonnes additives uniquement (role TEXT, organization TEXT)
                     Aucune touche à id, role_id, hashed_password, username,
                     is_superuser, last_login, created_at — legacy préservé intact.
  2. token_blacklist — CREATE TABLE IF NOT EXISTS + 2 index + fn_cleanup_expired_tokens()
  3. audit_log       — ZÉRO touche (réservé 037_audit_hash_chain / M1B)

Règles respectées :
  RÈGLE-12  SQL brut op.execute() uniquement — zéro autogenerate
  RÈGLE-17  1 test minimum par invariant DB (voir tests/auth/)
  ADR-M1-001  Stratégie JWT
  ADR-M1-002  Matrice RBAC
"""

from alembic import op

revision = "037_security_baseline"
down_revision = "036_db_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. users — colonnes additives uniquement (RÈGLE : jamais DROP, jamais ALTER TYPE)
    # Approche en 4 étapes pour être idempotente quelle que soit la situation initiale :
    #   - colonne absente      → ADD COLUMN crée avec DEFAULT
    #   - colonne existe NULL  → UPDATE backfill + SET NOT NULL + CHECK
    #   - colonne existe déjà  → opérations IF NOT EXISTS / idempotentes
    op.execute("""
        ALTER TABLE users
          ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'viewer';
    """)
    # Backfill NULLs éventuels avant SET NOT NULL
    op.execute("""
        UPDATE users SET role = 'viewer' WHERE role IS NULL;
    """)
    op.execute("""
        ALTER TABLE users ALTER COLUMN role SET NOT NULL;
    """)
    op.execute("""
        ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer';
    """)
    # CHECK constraint — idempotente via DO block
    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.constraint_column_usage
            WHERE constraint_name = 'chk_users_role'
              AND table_name = 'users'
          ) THEN
            ALTER TABLE users
              ADD CONSTRAINT chk_users_role
              CHECK (role IN ('admin','manager','buyer','viewer','auditor'));
          END IF;
        END $$;
    """)
    op.execute("""
        ALTER TABLE users
          ADD COLUMN IF NOT EXISTS organization TEXT;
    """)

    # ── 2. token_blacklist — CREATE TABLE IF NOT EXISTS
    # Doctrine (ADR-M1-001) : table OPÉRATIONNELLE, non append-only.
    # Les tokens expirés sont supprimés par fn_cleanup_expired_tokens().
    # token_blacklist n'est PAS une table d'audit.
    # L'historique de révocation = audit_log (M1B).
    op.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token_jti  TEXT NOT NULL UNIQUE,
            revoked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL
        );
    """)

    # ── 3. Index token_blacklist
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti
          ON token_blacklist(token_jti);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires
          ON token_blacklist(expires_at);
    """)

    # ── 4. fn_cleanup_expired_tokens
    # Appelée par job applicatif (pas par cron DB).
    # Supprime uniquement les tokens dont expires_at < now().
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_cleanup_expired_tokens()
        RETURNS INTEGER LANGUAGE plpgsql AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM token_blacklist
            WHERE expires_at < now();
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_cleanup_expired_tokens();")
    op.execute("DROP TABLE IF EXISTS token_blacklist;")
    # Colonnes users ajoutées : ne pas DROP en downgrade
    # (données existantes pourraient être présentes — doctrine M0B)
