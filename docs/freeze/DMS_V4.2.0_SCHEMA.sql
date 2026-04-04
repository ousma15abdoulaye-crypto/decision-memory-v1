-- ══════════════════════════════════════════════════════
-- DMS V4.2.0 — SCHÉMA WORKSPACE-FIRST — ÉTAT CIBLE
-- Complémente V4.1.0 — ne remplace pas les tables non listées
-- Migrations via Alembic op.execute() uniquement — RÈGLE-12
-- Date freeze : 2026-04-04
-- ══════════════════════════════════════════════════════

-- ─────────────────────────────────────────
-- TRIGGER PARTAGÉ (réutilisé V4.1.0 → V4.2.0)
-- fn_reject_mutation() existe déjà dans V4.1.0
-- ─────────────────────────────────────────

-- ═══════════════════════════════════════════════════════
-- Migration 068 — TENANTS
-- ═══════════════════════════════════════════════════════

-- CRUD
-- RLS : non (table de référence globale, filtrée applicativement)
-- Invariant : aucun spécifique
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT NOT NULL UNIQUE,       -- 'sci_mali', 'dgmp_mopti'
    name            TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════
-- Migration 069 — PROCESS WORKSPACES + EVENTS + MEMBERSHIPS
-- ═══════════════════════════════════════════════════════

-- CRUD + FSM sealed irréversible
-- RLS : oui (tenant_id)
-- Invariants : INV-W04 (sealed = lecture seule), INV-W08 (pas d'artefact flottant)
CREATE TABLE process_workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    created_by      UUID NOT NULL REFERENCES users(id),

    reference_code  TEXT NOT NULL,
    title           TEXT NOT NULL,
    process_type    TEXT NOT NULL CHECK (process_type IN (
        'devis_unique','devis_simple','devis_formel',
        'appel_offres_ouvert','rfp_consultance','contrat_direct'
    )),

    estimated_value      NUMERIC(15,2),
    currency             TEXT NOT NULL DEFAULT 'XOF',
    humanitarian_context TEXT NOT NULL DEFAULT 'none' CHECK (
        humanitarian_context IN ('none','cat1','cat2','cat3','cat4')
    ),
    min_offers_required  INTEGER NOT NULL DEFAULT 1,
    response_period_days INTEGER,
    sealed_bids_required BOOLEAN NOT NULL DEFAULT FALSE,
    committee_required   BOOLEAN NOT NULL DEFAULT FALSE,
    zone_id              UUID REFERENCES geo_master(id),
    category_id          UUID REFERENCES procurement_categories(id),
    submission_deadline  TIMESTAMPTZ,
    profile_applied      TEXT,

    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',
        'assembling',
        'assembled',
        'in_analysis',
        'analysis_complete',
        'in_deliberation',
        'sealed',
        'closed',
        'cancelled'
    )),

    -- OBS-01 : dette planifiée — à terme vue matérialisée
    -- calculée depuis bundle_documents + evaluation_documents
    procurement_file JSONB NOT NULL DEFAULT '{
        "pr": "absent", "rfq": "absent",
        "sealed_bids_opened": false, "offers_received": 0,
        "aco": "absent", "vcrn_all_verified": false,
        "contract": "absent", "po": "absent", "grn": "absent"
    }',

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assembled_at            TIMESTAMPTZ,
    analysis_started_at     TIMESTAMPTZ,
    deliberation_started_at TIMESTAMPTZ,
    sealed_at               TIMESTAMPTZ,
    closed_at               TIMESTAMPTZ,

    -- Migration idempotence : référence vers l'ancien case.id
    legacy_case_id          UUID,

    UNIQUE (tenant_id, reference_code)
);

ALTER TABLE process_workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY pw_tenant_isolation ON process_workspaces
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

CREATE INDEX idx_pw_tenant_status ON process_workspaces(tenant_id, status);
CREATE INDEX idx_pw_zone ON process_workspaces(zone_id);
CREATE INDEX idx_pw_created ON process_workspaces(created_at DESC);

CREATE OR REPLACE FUNCTION fn_workspace_sealed_final()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'sealed' AND NEW.status NOT IN ('sealed','closed') THEN
        RAISE EXCEPTION 'Workspace % est scellé. Seule transition autorisée : sealed → closed.', OLD.id;
    END IF;
    IF OLD.status = 'closed' THEN
        RAISE EXCEPTION 'Workspace % est clôturé. Aucune transition autorisée.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_workspace_sealed_final
    BEFORE UPDATE ON process_workspaces
    FOR EACH ROW EXECUTE FUNCTION fn_workspace_sealed_final();


-- APPEND-ONLY (INV-W03, INV-W05)
-- RLS : oui (tenant_id)
-- Invariants : INV-W03 (append-only), INV-W05 (identité event)
CREATE TABLE workspace_events (
    id              BIGSERIAL PRIMARY KEY,
    workspace_id    UUID NOT NULL REFERENCES process_workspaces(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    event_type      TEXT NOT NULL,
    actor_id        UUID NOT NULL,
    actor_type      TEXT NOT NULL CHECK (actor_type IN ('user','service','agent')),
    payload         JSONB NOT NULL DEFAULT '{}',
    schema_version  INTEGER NOT NULL DEFAULT 1,
    emitted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_workspace_events_append_only
    BEFORE DELETE OR UPDATE ON workspace_events
    FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();

ALTER TABLE workspace_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY we_tenant_isolation ON workspace_events
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

CREATE INDEX idx_we_workspace_time ON workspace_events(workspace_id, emitted_at);
CREATE INDEX idx_we_tenant_type ON workspace_events(tenant_id, event_type);
CREATE INDEX idx_we_emitted ON workspace_events(emitted_at DESC);

-- OBS-02 : partitionnement par RANGE(emitted_at) planifié
-- avant passage multi-tenant > 10 tenants ou > 500 processus/an.
-- En pilote SCI Mali (50-100 processus/an) : non nécessaire.


-- CRUD — BLOC-03 CORRIGÉ : UNIQUE sur (workspace_id, user_id, role)
-- Un même utilisateur peut avoir plusieurs rôles dans un workspace.
-- SCI Mali terrain 3-5 personnes : Supply Chain Coordinator = souvent aussi membre comité.
-- RLS : non
-- Invariant : BLOC-03
CREATE TABLE workspace_memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES process_workspaces(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    role            TEXT NOT NULL,
    granted_by      UUID NOT NULL REFERENCES users(id),
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ,
    UNIQUE(workspace_id, user_id, role)
);


-- ═══════════════════════════════════════════════════════
-- Migration 070 — SUPPLIER BUNDLES + BUNDLE DOCUMENTS
-- ═══════════════════════════════════════════════════════

-- CRUD
-- RLS : oui (tenant_id)
-- Invariant : INV-W08 (workspace_id NOT NULL)
CREATE TABLE supplier_bundles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id        UUID NOT NULL REFERENCES process_workspaces(id),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),

    vendor_name_raw     TEXT NOT NULL,
    vendor_id           UUID REFERENCES vendors(id),

    bundle_status       TEXT NOT NULL DEFAULT 'assembling' CHECK (
        bundle_status IN (
            'assembling',
            'complete',
            'incomplete',
            'rejected',
            'orphan'
        )
    ),
    completeness_score  NUMERIC(3,2),
    missing_documents   TEXT[],

    hitl_required       BOOLEAN NOT NULL DEFAULT FALSE,
    hitl_resolved       BOOLEAN NOT NULL DEFAULT FALSE,
    hitl_resolved_by    UUID REFERENCES users(id),
    hitl_resolved_at    TIMESTAMPTZ,

    assembled_by        TEXT NOT NULL DEFAULT 'pass_minus_1',
    assembled_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    bundle_index        INTEGER NOT NULL,
    UNIQUE(workspace_id, bundle_index)
);

ALTER TABLE supplier_bundles ENABLE ROW LEVEL SECURITY;
CREATE POLICY sb_tenant_isolation ON supplier_bundles
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

CREATE INDEX idx_sb_workspace ON supplier_bundles(workspace_id);


-- CRUD
-- RLS : oui (tenant_id)
-- Invariant : INV-W08 (workspace_id NOT NULL)
CREATE TABLE bundle_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bundle_id       UUID NOT NULL REFERENCES supplier_bundles(id),
    workspace_id    UUID NOT NULL REFERENCES process_workspaces(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),

    doc_type        TEXT NOT NULL CHECK (doc_type IN (
        'offer_technical','offer_financial','offer_combined',
        'nif','rccm','rib','quitus_fiscal','cert_non_faillite',
        'sci_conditions','sanctions_cert','sustainability_proof',
        'submission_letter','price_schedule','boq',
        'cv','reference_list','licence','tdr','rfq','dao','other'
    )),
    doc_role        TEXT NOT NULL DEFAULT 'primary' CHECK (
        doc_role IN ('primary','supporting','admin','unknown')
    ),

    filename        TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    file_type       TEXT NOT NULL CHECK (
        file_type IN ('native_pdf','scan','word','excel','image','unknown')
    ),
    storage_path    TEXT NOT NULL,
    page_count      INTEGER,

    ocr_engine      TEXT CHECK (ocr_engine IN (
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

    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by     UUID REFERENCES users(id),

    UNIQUE(workspace_id, sha256)
);

ALTER TABLE bundle_documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY bd_tenant_isolation ON bundle_documents
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

CREATE INDEX idx_bd_bundle ON bundle_documents(bundle_id);
CREATE INDEX idx_bd_workspace ON bundle_documents(workspace_id);


-- ═══════════════════════════════════════════════════════
-- Migration 071 — COMMITTEE SESSIONS + MEMBERS + DELIBERATION EVENTS
-- ═══════════════════════════════════════════════════════

-- CRUD + FSM sealed irréversible
-- RLS : oui (tenant_id)
-- Invariants : INV-W01 (immuabilité actes), INV-W04 (sealed irréversible)
CREATE TABLE committee_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES process_workspaces(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),

    committee_type  TEXT NOT NULL DEFAULT 'standard' CHECK (
        committee_type IN ('standard','humanitarian','simplified')
    ),
    min_members     INTEGER NOT NULL DEFAULT 3,

    session_status  TEXT NOT NULL DEFAULT 'draft' CHECK (
        session_status IN (
            'draft',
            'active',
            'in_deliberation',
            'sealed',
            'closed'
        )
    ),

    activated_at            TIMESTAMPTZ,
    deliberation_opened_at  TIMESTAMPTZ,
    sealed_at               TIMESTAMPTZ,
    closed_at               TIMESTAMPTZ,

    sealed_by       UUID REFERENCES users(id),
    seal_hash       TEXT,
    pv_snapshot     JSONB,

    UNIQUE(workspace_id),
    CONSTRAINT sealed_requires_timestamp CHECK (
        NOT (session_status IN ('draft','active') AND sealed_at IS NOT NULL)
    )
);

CREATE OR REPLACE FUNCTION fn_committee_session_sealed_final()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.session_status = 'sealed' AND NEW.session_status NOT IN ('sealed','closed') THEN
        RAISE EXCEPTION 'Session % est scellée. Seule transition : sealed → closed.', OLD.id;
    END IF;
    IF OLD.session_status = 'closed' THEN
        RAISE EXCEPTION 'Session % est clôturée. Aucune transition.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_committee_session_sealed
    BEFORE UPDATE ON committee_sessions
    FOR EACH ROW EXECUTE FUNCTION fn_committee_session_sealed_final();

ALTER TABLE committee_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY cs_tenant_isolation ON committee_sessions
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );


-- CRUD (composition administrative — pas append-only)
-- RLS : non
-- Invariant : INV-W03 (CRUD, pas append-only)
CREATE TABLE committee_session_members (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id           UUID NOT NULL REFERENCES committee_sessions(id),
    workspace_id         UUID NOT NULL REFERENCES process_workspaces(id),
    tenant_id            UUID NOT NULL REFERENCES tenants(id),
    user_id              UUID NOT NULL REFERENCES users(id),

    role_in_committee    TEXT NOT NULL CHECK (role_in_committee IN (
        'supply_chain','finance','budget_holder',
        'technical','security','pharma','observer','secretary'
    )),
    is_voting            BOOLEAN NOT NULL DEFAULT TRUE,

    conflict_declared    BOOLEAN NOT NULL DEFAULT FALSE,
    conflict_detail      TEXT,
    conflict_declared_at TIMESTAMPTZ,

    delegate_name        TEXT,
    delegate_function    TEXT,
    delegation_reason    TEXT,

    joined_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at           TIMESTAMPTZ,

    UNIQUE(session_id, user_id)
);


-- APPEND-ONLY (INV-W01, INV-W03)
-- RLS : oui (tenant_id)
-- Invariants : INV-W01 (immuabilité actes), INV-W03 (append-only)
CREATE TABLE committee_deliberation_events (
    id              BIGSERIAL PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES committee_sessions(id),
    workspace_id    UUID NOT NULL REFERENCES process_workspaces(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    actor_id        UUID NOT NULL REFERENCES users(id),

    event_type      TEXT NOT NULL CHECK (event_type IN (
        'session_activated',
        'deliberation_opened',
        'comment_added',
        'score_challenged',
        'clarification_requested',
        'conflict_declared',
        'member_added',
        'member_removed',
        'deliberation_closed',
        'session_sealed',
        'pv_generated',
        'session_closed'
    )),

    payload         JSONB NOT NULL DEFAULT '{}',
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_cde_append_only
    BEFORE DELETE OR UPDATE ON committee_deliberation_events
    FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();

ALTER TABLE committee_deliberation_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY cde_tenant_isolation ON committee_deliberation_events
    USING (
        COALESCE(current_setting('app.is_admin', true), '') = 'true'
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

CREATE INDEX idx_cde_session ON committee_deliberation_events(session_id, occurred_at);


-- ═══════════════════════════════════════════════════════
-- Migration 072 — VENDOR MARKET SIGNALS + WATCHLIST
-- ═══════════════════════════════════════════════════════

-- APPEND-ONLY
-- RLS : non
-- Invariant : INV-W03 (append-only)
CREATE TABLE vendor_market_signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    vendor_id           UUID NOT NULL REFERENCES vendors(id),
    signal_type         TEXT NOT NULL CHECK (signal_type IN (
        'reliability_update','price_anchor_update',
        'compliance_flag','blacklist_alert',
        'watchlist_trigger','performance_note'
    )),
    payload             JSONB NOT NULL,
    source_workspace_id UUID REFERENCES process_workspaces(id),
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_vms_append_only
    BEFORE DELETE OR UPDATE ON vendor_market_signals
    FOR EACH ROW EXECUTE FUNCTION fn_reject_mutation();


-- CRUD
-- RLS : non
-- Invariant : aucun spécifique
CREATE TABLE market_watchlist_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    created_by          UUID NOT NULL REFERENCES users(id),
    item_type           TEXT NOT NULL CHECK (item_type IN ('item_key','vendor')),
    item_ref            TEXT NOT NULL,
    alert_threshold_pct NUMERIC(5,2),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ═══════════════════════════════════════════════════════
-- Migration 073 — ALTER TABLES + CHECK CONSTRAINT
-- ═══════════════════════════════════════════════════════

-- Ajout workspace_id nullable sur 10 tables existantes
ALTER TABLE documents ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE evaluation_criteria ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE offer_extractions ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE extraction_review_queue ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE score_history ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE elimination_log ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE evaluation_documents ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE decision_history ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE dict_proposals ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE market_surveys ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);

-- INV-W06 : interdiction verdict automatique (RÈGLE-09 canon)
ALTER TABLE evaluation_documents ADD CONSTRAINT no_winner_field CHECK (
    (scores_matrix IS NULL) OR (
        (scores_matrix->>'winner') IS NULL AND
        (scores_matrix->>'rank') IS NULL AND
        (scores_matrix->>'recommendation') IS NULL AND
        (scores_matrix->>'best_offer') IS NULL AND
        (scores_matrix->>'selected_vendor') IS NULL
    )
);


-- ═══════════════════════════════════════════════════════
-- Migration 074 — DROP case_id + RENAME deprecated
-- PRÉ-CONDITION : script migrate_cases_to_workspaces.py exécuté et vérifié
-- ═══════════════════════════════════════════════════════

-- SET NOT NULL (market_surveys reste nullable — W2 hors processus)
ALTER TABLE documents ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE evaluation_criteria ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE offer_extractions ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE extraction_review_queue ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE score_history ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE elimination_log ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE evaluation_documents ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE decision_history ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE dict_proposals ALTER COLUMN workspace_id SET NOT NULL;

-- DROP case_id
ALTER TABLE documents DROP COLUMN case_id;
ALTER TABLE evaluation_criteria DROP COLUMN case_id;
ALTER TABLE offer_extractions DROP COLUMN case_id;
ALTER TABLE extraction_review_queue DROP COLUMN case_id;
ALTER TABLE score_history DROP COLUMN case_id;
ALTER TABLE elimination_log DROP COLUMN case_id;
ALTER TABLE evaluation_documents DROP COLUMN case_id;
ALTER TABLE decision_history DROP COLUMN case_id;
ALTER TABLE dict_proposals DROP COLUMN source_case_id;
ALTER TABLE market_surveys DROP COLUMN case_id;

-- RENAME (pas DROP — rollback possible 30 jours)
ALTER TABLE cases RENAME TO _deprecated_cases;
ALTER TABLE committees RENAME TO _deprecated_committees;
ALTER TABLE committee_members RENAME TO _deprecated_committee_members;
ALTER TABLE committee_delegations RENAME TO _deprecated_committee_delegations;
ALTER TABLE submission_registries RENAME TO _deprecated_submission_registries;
ALTER TABLE submission_registry_events RENAME TO _deprecated_submission_registry_events;

-- DROP deprecated triggers
DROP TRIGGER IF EXISTS trg_sre_append_only ON _deprecated_submission_registry_events;
DROP TRIGGER IF EXISTS trg_sre_reject_after_close ON _deprecated_submission_registry_events;
DROP TRIGGER IF EXISTS trg_sync_registry_on_lock ON _deprecated_committees;


-- ═══════════════════════════════════════════════════════
-- Migration 075 — RBAC
-- ═══════════════════════════════════════════════════════

-- Référence
-- RLS : non
-- Invariant : aucun spécifique
CREATE TABLE rbac_permissions (
    id    TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

INSERT INTO rbac_permissions VALUES
    ('workspace.view',            'Voir le workspace'),
    ('workspace.create',          'Créer un workspace'),
    ('workspace.manage_members',  'Gérer les membres'),
    ('workspace.view_bundles',    'Voir les bundles'),
    ('workspace.view_scores',     'Voir les scores'),
    ('workspace.view_market',     'Voir le contexte marché'),
    ('committee.view_session',    'Voir la session'),
    ('committee.add_comment',     'Commenter en délibération'),
    ('committee.challenge_score', 'Contester un score'),
    ('committee.request_clarif',  'Demander clarification'),
    ('committee.declare_conflict','Déclarer conflit intérêt'),
    ('committee.seal_session',    'Sceller la session'),
    ('committee.manage_members',  'Gérer composition comité'),
    ('market.view',               'Consulter mémoire marché'),
    ('market.annotate',           'Annoter données marché'),
    ('admin.manage_users',        'Gérer utilisateurs'),
    ('admin.view_audit',          'Consulter audit complet');

CREATE TABLE rbac_roles (
    id    TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

INSERT INTO rbac_roles VALUES
    ('procurement_officer',  'Agent procurement'),
    ('committee_president',  'Président du comité'),
    ('committee_member',     'Membre votant du comité'),
    ('committee_observer',   'Observateur comité'),
    ('market_analyst',       'Analyste marché'),
    ('tenant_admin',         'Administrateur tenant');

CREATE TABLE rbac_role_permissions (
    role_id       TEXT NOT NULL REFERENCES rbac_roles(id),
    permission_id TEXT NOT NULL REFERENCES rbac_permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

INSERT INTO rbac_role_permissions VALUES
    ('procurement_officer','workspace.view'),
    ('procurement_officer','workspace.create'),
    ('procurement_officer','workspace.manage_members'),
    ('procurement_officer','workspace.view_bundles'),
    ('procurement_officer','workspace.view_scores'),
    ('procurement_officer','workspace.view_market'),
    ('procurement_officer','market.view'),
    ('procurement_officer','committee.view_session'),
    ('committee_president','workspace.view'),
    ('committee_president','workspace.view_bundles'),
    ('committee_president','workspace.view_scores'),
    ('committee_president','workspace.view_market'),
    ('committee_president','committee.view_session'),
    ('committee_president','committee.add_comment'),
    ('committee_president','committee.challenge_score'),
    ('committee_president','committee.request_clarif'),
    ('committee_president','committee.declare_conflict'),
    ('committee_president','committee.seal_session'),
    ('committee_president','committee.manage_members'),
    ('committee_president','market.view'),
    ('committee_member','workspace.view'),
    ('committee_member','workspace.view_bundles'),
    ('committee_member','workspace.view_scores'),
    ('committee_member','committee.view_session'),
    ('committee_member','committee.add_comment'),
    ('committee_member','committee.challenge_score'),
    ('committee_member','committee.declare_conflict'),
    ('committee_observer','workspace.view'),
    ('committee_observer','workspace.view_bundles'),
    ('committee_observer','workspace.view_scores'),
    ('committee_observer','committee.view_session'),
    ('market_analyst','market.view'),
    ('market_analyst','market.annotate'),
    ('market_analyst','workspace.view'),
    ('market_analyst','workspace.view_market'),
    ('tenant_admin','workspace.view'),
    ('tenant_admin','workspace.create'),
    ('tenant_admin','workspace.manage_members'),
    ('tenant_admin','workspace.view_bundles'),
    ('tenant_admin','workspace.view_scores'),
    ('tenant_admin','workspace.view_market'),
    ('tenant_admin','committee.view_session'),
    ('tenant_admin','committee.add_comment'),
    ('tenant_admin','committee.challenge_score'),
    ('tenant_admin','committee.request_clarif'),
    ('tenant_admin','committee.declare_conflict'),
    ('tenant_admin','committee.seal_session'),
    ('tenant_admin','committee.manage_members'),
    ('tenant_admin','market.view'),
    ('tenant_admin','market.annotate'),
    ('tenant_admin','admin.manage_users'),
    ('tenant_admin','admin.view_audit');

CREATE TABLE user_tenant_roles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id),
    tenant_id  UUID NOT NULL REFERENCES tenants(id),
    role_id    TEXT NOT NULL REFERENCES rbac_roles(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, tenant_id, role_id)
);

-- Migration RBAC depuis V4.1.0
-- users.role → user_tenant_roles mapping :
--   admin   → tenant_admin
--   manager → procurement_officer
--   buyer   → procurement_officer
--   viewer  → committee_observer
--   auditor → tenant_admin (permissions audit)
