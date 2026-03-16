"""048_vendors_sensitive_data

Revision ID: 048_vendors_sensitive_data
Revises: 047_couche_a_service_columns
Create Date: 2026-03-15

ADR-014 — Registre vendor sécurisé.
Chiffrement AES-256-GCM pour NIF, RCCM, phone, email.
Tokens de référence dans Label Studio — valeurs jamais exposées.
"""
from alembic import op

revision = "048_vendors_sensitive_data"
down_revision = "047_couche_a_service_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Table principale des données sensibles chiffrées
    op.execute("""
        CREATE TABLE IF NOT EXISTS vendors_sensitive_data (
            id                      UUID PRIMARY KEY
                                    DEFAULT gen_random_uuid(),
            token                   TEXT NOT NULL UNIQUE,
            field_type              TEXT NOT NULL
                                    CHECK (field_type IN (
                                        'nif', 'rccm', 'phone', 'email'
                                    )),
            encrypted_value         TEXT NOT NULL,
            supplier_name_normalized TEXT NOT NULL,
            case_id                 TEXT,
            annotation_task_id      TEXT,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            accessed_at             TIMESTAMPTZ,
            accessed_by             TEXT
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vsd_token
            ON vendors_sensitive_data(token);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vsd_supplier
            ON vendors_sensitive_data(supplier_name_normalized);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vsd_field_type
            ON vendors_sensitive_data(field_type);
    """)

    # Table de validité documents (quitus, certificat)
    op.execute("""
        CREATE TABLE IF NOT EXISTS vendors_doc_validity (
            id                          UUID PRIMARY KEY
                                        DEFAULT gen_random_uuid(),
            supplier_name_normalized    TEXT NOT NULL,
            case_id                     TEXT,
            doc_type                    TEXT NOT NULL
                                        CHECK (doc_type IN (
                                            'quitus_fiscal',
                                            'cert_non_faillite',
                                            'rccm_validity',
                                            'other'
                                        )),
            encrypted_date              TEXT NOT NULL,
            is_valid                    BOOLEAN NOT NULL,
            expires_in_days             INTEGER NOT NULL,
            computed_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
            annotation_task_id          TEXT,
            CONSTRAINT uq_vendor_doc
                UNIQUE (supplier_name_normalized, doc_type, case_id)
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vdv_supplier
            ON vendors_doc_validity(supplier_name_normalized);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vdv_doc_type
            ON vendors_doc_validity(doc_type);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vdv_valid
            ON vendors_doc_validity(is_valid);
    """)

    # Trigger append-only sur vendors_sensitive_data
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_vsd_no_delete()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'vendors_sensitive_data est append-only. DELETE interdit.';
        END;
        $$;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_vsd_no_delete ON vendors_sensitive_data;
    """)
    op.execute("""
        CREATE TRIGGER trg_vsd_no_delete
            BEFORE DELETE ON vendors_sensitive_data
            FOR EACH ROW EXECUTE FUNCTION fn_vsd_no_delete();
    """)

    # Trigger audit accès sur vendors_sensitive_data
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_vsd_audit_access()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.accessed_at = now();
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_vsd_audit_access ON vendors_sensitive_data;
    """)
    op.execute("""
        CREATE TRIGGER trg_vsd_audit_access
            BEFORE UPDATE OF accessed_by ON vendors_sensitive_data
            FOR EACH ROW EXECUTE FUNCTION fn_vsd_audit_access();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_vsd_audit_access "
        "ON vendors_sensitive_data;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_vsd_no_delete "
        "ON vendors_sensitive_data;"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_vsd_audit_access();")
    op.execute("DROP FUNCTION IF EXISTS fn_vsd_no_delete();")
    op.execute("DROP INDEX IF EXISTS idx_vdv_valid;")
    op.execute("DROP INDEX IF EXISTS idx_vdv_doc_type;")
    op.execute("DROP INDEX IF EXISTS idx_vdv_supplier;")
    op.execute("DROP TABLE IF EXISTS vendors_doc_validity;")
    op.execute("DROP INDEX IF EXISTS idx_vsd_field_type;")
    op.execute("DROP INDEX IF EXISTS idx_vsd_supplier;")
    op.execute("DROP INDEX IF EXISTS idx_vsd_token;")
    op.execute("DROP TABLE IF EXISTS vendors_sensitive_data;")
