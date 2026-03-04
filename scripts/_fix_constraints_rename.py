"""Reapplique les renames contraintes/indexes vi_ vers vendors_ sur la table vendors."""
import psycopg, os

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
SQL = """
DO $$
BEGIN
    -- RENAME PK
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='public' AND table_name='vendors'
          AND constraint_name='vendor_identities_pkey'
    ) THEN
        ALTER TABLE vendors RENAME CONSTRAINT vendor_identities_pkey TO vendors_pkey;
        RAISE NOTICE 'RENAME vendor_identities_pkey -> vendors_pkey';
    END IF;

    -- RENAME fingerprint UNIQUE
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='public' AND table_name='vendors'
          AND constraint_name='vendor_identities_fingerprint_key'
    ) THEN
        ALTER TABLE vendors RENAME CONSTRAINT vendor_identities_fingerprint_key TO vendors_fingerprint_key;
        RAISE NOTICE 'RENAME vendor_identities_fingerprint_key -> vendors_fingerprint_key';
    END IF;

    -- RENAME vendor_id UNIQUE
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='public' AND table_name='vendors'
          AND constraint_name='vendor_identities_vendor_id_key'
    ) THEN
        ALTER TABLE vendors RENAME CONSTRAINT vendor_identities_vendor_id_key TO vendors_vendor_id_key;
        RAISE NOTICE 'RENAME vendor_identities_vendor_id_key -> vendors_vendor_id_key';
    END IF;

    -- RENAME vcrn UNIQUE
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='public' AND table_name='vendors'
          AND constraint_name='vendor_identities_vcrn_key'
    ) THEN
        ALTER TABLE vendors RENAME CONSTRAINT vendor_identities_vcrn_key TO vendors_vcrn_key;
        RAISE NOTICE 'RENAME vendor_identities_vcrn_key -> vendors_vcrn_key';
    END IF;

    -- RENAME uq_vi_canonical_name
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='public' AND table_name='vendors'
          AND constraint_name='uq_vi_canonical_name'
    ) THEN
        ALTER TABLE vendors RENAME CONSTRAINT uq_vi_canonical_name TO uq_vendors_canonical_name;
        RAISE NOTICE 'RENAME uq_vi_canonical_name -> uq_vendors_canonical_name';
    END IF;

    -- RENAME idx_vi_canonical
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname='public' AND tablename='vendors' AND indexname='idx_vi_canonical'
    ) THEN
        ALTER INDEX idx_vi_canonical RENAME TO idx_vendors_canonical;
        RAISE NOTICE 'RENAME idx_vi_canonical -> idx_vendors_canonical';
    END IF;

    -- RENAME idx_vi_verification
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname='public' AND tablename='vendors' AND indexname='idx_vi_verification'
    ) THEN
        ALTER INDEX idx_vi_verification RENAME TO idx_vendors_verification;
        RAISE NOTICE 'RENAME idx_vi_verification -> idx_vendors_verification';
    END IF;

END $$;
"""

with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute(SQL)
        print("OK: renames appliques")
