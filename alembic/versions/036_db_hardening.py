"""db hardening

Revision ID: 036_db_hardening
Revises: 035_create_analysis_summaries
Create Date: 2026-02-26

Ajustements post-PROBE-SQL-01 :
  - extraction_jobs : retry_count/max_retries/queued_at déjà présents
    → ADD IF NOT EXISTS sur les 5 colonnes (idempotent)
  - audit_log/score_history/elimination_log/decision_history absentes
    → triggers append-only conditionnés IF EXISTS
  - submission_registries/submission_registry_events absentes
    → fonctions fn_sre_* créées, triggers attachés à M16A
  - app_user absent → REVOKE hors scope, reporté M1
"""
from alembic import op

revision = '036_db_hardening'
down_revision = '035_create_analysis_summaries'
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── 1. FK pipeline_runs → cases — NOT VALID (données orphelines existantes)
    # PROBE-SQL-01 a révélé des case_id orphelins dans pipeline_runs.
    # NOT VALID : contrainte active pour nouvelles insertions.
    # VALIDATE CONSTRAINT exécuté après nettoyage données (voir TECHNICAL_DEBT.md).
    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_pipeline_runs_case_id'
              AND table_name = 'pipeline_runs'
          ) THEN
            ALTER TABLE pipeline_runs
              ADD CONSTRAINT fk_pipeline_runs_case_id
              FOREIGN KEY (case_id) REFERENCES cases(id)
              NOT VALID;
          END IF;
        END $$;
    """)

    # ── 2. committee_delegations
    # PROBE : committee_members PK = member_id (pas id)
    op.execute("""
        CREATE TABLE IF NOT EXISTS committee_delegations (
          id                      UUID PRIMARY KEY
            DEFAULT gen_random_uuid(),
          committee_id            UUID NOT NULL
            REFERENCES committees(committee_id),
          member_id               UUID NOT NULL
            REFERENCES committee_members(member_id),
          delegate_last_name      TEXT NOT NULL,
          delegate_first_name     TEXT NOT NULL,
          delegate_function_title TEXT NOT NULL,
          reason                  TEXT NOT NULL,
          starts_at               TIMESTAMPTZ,
          ends_at                 TIMESTAMPTZ,
          created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ── 3. dict_collision_log
    # PROBE : procurement_references.id = text (pas uuid)
    # canonical_id = TEXT pour correspondre à la PK réelle
    op.execute("""
        CREATE TABLE IF NOT EXISTS dict_collision_log (
          id             UUID PRIMARY KEY
            DEFAULT gen_random_uuid(),
          raw_text_1     TEXT NOT NULL,
          raw_text_2     TEXT NOT NULL,
          canonical_id   TEXT REFERENCES procurement_references(id),
          fuzzy_score    FLOAT NOT NULL
            CHECK (fuzzy_score BETWEEN 0.0 AND 1.0),
          category_match BOOLEAN NOT NULL,
          unit_match     BOOLEAN NOT NULL,
          resolution     TEXT NOT NULL CHECK (
            resolution IN (
              'auto_merged','proposal_created','unresolved'
            )
          ),
          resolved_by    TEXT NOT NULL DEFAULT 'auto',
          source_year_1  INTEGER,
          source_year_2  INTEGER,
          created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ── 4. annotation_registry
    # PROBE : documents.id = text (pas uuid)
    # document_id = TEXT pour correspondre à la PK réelle
    op.execute("""
        CREATE TABLE IF NOT EXISTS annotation_registry (
          id              UUID PRIMARY KEY
            DEFAULT gen_random_uuid(),
          document_id     TEXT REFERENCES documents(id),
          annotation_file TEXT NOT NULL,
          sha256          TEXT NOT NULL UNIQUE,
          document_type   TEXT NOT NULL,
          annotated_by    TEXT NOT NULL,
          annotated_at    TIMESTAMPTZ NOT NULL,
          duration_min    INTEGER,
          field_count     INTEGER,
          criteria_count  INTEGER,
          is_validated    BOOLEAN NOT NULL DEFAULT FALSE,
          validated_at    TIMESTAMPTZ,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ── 5. extraction_jobs — colonnes async (idempotent)
    # retry_count, max_retries, queued_at déjà présents (PROBE #6)
    op.execute("""
        ALTER TABLE extraction_jobs
          ADD COLUMN IF NOT EXISTS retry_count
            INTEGER NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS max_retries
            INTEGER NOT NULL DEFAULT 3,
          ADD COLUMN IF NOT EXISTS next_retry_at
            TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS queued_at
            TIMESTAMPTZ NOT NULL DEFAULT now(),
          ADD COLUMN IF NOT EXISTS fallback_used
            BOOLEAN NOT NULL DEFAULT FALSE;
    """)

    # ── 6. documents — ajouter sha256 + UNIQUE (case_id, sha256)
    # PROBE : sha256 absent de documents
    # sha256 ajouté nullable (backfill requis avant NOT NULL — voir TECHNICAL_DEBT)
    op.execute("""
        ALTER TABLE documents
          ADD COLUMN IF NOT EXISTS sha256 TEXT;
    """)

    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'uq_documents_case_sha256'
              AND table_name = 'documents'
          ) THEN
            ALTER TABLE documents
              ADD CONSTRAINT uq_documents_case_sha256
              UNIQUE (case_id, sha256);
          END IF;
        END $$;
    """)

    # ── 7. fn_reject_mutation — disponible pour tables futures
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_reject_mutation()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION
            'Table % est append-only. DELETE/UPDATE interdits.',
            TG_TABLE_NAME;
        END;
        $$;
    """)

    # ── 8. Triggers append-only — conditionnés IF EXISTS
    # Tables absentes (PROBE) : triggers ignorés silencieusement
    for table in [
        'audit_log',
        'score_history',
        'elimination_log',
        'dict_collision_log',
        'decision_history',
    ]:
        op.execute(f"""
            DO $$ BEGIN
              IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = '{table}'
                  AND table_schema = 'public'
              ) THEN
                EXECUTE 'DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}';
                EXECUTE 'CREATE TRIGGER trg_{table}_append_only
                  BEFORE DELETE OR UPDATE ON {table}
                  FOR EACH ROW
                  EXECUTE FUNCTION fn_reject_mutation()';
              END IF;
            END $$;
        """)

    # ── 9. Fonctions SRE — créées maintenant, triggers à M16A
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_sre_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION
            'submission_registry_events est append-only (INV-R3).';
        END;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_sre_reject_after_close()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
          v_status TEXT;
        BEGIN
          SELECT status INTO v_status
          FROM submission_registries
          WHERE registry_id = NEW.registry_id;
          IF v_status = 'closed' THEN
            RAISE EXCEPTION
              'Registre % est fermé. Aucun dépôt possible (INV-R4).',
              NEW.registry_id;
          END IF;
          RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_sync_registry_on_committee_lock()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.status = 'locked' AND OLD.status != 'locked' THEN
            UPDATE submission_registries
            SET status = 'closed', closed_at = now()
            WHERE committee_id = NEW.committee_id
              AND status = 'open';
          END IF;
          RETURN NEW;
        END;
        $$;
    """)

    # ── 10. Indexes critiques — conditionnés si table absente
    # Tables confirmées présentes (PROBE) : index créés directement
    # Tables absentes : index conditionné DO $$ IF EXISTS $$
    present_indexes = [
        ("idx_documents_case_id",       "documents(case_id)"),
        ("idx_offer_extractions_case",   "offer_extractions(case_id)"),
        ("idx_market_signals_item_zone", "market_signals(item_id, zone_id)"),
        ("idx_extraction_jobs_doc",      "extraction_jobs(document_id)"),
    ]
    for name, definition in present_indexes:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {definition};")

    # Tables absentes (PROBE) : index à créer quand table arrive
    conditional_indexes = [
        ("idx_audit_log_entity",         "audit_log",                    "audit_log(entity, entity_id)"),
        ("idx_score_history_case_vendor", "score_history",               "score_history(case_id, vendor_id)"),
        ("idx_mercurials_item_zone_year", "mercurials",                  "mercurials(item_id, zone_id, year)"),
        ("idx_sre_registry_id",          "submission_registry_events",   "submission_registry_events(registry_id)"),
    ]
    for name, table, definition in conditional_indexes:
        op.execute(f"""
            DO $$ BEGIN
              IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = '{table}'
                  AND table_schema = 'public'
              ) THEN
                EXECUTE $t$
                  CREATE INDEX IF NOT EXISTS {name} ON {definition};
                $t$;
              END IF;
            END $$;
        """)


def downgrade() -> None:
    raise NotImplementedError(
        "downgrade M0B non supporté — "
        "tables structurelles et triggers append-only"
    )
