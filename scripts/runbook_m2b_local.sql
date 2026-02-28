-- RUNBOOK M2B LOCAL — pipeline_runs orphelins + VALIDATE CONSTRAINT
-- NE PAS EXÉCUTER SUR PROD SANS PROBE + BACKUP + GO HUMAIN
-- Environnement cible : DB locale uniquement

-- ÉTAPE 1 : compter les orphelins avant purge
SELECT COUNT(*) AS orphan_count_before
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases);

-- ÉTAPE 2 : inspecter les orphelins (poster ce résultat avant DELETE)
SELECT id, case_id, created_at
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases)
ORDER BY created_at
LIMIT 20;

-- ÉTAPE 3 : purger les orphelins
-- EXÉCUTER UNIQUEMENT APRÈS VALIDATION HUMAINE DU RÉSULTAT ÉTAPE 2
DELETE FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases);

-- ÉTAPE 4 : confirmer orphan_count = 0
SELECT COUNT(*) AS orphan_count_after
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases);

-- ÉTAPE 5 : valider la contrainte
-- EXÉCUTER UNIQUEMENT SI orphan_count_after = 0
ALTER TABLE pipeline_runs
  VALIDATE CONSTRAINT fk_pipeline_runs_case_id;

-- ÉTAPE 6 : confirmer validation
SELECT
  conname,
  convalidated,
  conrelid::regclass AS table_name
FROM pg_constraint
WHERE conrelid = 'pipeline_runs'::regclass
  AND conname = 'fk_pipeline_runs_case_id';
