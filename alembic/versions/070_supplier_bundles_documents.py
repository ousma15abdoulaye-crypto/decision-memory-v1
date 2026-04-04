"""070 - Supplier bundles and bundle documents (V4.2.0)

Revision ID: 070_supplier_bundles_documents
Revises: 069_process_workspaces_events_memberships
Create Date: 2026-04-04

Cree les tables pour l'assemblage des bundles fournisseurs par Pass -1 :
  - supplier_bundles : un bundle = un fournisseur dans un workspace
  - bundle_documents : un document appartenant a un bundle

BLOC-03 : UNIQUE(workspace_id, bundle_index) sur supplier_bundles.
UNIQUE(workspace_id, sha256) sur bundle_documents (deduplication).
RLS tenant sur les deux tables.

users.id = INTEGER (migration 004).

Reference : docs/freeze/DMS_V4.2.0_SCHEMA.sql lignes 184-281
REGLE-12 : op.execute() uniquement.
"""

from __future__ import annotations

from alembic import op

revision = "070_supplier_bundles_documents"
down_revision = "069_process_workspaces_events_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE supplier_bundles (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        UUID NOT NULL REFERENCES process_workspaces(id),
            tenant_id           UUID NOT NULL REFERENCES tenants(id),

            vendor_name_raw     TEXT NOT NULL,
            vendor_id           UUID REFERENCES vendors(id),

            bundle_status TEXT NOT NULL DEFAULT 'assembling' CHECK (
                bundle_status IN (
                    'assembling','complete','incomplete','rejected','orphan'
                )
            ),
            completeness_score  NUMERIC(3,2),
            missing_documents   TEXT[],

            hitl_required       BOOLEAN NOT NULL DEFAULT FALSE,
            hitl_resolved       BOOLEAN NOT NULL DEFAULT FALSE,
            hitl_resolved_by    INTEGER REFERENCES users(id),
            hitl_resolved_at    TIMESTAMPTZ,

            assembled_by        TEXT NOT NULL DEFAULT 'pass_minus_1',
            assembled_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            bundle_index        INTEGER NOT NULL,
            UNIQUE(workspace_id, bundle_index)
        )
        """)

    op.execute("ALTER TABLE supplier_bundles ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY sb_tenant_isolation ON supplier_bundles
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute("CREATE INDEX idx_sb_workspace ON supplier_bundles(workspace_id)")

    op.execute("""
        CREATE TABLE bundle_documents (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bundle_id    UUID NOT NULL REFERENCES supplier_bundles(id),
            workspace_id UUID NOT NULL REFERENCES process_workspaces(id),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),

            doc_type TEXT NOT NULL CHECK (doc_type IN (
                'offer_technical','offer_financial','offer_combined',
                'nif','rccm','rib','quitus_fiscal','cert_non_faillite',
                'sci_conditions','sanctions_cert','sustainability_proof',
                'submission_letter','price_schedule','boq',
                'cv','reference_list','licence','tdr','rfq','dao','other'
            )),
            doc_role TEXT NOT NULL DEFAULT 'primary' CHECK (
                doc_role IN ('primary','supporting','admin','unknown')
            ),

            filename     TEXT NOT NULL,
            sha256       TEXT NOT NULL,
            file_type TEXT NOT NULL CHECK (
                file_type IN (
                    'native_pdf','scan','word','excel','image','unknown'
                )
            ),
            storage_path TEXT NOT NULL,
            page_count   INTEGER,

            ocr_engine TEXT CHECK (ocr_engine IN (
                'mistral_ocr_3','azure_doc_intel','vlm_direct',
                'python_docx','openpyxl','none'
            )),
            ocr_confidence  NUMERIC(3,2),
            raw_text        TEXT,
            structured_json JSONB,
            extracted_at    TIMESTAMPTZ,

            m12_doc_kind    TEXT,
            m12_confidence  NUMERIC(3,2),
            m12_evidence    TEXT[],

            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            uploaded_by INTEGER REFERENCES users(id),

            UNIQUE(workspace_id, sha256)
        )
        """)

    op.execute("ALTER TABLE bundle_documents ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY bd_tenant_isolation ON bundle_documents
            USING (
                COALESCE(current_setting('app.is_admin', true), '') = 'true'
                OR tenant_id = current_setting('app.tenant_id', true)::uuid
            )
        """)

    op.execute("CREATE INDEX idx_bd_bundle ON bundle_documents(bundle_id)")
    op.execute("CREATE INDEX idx_bd_workspace ON bundle_documents(workspace_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bundle_documents CASCADE")
    op.execute("DROP TABLE IF EXISTS supplier_bundles CASCADE")
