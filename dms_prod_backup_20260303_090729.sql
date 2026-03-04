-- DMS Railway Prod Backup — 20260303_090729 UTC
-- Généré par scripts/_backup_railway_tmp.py via psycopg
-- Serveur: PostgreSQL 17.x Railway

-- Alembic version: ['m4_patch_a_fix']

-- Tables (59): ['alembic_version', 'analyses', 'analysis_summaries', 'annotation_registry', 'artifacts', 'audit_log', 'audits', 'cases', 'cba_template_schemas', 'committee_decisions', 'committee_delegations', 'committee_events', 'committee_members', 'committees', 'criteria', 'criteria_weighting_validation', 'dao_criteria', 'decision_snapshots', 'dict_collision_log', 'dictionary', 'documents', 'extraction_corrections', 'extraction_errors', 'extraction_jobs', 'extractions', 'geo_cercles', 'geo_communes', 'geo_countries', 'geo_localites', 'geo_master', 'geo_regions', 'geo_zone_commune_mapping', 'geo_zones_operationnelles', 'items', 'lots', 'market_data', 'market_signals', 'memory_entries', 'offer_extractions', 'offers', 'permissions', 'pipeline_runs', 'pipeline_step_runs', 'procurement_categories', 'procurement_references', 'procurement_thresholds', 'purchase_categories', 'role_permissions', 'roles', 'score_runs', 'scoring_configs', 'submission_scores', 'supplier_eliminations', 'supplier_scores', 'token_blacklist', 'units', 'users', 'vendor_identities', 'vendors']


-- TABLE: alembic_version (1 lignes)
-- Colonnes: ['version_num']
INSERT INTO alembic_version (version_num) VALUES ('m4_patch_a_fix');
-- analyses: 0 lignes (skip)
-- analysis_summaries: 0 lignes (skip)
-- annotation_registry: 0 lignes (skip)
-- artifacts: 0 lignes (skip)
-- audit_log: 0 lignes (skip)
-- audits: 0 lignes (skip)
-- cases: 0 lignes (skip)
-- cba_template_schemas: 0 lignes (skip)
-- committee_decisions: 0 lignes (skip)
-- committee_delegations: 0 lignes (skip)
-- committee_events: 0 lignes (skip)
-- committee_members: 0 lignes (skip)
-- committees: 0 lignes (skip)
-- criteria: 0 lignes (skip)
-- criteria_weighting_validation: 0 lignes (skip)
-- dao_criteria: 0 lignes (skip)
-- decision_snapshots: 0 lignes (skip)
-- dict_collision_log: 0 lignes (skip)
-- dictionary: 0 lignes (skip)
-- documents: 0 lignes (skip)
-- extraction_corrections: 0 lignes (skip)
-- extraction_errors: 0 lignes (skip)
-- extraction_jobs: 0 lignes (skip)
-- extractions: 0 lignes (skip)
-- geo_cercles: 0 lignes (skip)
-- geo_communes: 0 lignes (skip)
-- geo_countries: 0 lignes (skip)
-- geo_localites: 0 lignes (skip)

-- TABLE: geo_master (3 lignes)
-- Colonnes: ['id', 'name', 'type', 'parent_id', 'created_at']
INSERT INTO geo_master (id, name, type, parent_id, created_at) VALUES ('zone-bamako-1', 'Bamako', 'city', NULL, '2026-02-28T13:43:27.166896+00:00');
INSERT INTO geo_master (id, name, type, parent_id, created_at) VALUES ('zone-kayes-1', 'Kayes', 'city', NULL, '2026-02-28T13:43:27.166896+00:00');
INSERT INTO geo_master (id, name, type, parent_id, created_at) VALUES ('zone-sikasso-1', 'Sikasso', 'city', NULL, '2026-02-28T13:43:27.166896+00:00');
-- geo_regions: 0 lignes (skip)
-- geo_zone_commune_mapping: 0 lignes (skip)
-- geo_zones_operationnelles: 0 lignes (skip)

-- TABLE: items (3 lignes)
-- Colonnes: ['id', 'description', 'category', 'unit_id', 'created_at']
INSERT INTO items (id, description, category, unit_id, created_at) VALUES (1, 'Riz local', 'Céréales', 1, '2026-02-28T13:43:27.166896+00:00');
INSERT INTO items (id, description, category, unit_id, created_at) VALUES (2, 'Tomate fraîche', 'Légumes', 1, '2026-02-28T13:43:27.166896+00:00');
INSERT INTO items (id, description, category, unit_id, created_at) VALUES (3, 'Mil', 'Céréales', 1, '2026-02-28T13:43:27.166896+00:00');
-- lots: 0 lignes (skip)
-- market_data: 0 lignes (skip)
-- market_signals: 0 lignes (skip)
-- memory_entries: 0 lignes (skip)
-- offer_extractions: 0 lignes (skip)
-- offers: 0 lignes (skip)
-- permissions: 0 lignes (skip)
-- pipeline_runs: 0 lignes (skip)
-- pipeline_step_runs: 0 lignes (skip)

-- TABLE: procurement_categories (6 lignes)
-- Colonnes: ['id', 'code', 'name_en', 'name_fr', 'threshold_usd', 'requires_technical_eval', 'min_suppliers', 'created_at']
INSERT INTO procurement_categories (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at) VALUES ('cat_equipmed', 'EQUIPMED', 'Medical Equipment', 'Équipement médical', '50000.00', TRUE, 5, '2026-02-28T13:43:27.115483');
INSERT INTO procurement_categories (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at) VALUES ('cat_vehicules', 'VEHICULES', 'Vehicles', 'Véhicules', '100000.00', TRUE, 5, '2026-02-28T13:43:27.115483');
INSERT INTO procurement_categories (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at) VALUES ('cat_fournitures', 'FOURNITURES', 'Office Supplies', 'Fournitures bureau', '5000.00', FALSE, 3, '2026-02-28T13:43:27.115483');
INSERT INTO procurement_categories (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at) VALUES ('cat_it', 'IT', 'IT Equipment', 'Équipement IT', '25000.00', TRUE, 3, '2026-02-28T13:43:27.115483');
INSERT INTO procurement_categories (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at) VALUES ('cat_construction', 'CONSTRUCTION', 'Construction Works', 'Travaux construction', '150000.00', TRUE, 5, '2026-02-28T13:43:27.115483');
INSERT INTO procurement_categories (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at) VALUES ('cat_services', 'SERVICES', 'Professional Services', 'Services professionnels', '30000.00', TRUE, 3, '2026-02-28T13:43:27.115483');
-- procurement_references: 0 lignes (skip)

-- TABLE: procurement_thresholds (3 lignes)
-- Colonnes: ['id', 'procedure_type', 'min_amount_usd', 'max_amount_usd', 'min_suppliers', 'description_en', 'description_fr']
INSERT INTO procurement_thresholds (id, procedure_type, min_amount_usd, max_amount_usd, min_suppliers, description_en, description_fr) VALUES (1, 'RFQ', '0.00', '10000.00', 3, 'Request for Quotation', 'Demande de cotation');
INSERT INTO procurement_thresholds (id, procedure_type, min_amount_usd, max_amount_usd, min_suppliers, description_en, description_fr) VALUES (2, 'RFP', '10001.00', '100000.00', 5, 'Request for Proposal', 'Demande de proposition');
INSERT INTO procurement_thresholds (id, procedure_type, min_amount_usd, max_amount_usd, min_suppliers, description_en, description_fr) VALUES (3, 'DAO', '100001.00', NULL, 5, 'Open Tender', 'Appel d''offres ouvert');

-- TABLE: purchase_categories (10 lignes)
-- Colonnes: ['id', 'code', 'label', 'is_high_risk', 'requires_expert', 'specific_rules_json', 'created_at']
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_travel', 'TRAVEL', 'Voyages et hôtels', FALSE, FALSE, '{"max_procedure": "devis_formel"}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_property', 'PROPERTY', 'Location immobilière', FALSE, FALSE, '{"legal_review_required": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_constr', 'CONSTR', 'Construction', TRUE, TRUE, '{"site_visit_required": true, "technical_expert_required": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_health', 'HEALTH', 'Produits de santé', TRUE, TRUE, '{"qualified_suppliers_only": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_it_sci', 'IT_SCI', 'IT / Technologie', TRUE, FALSE, '{"it_approval_required": true, "section_889_compliance": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_labor', 'LABOR', 'Main-d''œuvre externe', FALSE, FALSE, '{"consultancy_fee_limits": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_cva', 'CVA', 'Espèces et bons (CVA)', FALSE, FALSE, '{"fsp_panel_required": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_fleet', 'FLEET', 'Flotte et transport', FALSE, FALSE, '{"safety_standards": true, "fleet_fund_priority": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_insurance', 'INSURANCE', 'Assurance', FALSE, FALSE, '{"provider": "Marsh/MMB", "no_competition": true}', '2026-02-28T13:43:27.115483');
INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES ('cat_generic', 'GENERIC', 'Achats généraux', FALSE, FALSE, '{}', '2026-02-28T13:43:27.115483');
-- role_permissions: 0 lignes (skip)

-- TABLE: roles (3 lignes)
-- Colonnes: ['id', 'name', 'description', 'created_at']
INSERT INTO roles (id, name, description, created_at) VALUES (1, 'admin', 'Full system access', '2026-02-28T13:43:27.143583');
INSERT INTO roles (id, name, description, created_at) VALUES (2, 'procurement_officer', 'Can create and manage own cases', '2026-02-28T13:43:27.143583');
INSERT INTO roles (id, name, description, created_at) VALUES (3, 'viewer', 'Read-only access', '2026-02-28T13:43:27.143583');
-- score_runs: 0 lignes (skip)

-- TABLE: scoring_configs (10 lignes)
-- Colonnes: ['id', 'profile_code', 'commercial_formula', 'commercial_weight', 'capacity_formula', 'capacity_weight', 'sustainability_formula', 'sustainability_weight', 'essentials_weight', 'created_at', 'updated_at', 'price_ratio_acceptable', 'price_ratio_eleve']
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_health', 'HEALTH', 'price_lowest_100', 0.4, 'capacity_experience', 0.4, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_constr', 'CONSTR', 'price_lowest_100', 0.4, 'capacity_experience', 0.4, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_it', 'IT', 'price_lowest_100', 0.5, 'capacity_experience', 0.35, 'sustainability_certifications', 0.15, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_travel', 'TRAVEL', 'price_lowest_100', 0.6, 'capacity_experience', 0.25, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_property', 'PROPERTY', 'price_lowest_100', 0.5, 'capacity_experience', 0.35, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_labor', 'LABOR', 'price_lowest_100', 0.45, 'capacity_experience', 0.4, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_cva', 'CVA', 'price_lowest_100', 0.5, 'capacity_experience', 0.35, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_fleet', 'FLEET', 'price_lowest_100', 0.45, 'capacity_experience', 0.35, 'sustainability_certifications', 0.15, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_insurance', 'INSURANCE', 'price_lowest_100', 0.7, 'capacity_experience', 0.2, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
INSERT INTO scoring_configs (id, profile_code, commercial_formula, commercial_weight, capacity_formula, capacity_weight, sustainability_formula, sustainability_weight, essentials_weight, created_at, updated_at, price_ratio_acceptable, price_ratio_eleve) VALUES ('scoring_generic', 'GENERIC', 'price_lowest_100', 0.5, 'capacity_experience', 0.3, 'sustainability_certifications', 0.1, 0.0, '2026-02-14T00:00:00Z', '2026-02-14T00:00:00Z', 1.05, 1.2);
-- submission_scores: 0 lignes (skip)
-- supplier_eliminations: 0 lignes (skip)
-- supplier_scores: 0 lignes (skip)
-- token_blacklist: 0 lignes (skip)

-- TABLE: units (6 lignes)
-- Colonnes: ['id', 'name', 'symbol', 'created_at']
INSERT INTO units (id, name, symbol, created_at) VALUES (1, 'Kilogramme', 'kg', '2026-02-28T13:43:27.166896+00:00');
INSERT INTO units (id, name, symbol, created_at) VALUES (2, 'Gramme', 'g', '2026-02-28T13:43:27.166896+00:00');
INSERT INTO units (id, name, symbol, created_at) VALUES (3, 'Litre', 'L', '2026-02-28T13:43:27.166896+00:00');
INSERT INTO units (id, name, symbol, created_at) VALUES (4, 'Pièce', 'pce', '2026-02-28T13:43:27.166896+00:00');
INSERT INTO units (id, name, symbol, created_at) VALUES (5, 'Sac', 'sac', '2026-02-28T13:43:27.166896+00:00');
INSERT INTO units (id, name, symbol, created_at) VALUES (6, 'Tonne', 't', '2026-02-28T13:43:27.166896+00:00');

-- TABLE: users (1 lignes)
-- Colonnes: ['id', 'email', 'username', 'hashed_password', 'full_name', 'is_active', 'is_superuser', 'role_id', 'created_at', 'last_login', 'role', 'organization']
INSERT INTO users (id, email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at, last_login, role, organization) VALUES (1, 'admin@dms.local', 'admin', '$2b$12$n19PjDhu0vc01dy0LDWnZ.n8fX4z8tKiNGVwON4wTavaaGXOXFvDG', 'System Administrator', TRUE, TRUE, 1, '2026-02-28 13:43:27.143583+00:00', '2026-02-28T14:48:28.210588', 'viewer', NULL);
-- vendor_identities: 0 lignes (skip)

-- TABLE: vendors (2 lignes)
-- Colonnes: ['id', 'name', 'zone_id', 'created_at']
INSERT INTO vendors (id, name, zone_id, created_at) VALUES (1, 'Marché Central', 'zone-bamako-1', '2026-02-28T13:43:27.166896+00:00');
INSERT INTO vendors (id, name, zone_id, created_at) VALUES (2, 'Boutique Kayes', 'zone-kayes-1', '2026-02-28T13:43:27.166896+00:00');

-- FIN BACKUP — 48 lignes au total