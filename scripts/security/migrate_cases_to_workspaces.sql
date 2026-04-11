-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRATION cases → process_workspaces — HORS AUTOMATISATION
-- ═══════════════════════════════════════════════════════════════════════════
--
-- La table `cases` (V4.1) et `process_workspaces` (V4.2) coexistent par design
-- (voir docs/freeze/CONTEXT_ANCHOR.md — renommages reportés).
--
-- Toute copie de données ou coupure de code exige :
--   - Mandat CTO explicite
--   - Cartographie case_id → workspace_id
--   - Fenêtre de maintenance + validation métier
--
-- Ne pas exécuter ce fichier tel quel en production.

-- Exemple NON EXÉCUTABLE (template) :
--
-- INSERT INTO process_workspaces (id, tenant_id, created_by, reference_code, title, process_type, status)
-- SELECT gen_random_uuid(), ... FROM cases c WHERE ... ;
--
-- ROLLBACK : restaurer depuis sauvegarde logique / PITR.

SELECT 'migrate_cases_to_workspaces.sql — template vide ; mandat CTO requis.' AS status;
