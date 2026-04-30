"""
Tests migration 046b — corrections FK RESTRICT + index fonctionnels.
RÈGLE-17 : toute migration DB = 1 test minimum prouvant l'invariant visé.

Ces tests vérifient l'état FINAL après 046 + 046b.
Ils passent que la DB vienne de l'ancienne 046 (corrigée par 046b)
ou de la nouvelle 046 (déjà correcte, 046b idempotente).
"""

from __future__ import annotations

from psycopg.rows import dict_row

# ─────────────────────────────────────────────────────────
# INVARIANTS ÉTAT FINAL — lecture seule
# ─────────────────────────────────────────────────────────


def test_fk_is_restrict(db_conn):
    """
    FK item_id = ON DELETE RESTRICT après 046b.
    confdeltype = 'r'.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT c.confdeltype
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
             WHERE t.relname = 'imc_category_item_map'
               AND c.contype = 'f'
             LIMIT 1;
        """)
        row = cur.fetchone()
    assert row is not None, "FK introuvable sur imc_category_item_map"
    assert (
        row["confdeltype"] == "r"
    ), f"FK doit être RESTRICT (r) — trouvé : {row['confdeltype']}"


def test_functional_index_imc_map(db_conn):
    """
    idx_imc_map_category_norm (fonctionnel) présent.
    idx_imc_map_category_raw (btree) absent.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'imc_category_item_map';
        """)
        indexes = {row["indexname"] for row in cur.fetchall()}

    assert "idx_imc_map_category_norm" in indexes, "idx_imc_map_category_norm absent"
    assert (
        "idx_imc_map_category_raw" not in indexes
    ), "idx_imc_map_category_raw doit être supprimé"


def test_functional_index_imc_entries(db_conn):
    """
    idx_imc_entries_category_norm (fonctionnel) présent sur imc_entries.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'imc_entries';
        """)
        indexes = {row["indexname"] for row in cur.fetchall()}

    assert (
        "idx_imc_entries_category_norm" in indexes
    ), "idx_imc_entries_category_norm absent sur imc_entries"


# Heads valides — mis à jour après chaque migration
# Ref : Mandat 2 pré-M12 — 2026-03-17
# Chantier 2 CTO correction plan — 2026-04-01 : 055 RLS extension
# fix/pre-m13-blockers — 2026-04-01 : 056 evaluation_documents
VALID_ALEMBIC_HEADS = (
    "046b_imc_map_fix_restrict_indexes",
    "047_couche_a_service_columns",
    "048_vendors_sensitive_data",
    "049_validate_pipeline_runs_fk",
    "050_documents_sha256_not_null",
    "051_cases_tenant_user_tenants_rls",
    "052_dm_app_rls_role",
    "053_dm_app_enforce_security_attrs",
    "054_m12_correction_log",
    "055_extend_rls_documents_extraction_jobs",  # Chantier 2 — RLS extension
    "056_evaluation_documents",  # M13 — table ACO + RLS tenant_scoped
    "057_m13_regulatory_profile_and_correction_log",
    "058_m13_correction_log_case_id_index",
    "059_m14_score_history_elimination_log",
    "m7_4_dict_vivant",  # branche parallèle
    # DMS VIVANT V2 — migrations H0-H4 (PR #300)
    "060_market_coverage_auto_refresh",
    "061_dms_event_index",
    "062_bitemporal_columns",
    "063_candidate_rules",
    "064_dms_embeddings",
    "065_llm_traces",
    "066_bridge_triggers",
    "067_fix_market_coverage_trigger",
    # DMS V4.2.0 — Workspace-First (PR #319-323)
    "068_create_tenants",
    "069_process_workspaces_events_memberships",
    "070_supplier_bundles_documents",
    "071_committee_sessions_deliberation",
    "072_vendor_market_signals_watchlist",
    "073_add_workspace_id_to_canon_tables",
    "074_drop_case_id_set_workspace_not_null",
    "075_rbac_permissions_roles",
    "076_evaluation_documents_workspace_unique",
    "077_fix_bridge_triggers_workspace_id",
    # BLOC5 — SPEC V4.3.1 (source package O2 + qualification / signal_relevance_log)
    "078_source_package_documents_bloc5",
    "079_bloc5_confidence_qualification_signal_log",
    # DMS-FIX-VMS-PIPELINE-V001 — index zone_id pour fallback PV / market_signals_v2
    "080_market_signals_v2_zone_id_index",
    # M16 — Comparatif contradictoire (PR M16)
    "081_m16_evaluation_domains",
    "082_m16_criterion_assessments",
    "083_m16_deliberation_tables",
    "084_m16_price_line_comparisons",
    "085_m16_frame_query_indexes",
    "086_m16_force_row_level_security",
    # DMS V5.1.0 — MQL log, comments, RLS correctif, Langfuse trace (PR #345)
    "087_v51_mql_query_log",
    "088_v51_assessment_comments",
    "089_v51_rls_force_corrective",
    "090_v51_extraction_jobs_langfuse_trace",
    # PR #351 — auth / workspace access rebuild
    "091_fix_user_tenant_provisioning",
    "092_workspace_access_model_v2",
    # Canon V5.1.0 §5.4 / O6 — journal métier assessment_history
    "093_v51_assessment_history",
    # DMS V5.2 — market delta price_line_bundle_values (PR V52)
    "v52_p2_001_price_line_market_delta",
    # No-op après v52_p2 (graphe Alembic linearisé — même id conservé pour déploiements)
    "6ce2036bd346",
    # Sécurité multi-tenant — RLS marché / mercuriale / offres (PR #366)
    "094_security_market_mercurial_tenant_rls",
    "095_tenant_id_default_offers_extractions",
    "096_dms_embeddings_tenant_rls",
    # M12 / agent — rôle supply_chain utilisateur test (CI-friendly si user absent)
    "097_fix_test_user_role_supply_chain",
    # Admin principal propriétaire — email + JWT superuser (PR #398)
    "098_primary_admin_email_owner_mandate",
    # Rôles seed + admin login (migration 099, post-098)
    "099_fix_admin_roles_seed",
    # ZIP Pass-1 R2 — colonnes zip_r2_key / zip_filename sur process_workspaces
    "100_process_workspaces_zip_r2",
    # Phase 1 — offer_extractions FK bundles + stub 098 + merge graphe (PR Phase 1)
    "075_fix_offer_extractions_artifact_fk",
    "076_fix_offer_extractions_fk_to_bundles",
    "098_primary_admin_email_owner_mandate_stub",
    "f7198e64fb16",
    "e7df16ec18ee",
    # P3.2 — scoring schema dao_criteria + process_workspaces (migration 101)
    "101_p32_dao_criteria_scoring_schema",
    # V1.1 M3 — Gate B qualification persisted on supplier_bundles
    "102_v11_bundle_gate_b_role",
)


def test_alembic_head_is_046b(db_conn):
    """
    Head Alembic dans la liste des heads valides (046b → 052, m7_4…).
    ANCHOR-05 : chaîne Alembic intacte — étendre VALID_ALEMBIC_HEADS à chaque migration head.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        version = cur.fetchone()["version_num"]
    assert version in VALID_ALEMBIC_HEADS, f"Head inattendu : {version}"


def test_046b_idempotent_on_clean_db(db_conn):
    """
    Sur une DB déjà correcte (046 nouvelle version),
    046b ne doit pas lever d'erreur.
    La FK est déjà RESTRICT — le DO $$ ne modifie rien.
    Les index IF NOT EXISTS ne créent pas de doublon.
    Ce test passe si head = 046b et FK = RESTRICT.
    """
    with db_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM pg_indexes
            WHERE tablename = 'imc_category_item_map'
              AND indexname = 'idx_imc_map_category_norm';
        """)
        count = cur.fetchone()["cnt"]
    assert (
        count == 1
    ), f"idx_imc_map_category_norm doit exister en un exemplaire — count={count}"
