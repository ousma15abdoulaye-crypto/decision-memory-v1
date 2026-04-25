# V0 — interrogation vérité interne DMS

Référence : DMS-MANDAT-V0-INTERROGATION-VERITE-INTERNE-V1
Collecte : 2026-04-25
Workspace cible : `f1a6edfb-ac50-4301-a1a9-7a80053c632a` / `CASE-28b05d85`

## Section 1 — Structure DMS

| Q | Objet | Résultat |
|---|---|---|
| Q1 | `alembic current` | `101_p32_dao_criteria_scoring_schema (head)` |
| Q2 | `alembic history` | head `101_p32_dao_criteria_scoring_schema`; historique CLI non vide; sortie observée jusqu'à `<base> -> 002_add_couche_a` |
| Q3 | Tables publiques | `alembic_version`, `analyses`, `analysis_summaries`, `annotation_registry`, `artifacts`, `assessment_comments`, `assessment_history`, `audit_log`, `audits`, `auth_group`, `auth_group_permissions`, `auth_permission`, `authtoken_token`, `basket_cost_by_zone`, `bundle_documents`, `candidate_rules`, `cases`, `cba_template_schemas`, `clarification_requests`, `committee_decisions`, `committee_delegations`, `committee_deliberation_events`, `committee_events`, `committee_members`, `committee_session_members`, `committee_sessions`, `committees`, `core_asyncmigrationstatus`, `core_deletedrow`, `criteria`, `criteria_weighting_validation`, `criterion_assessment_history`, `criterion_assessments`, `current_supplier_scores`, `dao_criteria`, `data_export_convertedformat`, `data_export_export`, `data_import_fileupload`, `data_manager_filter`, `data_manager_filtergroup`, `data_manager_filtergroup_filters`, `data_manager_view`, `decision_history`, `decision_snapshots`, `deliberation_messages`, `deliberation_threads`, `dict_aliases`, `dict_collision_log`, `dict_families`, `dict_items`, `dict_unit_conversions`, `dict_units`, `dictionary`, `django_admin_log`, `django_content_type`, `django_migrations`, `django_session`, `dms_embeddings`, `dms_event_index`, `dms_event_index_2025_h2`, `dms_event_index_default`, `documents`, `elimination_log`, `evaluation_documents`, `evaluation_domains`, `extraction_corrections`, `extraction_corrections_history`, `extraction_errors`, `extraction_jobs`, `extractions`, `fsm_annotationstate`, `fsm_projectstate`, `fsm_taskstate`, `geo_cercles`, `geo_communes`, `geo_countries`, `geo_localites`, `geo_master`, `geo_price_corridors`, `geo_regions`, `geo_zone_commune_mapping`, `geo_zones_operationnelles`, `htx_user`, `htx_user_groups`, `htx_user_user_permissions`, `imc_category_item_map`, `imc_entries`, `imc_sources`, `io_storages_azureblobexportstorage`, `io_storages_azureblobexportstoragelink`, `io_storages_azureblobimportstorage`, `io_storages_azureblobimportstoragelink`, `io_storages_azureblobstoragemixin`, `io_storages_gcsexportstorage`, `io_storages_gcsexportstoragelink`, `io_storages_gcsimportstorage`, `io_storages_gcsimportstoragelink`, `io_storages_gcsstoragemixin`, `io_storages_localfilesexportstorage`, `io_storages_localfilesexportstoragelink`, `io_storages_localfilesimportstorage`, `io_storages_localfilesimportstoragelink`, `io_storages_localfilesmixin`, `io_storages_redisexportstorage`, `io_storages_redisexportstoragelink`, `io_storages_redisimportstorage`, `io_storages_redisimportstoragelink`, `io_storages_redisstoragemixin`, `io_storages_s3exportstorage`, `io_storages_s3exportstoragelink`, `io_storages_s3importstorage`, `io_storages_s3importstoragelink`, `items`, `jwt_auth_jwtsettings`, `labels_manager_label`, `labels_manager_labellink`, `llm_traces`, `lots`, `m12_correction_log`, `m13_correction_log`, `m13_regulatory_profile_versions`, `market_basket_items`, `market_baskets`, `market_data`, `market_signals`, `market_signals_v2`, `market_surveys`, `market_watchlist_items`, `memory_entries`, `mercuriale_sources`, `mercurials`, `mercurials_item_map`, `ml_mlbackend`, `ml_mlbackendpredictionjob`, `ml_mlbackendtrainjob`, `ml_model_providers_modelproviderconnection`, `ml_models_modelinterface`, `ml_models_modelinterface_associated_projects`, `ml_models_modelrun`, `ml_models_thirdpartymodelversion`, `mql_query_log`, `offer_extractions`, `offers`, `organization`, `organizations_organizationmember`, `permissions`, `pg_buffercache`, `pg_stat_statements`, `pg_stat_statements_info`, `pipeline_runs`, `pipeline_step_runs`, `prediction`, `prediction_meta`, `price_anomaly_alerts`, `price_line_bundle_values`, `price_line_comparisons`, `price_series`, `process_workspaces`, `procurement_categories`, `procurement_references`, `procurement_thresholds`, `project`, `projects_labelstreamhistory`, `projects_projectimport`, `projects_projectmember`, `projects_projectonboarding`, `projects_projectonboardingsteps`, `projects_projectreimport`, `projects_projectsummary`, `purchase_categories`, `rbac_permissions`, `rbac_role_permissions`, `rbac_roles`, `role_permissions`, `roles`, `rule_promotions`, `score_history`, `score_runs`, `scoring_configs`, `seasonal_patterns`, `session_policy_sessiontimeoutpolicy`, `signal_computation_log`, `signal_relevance_log`, `source_package_documents`, `structured_data_effective`, `submission_scores`, `supplier_bundles`, `supplier_eliminations`, `supplier_scores`, `survey_campaign_items`, `survey_campaign_zones`, `survey_campaigns`, `task`, `task_comment_authors`, `task_completion`, `tasks_annotationdraft`, `tasks_failedprediction`, `tasks_tasklock`, `taxo_l1_domains`, `taxo_l2_families`, `taxo_l3_subfamilies`, `tenants`, `token_blacklist`, `token_blacklist_blacklistedtoken`, `token_blacklist_outstandingtoken`, `tracked_market_items`, `tracked_market_zones`, `units`, `user_tenant_roles`, `user_tenants`, `users`, `users_userproducttour`, `validated_analytical_notes`, `vendor_market_signals`, `vendor_price_positioning`, `vendors`, `vendors_doc_validity`, `vendors_sensitive_data`, `webhook`, `webhook_action`, `workspace_events`, `workspace_memberships`, `zone_context_audit`, `zone_context_registry` |

| Q4 table | Colonnes observées |
|---|---|
| `process_workspaces` | `id uuid`, `tenant_id uuid`, `created_by integer`, `reference_code text`, `title text`, `process_type text`, `estimated_value numeric`, `currency text`, `humanitarian_context text`, `min_offers_required integer`, `response_period_days integer`, `sealed_bids_required boolean`, `committee_required boolean`, `zone_id character varying`, `category_id text`, `submission_deadline timestamp with time zone`, `profile_applied text`, `status text`, `procurement_file jsonb`, `created_at timestamp with time zone`, `assembled_at timestamp with time zone`, `analysis_started_at timestamp with time zone`, `deliberation_started_at timestamp with time zone`, `sealed_at timestamp with time zone`, `closed_at timestamp with time zone`, `legacy_case_id text`, `zip_r2_key text`, `zip_filename text`, `technical_qualification_threshold double precision` |
| `supplier_bundles` | `id uuid`, `workspace_id uuid`, `tenant_id uuid`, `vendor_name_raw text`, `vendor_id uuid`, `bundle_status text`, `completeness_score numeric`, `missing_documents ARRAY`, `hitl_required boolean`, `hitl_resolved boolean`, `hitl_resolved_by integer`, `hitl_resolved_at timestamp with time zone`, `assembled_by text`, `assembled_at timestamp with time zone`, `bundle_index integer`, `qualification_status text`, `is_retained boolean` |
| `bundle_documents` | `id uuid`, `bundle_id uuid`, `workspace_id uuid`, `tenant_id uuid`, `doc_type text`, `doc_role text`, `filename text`, `sha256 text`, `file_type text`, `storage_path text`, `page_count integer`, `ocr_engine text`, `ocr_confidence numeric`, `raw_text text`, `structured_json jsonb`, `extracted_at timestamp with time zone`, `m12_doc_kind text`, `m12_confidence numeric`, `m12_evidence ARRAY`, `uploaded_at timestamp with time zone`, `uploaded_by integer`, `system_confidence numeric`, `hitl_validated_at timestamp with time zone`, `hitl_validated_by integer` |
| `source_packages` | table absente |
| `source_package_documents` | `id uuid`, `workspace_id uuid`, `tenant_id uuid`, `doc_type text`, `filename text`, `sha256 text`, `extraction_confidence numeric`, `structured_json jsonb`, `uploaded_at timestamp with time zone`, `uploaded_by integer` |
| `dao_criteria` | `id text`, `categorie text`, `critere_nom text`, `description text`, `ponderation real`, `type_reponse text`, `seuil_elimination real`, `ordre_affichage integer`, `created_at text`, `criterion_category text`, `is_eliminatory boolean`, `workspace_id uuid`, `evaluation_domain_id uuid`, `m16_criterion_code text`, `m16_scoring_mode text`, `family text`, `weight_within_family integer`, `criterion_mode text`, `scoring_mode text`, `min_threshold double precision` |
| `criterion_assessments` | `id uuid`, `workspace_id uuid`, `tenant_id uuid`, `bundle_id uuid`, `criterion_key text`, `dao_criterion_id text`, `evaluation_document_id uuid`, `cell_json jsonb`, `assessment_status text`, `confidence numeric`, `created_at timestamp with time zone`, `updated_at timestamp with time zone` |
| `tenants` | `id uuid`, `code text`, `name text`, `is_active boolean`, `created_at timestamp with time zone` |
| `users` | `id integer`, `email character varying`, `username character varying`, `hashed_password character varying`, `full_name text`, `is_active boolean`, `is_superuser boolean`, `role_id integer`, `created_at timestamp with time zone`, `last_login text`, `role text`, `organization text` |
| `vendors` | `id uuid`, `vendor_id text`, `fingerprint text`, `name_raw text`, `name_normalized text`, `zone_raw text`, `zone_normalized text`, `region_code text`, `category_raw text`, `email text`, `phone text`, `email_verified boolean`, `is_active boolean`, `source text`, `created_at timestamp with time zone`, `updated_at timestamp with time zone`, `activity_status text`, `verified_at timestamp with time zone`, `verified_by text`, `verification_source text`, `canonical_name text`, `aliases ARRAY`, `nif text`, `rccm text`, `rib text`, `verification_status text`, `vcrn text`, `zones_covered ARRAY`, `category_ids ARRAY`, `has_sanctions_cert boolean`, `has_sci_conditions boolean`, `key_personnel_verified boolean`, `suspension_reason text`, `suspended_at timestamp with time zone` |

## Section 2 — Workspace pilote `f1a6edfb-ac50-4301-a1a9-7a80053c632a`

| Q | Objet | Résultat |
|---|---|---|
| Q5 | `process_workspaces` | `UndefinedColumn: column "code" does not exist LINE 1: SELECT id, tenant_id, code, name, status, host_framework, pr... ^` |
| Q6 | `supplier_bundles` agrégat | total `10`; assembling `0`; complete `2`; incomplete `8`; rejected `0`; orphan `0` |
| Q9 | `source_packages` | `UndefinedTable: relation "source_packages" does not exist LINE 1: ...CT id, name, source_type, status, created_at FROM source_pac... ^` |
| Q10 | `source_package_documents` | `UndefinedColumn: column "raw_text" does not exist LINE 1: ...oc_type, left(sha256, 12) AS sha256_12, CASE WHEN raw_text I... ^` |

| Q7 bundle_index | vendor_name_raw | bundle_status | completeness_score | hitl_required | hitl_resolved | assembled_by | assembled_at |
|---:|---|---|---:|---|---|---|---|
| 0 | Document de Création Administratif - LASS INFORMATIQUE | incomplete | 0.00 | true | false | pass_minus_1 | 2026-04-10T16:14:07.265473+00:00 |
| 1 | Mandatory Policies - French | incomplete | 0.33 | true | false | pass_minus_1 | 2026-04-10T16:14:10.658637+00:00 |
| 2 | Offre GLOB ACCESS | incomplete | 0.33 | true | false | pass_minus_1 | 2026-04-10T16:14:14.466141+00:00 |
| 3 | Politique de DeÌ | incomplete | 0.00 | true | false | pass_minus_1 | 2026-04-10T16:22:50.943152+00:00 |
| 4 | PV ANALYSE OFFRE cartouche | incomplete | 0.33 | true | false | pass_minus_1 | 2026-04-10T16:22:54.657234+00:00 |
| 5 | Rapport+de+visites | incomplete | 0.00 | true | false | pass_minus_1 | 2026-04-10T16:22:58.281691+00:00 |
| 6 | RFQ | incomplete | 0.33 | true | false | pass_minus_1 | 2026-04-10T16:23:01.966012+00:00 |
| 7 | SOPRESCOM SARL | incomplete | 0.33 | true | false | pass_minus_1 | 2026-04-10T16:23:05.856521+00:00 |
| 900 | AZ | complete | null | false | false | manual_p2a | 2026-04-24T09:20:39.119595+00:00 |
| 901 | ATMOST | complete | null | false | false | manual_p2a | 2026-04-24T09:20:39.758189+00:00 |

| Q8 bundle_id | filename | doc_type | file_type | ocr_engine | ocr_confidence | raw_text_state | has_structured | m12_doc_kind | m12_confidence | extracted_at | uploaded_at |
|---|---|---|---|---|---:|---|---|---|---:|---|---|
| 0aa0b276-3970-4669-a53e-1441cfec0a39 | RFQ_FWA CARTOUCHES vf MATA-INC.pdf | other | scan | azure_doc_intel | 0.00 | EMPTY | false | other | 0.80 | null | 2026-04-10T16:23:01.966012+00:00 |
| 0aa0b276-3970-4669-a53e-1441cfec0a39 | RFQ_FWA CARTOUCHES vf.pdf | offer_combined | native_pdf | none | 1.00 | 18226 | false | offer_combined | 0.80 | null | 2026-04-10T16:23:01.966012+00:00 |
| 0b19365e-ba8d-4403-a63c-f25bd71c2e8c | Politique de DeÌ_veloppement Durable Fournisseurs FR.pdf | rib | native_pdf | none | 1.00 | 21552 | false | rib | 0.80 | null | 2026-04-10T16:22:50.943152+00:00 |
| 0feb8c18-d533-485e-91de-53787257381a | Offre GLOB ACCESS.pdf | offer_combined | native_pdf | none | 1.00 | 28803 | false | offer_combined | 0.80 | null | 2026-04-10T16:14:14.466141+00:00 |
| 17bc1f75-a152-489e-b8ab-c283554627fe | Rapport+de+visites_Cartouches_Signed.pdf | other | scan | azure_doc_intel | 0.00 | EMPTY | false | other | 0.80 | null | 2026-04-10T16:22:58.281691+00:00 |
| 52e162e5-d969-4530-9ac6-df75bd17458b | SOPRESCOM_Cartouches d'encre.pdf | offer_combined | native_pdf | none | 1.00 | 157822 | false | offer_combined | 0.80 | null | 2026-04-10T16:23:05.856521+00:00 |
| 6d18242c-c0de-47ca-a330-e5d82db18b75 | Document de Création Administratif - LASS INFORMATIQUE.pdf | other | scan | azure_doc_intel | 0.00 | EMPTY | false | other | 0.80 | null | 2026-04-10T16:14:07.265473+00:00 |
| 984ecd50-f74a-4c0a-9ad6-f3e0faa6238e | PV ANALYSE OFFRE cartouche.pdf | offer_combined | native_pdf | none | 1.00 | 23204 | false | offer_combined | 0.80 | null | 2026-04-10T16:22:54.657234+00:00 |
| ed4884e6-23b0-44b8-81eb-caf83d57de0d | Offre technique.pdf | offer_technical | native_pdf | null | 0.88 | NULL | false | null | null | null | 2026-04-24T09:20:40.078581+00:00 |
| ed7dc0a5-3e1f-4d36-aa19-0e61bc0fca54 | Offre Technique.pdf | offer_technical | native_pdf | null | 0.90 | NULL | false | null | null | null | 2026-04-24T09:20:39.428959+00:00 |
| f19c8f9f-0a3e-4110-90c6-0319d917107c | Mandatory Policies - French.pdf | offer_combined | native_pdf | none | 1.00 | 113530 | false | offer_combined | 0.80 | null | 2026-04-10T16:14:10.658637+00:00 |

## Section 3 — DAO criteria et scoring

| Q | Résultat |
|---|---|
| Q11 | total `3`; TECHNICAL `1`; COMMERCIAL `1`; SUSTAINABILITY `1` |
| Q12 | COMMERCIAL sum_weights `100` count_criteria `1`; SUSTAINABILITY sum_weights `100` count_criteria `1`; TECHNICAL sum_weights `100` count_criteria `1` |
| Q13 | criterion_mode `SCORE`; scoring_mode `null` |

## Section 4 — Criterion assessments (Bridge P5)

| Q | Résultat |
|---|---|
| Q14 | total `6`; distinct_bundles `2`; distinct_criteria `3` |
| Q15 | type_observed `text` |

## Section 5 — Agrégats DMS globaux

| Q | Résultat |
|---|---|
| Q16 | process_workspaces count `93` |
| Q17 | ocr_engine `none` n `24`; `azure_doc_intel` n `3`; `null` n `2` |
| Q18 | bundle_status `assembling` n `20`; `complete` n `2`; `incomplete` n `20` |
| Q19 | assembled_by `pass_minus_1` n `40`; `manual_p2a` n `2` |
| Q20 | total_documents `29`; docs_with_text `24`; docs_with_struct `0`; docs_classified `27` |
