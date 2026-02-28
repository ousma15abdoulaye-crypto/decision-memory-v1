-- RUNBOOK M2B -- pipeline_runs orphelins + VALIDATE CONSTRAINT
-- WARNING CONTEXTE ET LIMITES :
--     Ce runbook a ete prepare avant la decouverte que pipeline_runs
--     est protegee par le trigger trg_pipeline_runs_append_only (ADR-0012).
--     Les ETAPES 3 et 5 ne peuvent PAS s executer en local sans violer ADR-0012.
--     ETAPES 1, 2, 4 : executables en local -- diagnostic uniquement.
--     ETAPES 3, 5    : reservees prod Railway si orphan_count prod = 0.
--     En local       : FK reste NOT VALID -- assume et documente (DETTE-M0B-01).
--     Strategie locale alternative : DETTE-FIXTURE-01 -- refactorer les fixtures.

-- ETAPE 1 : compter les orphelins avant purge
SELECT COUNT(*) AS orphan_count_before
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases);

-- ETAPE 2 : inspecter les orphelins
-- PK reelle = pipeline_run_id (verifiee migration 032)
SELECT pipeline_run_id, case_id, created_at
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases)
ORDER BY created_at
LIMIT 20;

-- ETAPE 3 : purger les orphelins
-- INAPPLICABLE EN LOCAL -- trigger append-only ADR-0012 bloque le DELETE
-- PROD UNIQUEMENT -- apres PROBE + backup + GO humain explicite
-- BEGIN;
-- DELETE FROM pipeline_runs
-- WHERE case_id NOT IN (SELECT id FROM cases);
-- COMMIT;
-- En cas d erreur : ROLLBACK;

-- ETAPE 4 : confirmer orphan_count
SELECT COUNT(*) AS orphan_count_after
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases);

-- ETAPE 5 : valider la contrainte
-- INAPPLICABLE EN LOCAL si orphan_count_before > 0
-- PROD UNIQUEMENT -- apres preuve orphan_count_prod = 0
-- ALTER TABLE pipeline_runs
--   VALIDATE CONSTRAINT fk_pipeline_runs_case_id;

-- ETAPE 6 : confirmer validation (prod)
SELECT
  conname,
  convalidated,
  conrelid::regclass AS table_name
FROM pg_constraint
WHERE conrelid = 'pipeline_runs'::regclass
  AND conname = 'fk_pipeline_runs_case_id';

-- ETAPE 7 : DELETE prod sequences (PROD UNIQUEMENT)
-- apres backup confirme + GO humain
-- BEGIN;
-- DELETE FROM cases WHERE id = '<uuid_explicite>';
-- DELETE FROM users WHERE id = <id_explicite>;
-- COMMIT;
-- En cas d erreur : ROLLBACK;
