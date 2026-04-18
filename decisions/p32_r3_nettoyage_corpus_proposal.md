# P3.2 R3 — PROPOSITION NETTOYAGE CORPUS (3 OPTIONS)

**Date** : 2026-04-18  
**Référence** : P3.2 R1 — 19 workspaces LEGACY_90 exclus corpus actif  
**Statut** : 📋 **PROPOSITION** — décision CTO requise

---

## CONTEXTE

**Findings probe R1** :
- 1 workspace conforme : CASE-28b05d85 (sum=100%, pattern 50/40/10)
- 19 workspaces legacy : sum=90%, pattern 30/50/10
- **Décision CTO** : les 19 workspaces sont du BRUIT LEGACY → exclusion corpus actif P3.2

**Bloqueur migration** : P3.2 migration Alembic **ne peut pas** s'exécuter tant que les 19 workspaces LEGACY_90 restent dans le corpus actif (risque backfill erroné `weight_within_family`).

---

## OBJECTIF NETTOYAGE

**But** : isoler ou supprimer les 19 workspaces LEGACY_90 pour que :
1. Backfill `weight_within_family` ne s'applique **que** sur workspaces sum=100%
2. ScoringCore P3.2 consomme **uniquement** workspaces conformes
3. Benchmark B3 (concordance système) ne soit **pas** pollué par données legacy

**Périmètre** : 19 workspaces sci_mali (tenant_id `0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe`)

**Préservation** : CASE-28b05d85 (workspace conforme) **intouchable**

---

## OPTION A — HARD DELETE (suppression définitive)

### Description

**Opération** : `DELETE FROM process_workspaces WHERE id IN (...19 IDs...)`

**Cascade automatique** (ON DELETE CASCADE) :
- `dao_criteria` (critères du workspace)
- `process_runs` (exécutions pipeline)
- `evaluation_documents` (résultats M16 scellés)
- `committee_sessions` (délibérations comité)
- Autres tables liées (vendors, offers, documents, etc.)

### Avantages

✅ **Nettoyage complet** : aucune trace legacy dans la base  
✅ **Performance** : réduction volume DB (19 workspaces × critères × runs)  
✅ **Simplicité** : aucune logique de filtrage runtime (les données n'existent plus)  

### Inconvénients

❌ **Irréversible** : perte définitive des données (si besoin audit futur)  
❌ **Risque compliance** : si les 19 workspaces contenaient des dossiers réels (marchés contractés), suppression = destruction audit trail  
❌ **Traçabilité** : impossible de comprendre a posteriori pourquoi sum=90% (analyse forensic bloquée)  

### Prérequis validation CTO

1. **Confirmer** que les 19 workspaces sont **test/draft abandonnés** (pas de marchés contractés)
2. **Backup** SQL des 19 workspaces avant suppression (export CSV ou dump pg_dump)
3. **Audit légal** : vérifier que suppression ne viole pas obligations conservation données

### SQL exécutable

```sql
-- ⚠️  IRRÉVERSIBLE — backup requis avant exécution

-- Étape 1 : identifier IDs des 19 workspaces LEGACY_90
WITH workspace_legacy AS (
    SELECT pw.id
    FROM dao_criteria dc
    JOIN process_workspaces pw ON dc.workspace_id = pw.id
    WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
      AND dc.ponderation IS NOT NULL
    GROUP BY pw.id
    HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
)
-- Étape 2 : supprimer (CASCADE automatique vers dao_criteria, runs, etc.)
DELETE FROM process_workspaces
WHERE id IN (SELECT id FROM workspace_legacy);

-- Vérification post-suppression :
-- SELECT COUNT(*) FROM process_workspaces WHERE tenant_id = '0daf2d94...';
-- Attendu : 1 workspace (CASE-28b05d85 uniquement)
```

### Commande backup préalable

```bash
# Export SQL des 19 workspaces avant suppression
railway connect postgres

\copy (
    SELECT pw.* 
    FROM process_workspaces pw
    JOIN (
        SELECT pw.id
        FROM dao_criteria dc
        JOIN process_workspaces pw ON dc.workspace_id = pw.id
        WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
          AND dc.ponderation IS NOT NULL
        GROUP BY pw.id
        HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
    ) legacy ON pw.id = legacy.id
) TO 'backup_legacy_90_workspaces.csv' CSV HEADER;
```

---

## OPTION B — SOFT DELETE (marquage inactif)

### Description

**Opération** : ajouter colonne `is_active BOOLEAN DEFAULT TRUE` à `process_workspaces`, puis `UPDATE ... SET is_active = FALSE` sur les 19 workspaces.

**Alternative** : utiliser colonne `status` existante → `UPDATE ... SET status = 'ARCHIVED_LEGACY'`

**Filtrage runtime** : toutes les queries DMS ajoutent `WHERE is_active = TRUE` (ou `status != 'ARCHIVED_LEGACY'`)

### Avantages

✅ **Réversible** : restauration possible (`UPDATE ... SET is_active = TRUE`)  
✅ **Audit trail préservé** : données restent en base (analyse forensic future possible)  
✅ **Compliance** : pas de destruction données (si obligations légales conservation)  

### Inconvénients

❌ **Complexité runtime** : toutes les queries doivent filtrer `is_active = TRUE` (risque oubli → fuite legacy)  
❌ **Performance** : volume DB non réduit (19 workspaces × critères restent en base)  
❌ **Maintenance** : ajout logique de filtrage dans **tous** les routers/services (couche_a, M14, pipeline V5, etc.)  

### Prérequis validation CTO

1. **Choisir** mécanisme soft delete : `is_active` (nouvelle colonne) vs `status = 'ARCHIVED_LEGACY'` (colonne existante)
2. **Auditer** toutes les queries existantes (grep `FROM process_workspaces`) pour ajouter filtre `WHERE is_active = TRUE`
3. **Tester** en local que workspaces legacy n'apparaissent plus dans UI/API

### SQL exécutable

```sql
-- OPTION B1 : nouvelle colonne is_active

-- Migration Alembic P3.2 (avant backfill weight_within_family)
ALTER TABLE process_workspaces
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN process_workspaces.is_active IS
'Workspace actif (TRUE) ou archivé/legacy (FALSE). 
Filtrer WHERE is_active = TRUE dans toutes les queries DMS.';

-- Marquage des 19 workspaces LEGACY_90 comme inactifs
WITH workspace_legacy AS (
    SELECT pw.id
    FROM dao_criteria dc
    JOIN process_workspaces pw ON dc.workspace_id = pw.id
    WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
      AND dc.ponderation IS NOT NULL
    GROUP BY pw.id
    HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
)
UPDATE process_workspaces
SET is_active = FALSE
WHERE id IN (SELECT id FROM workspace_legacy);

-- Vérification :
-- SELECT COUNT(*) FROM process_workspaces WHERE tenant_id = '0daf2d94...' AND is_active = TRUE;
-- Attendu : 1 (CASE-28b05d85 uniquement)
```

```sql
-- OPTION B2 : colonne status existante (si suffisante)

-- Marquage via status (pas de nouvelle colonne)
WITH workspace_legacy AS (
    SELECT pw.id
    FROM dao_criteria dc
    JOIN process_workspaces pw ON dc.workspace_id = pw.id
    WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
      AND dc.ponderation IS NOT NULL
    GROUP BY pw.id
    HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
)
UPDATE process_workspaces
SET status = 'ARCHIVED_LEGACY'
WHERE id IN (SELECT id FROM workspace_legacy);

-- Filtrage queries DMS : WHERE status NOT IN ('ARCHIVED_LEGACY', ...)
```

### Modifications code requises

**Fichiers à modifier** (exhaustif grep `FROM process_workspaces`) :

```python
# src/api/routers/workspaces.py
# src/procurement/m14_engine.py
# src/procurement/pipeline_v5_service.py
# tests/integration/test_*.py

# Pattern ajout filtre :
# AVANT : SELECT * FROM process_workspaces WHERE tenant_id = ...
# APRÈS : SELECT * FROM process_workspaces WHERE tenant_id = ... AND is_active = TRUE
```

**Risque** : oubli filtre dans 1 query → workspace legacy consommé par erreur.

---

## OPTION C — ISOLATION TENANT (migration vers tenant séparé)

### Description

**Opération** : créer un tenant `sci_mali_legacy` (nouveau tenant_id), puis `UPDATE process_workspaces SET tenant_id = <legacy_tenant_id>` sur les 19 workspaces.

**Isolation RLS** : Row Level Security PostgreSQL **bloque automatiquement** accès cross-tenant (pas de modification code DMS).

### Avantages

✅ **Isolation automatique RLS** : aucune modification code DMS (filtrage tenant_id déjà en place)  
✅ **Audit trail préservé** : données restent en base, accessibles via tenant legacy dédié  
✅ **Réversible** : migration retour possible (`UPDATE ... SET tenant_id = <sci_mali_id>`)  
✅ **Performance** : aucune dégradation queries DMS (RLS filtre au niveau PostgreSQL)  

### Inconvénients

❌ **Complexité tenant** : création nouveau tenant (enregistrement `tenants` table + configurations RLS)  
❌ **UI/Dashboard** : si dashboard DMS liste tenants, `sci_mali_legacy` apparaîtra (peut confondre users)  
❌ **Accès legacy** : nécessite mécanisme switch tenant pour consulter workspaces legacy (si besoin audit futur)  

### Prérequis validation CTO

1. **Créer** tenant `sci_mali_legacy` (ou `sci_mali_archived_90pct`)
2. **Configurer** RLS policies pour ce tenant (même isolation que sci_mali production)
3. **Décider** si tenant legacy est **visible** dans UI (liste tenants) ou **masqué** (accès admin uniquement)

### SQL exécutable

```sql
-- Étape 1 : créer tenant legacy
INSERT INTO tenants (id, tenant_code, tenant_name, is_active, created_at)
VALUES (
    gen_random_uuid(),
    'sci_mali_legacy_90pct',
    'SCI Mali - Workspaces Legacy 90% (archived)',
    FALSE,  -- tenant inactif (pas de nouvelle création workspace)
    NOW()
)
RETURNING id AS legacy_tenant_id;

-- Copier legacy_tenant_id retourné (ex: 'abc12345-...')

-- Étape 2 : migrer les 19 workspaces vers tenant legacy
WITH workspace_legacy AS (
    SELECT pw.id
    FROM dao_criteria dc
    JOIN process_workspaces pw ON dc.workspace_id = pw.id
    WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'  -- sci_mali prod
      AND dc.ponderation IS NOT NULL
    GROUP BY pw.id
    HAVING ABS(SUM(dc.ponderation) - 90.0) <= 0.01
)
UPDATE process_workspaces
SET tenant_id = '<legacy_tenant_id>'  -- remplacer par ID retourné Étape 1
WHERE id IN (SELECT id FROM workspace_legacy);

-- Étape 3 : migrer dao_criteria (FK tenant_id si existe)
-- (si dao_criteria.tenant_id existe, sinon skip)
UPDATE dao_criteria
SET tenant_id = '<legacy_tenant_id>'
WHERE workspace_id IN (
    SELECT id FROM process_workspaces WHERE tenant_id = '<legacy_tenant_id>'
);

-- Vérification :
-- SELECT COUNT(*) FROM process_workspaces WHERE tenant_id = '0daf2d94...';
-- Attendu : 1 (CASE-28b05d85 uniquement dans sci_mali prod)
-- SELECT COUNT(*) FROM process_workspaces WHERE tenant_id = '<legacy_tenant_id>';
-- Attendu : 19 (workspaces LEGACY_90 isolés)
```

### Modifications code requises

**Aucune modification code DMS** si RLS déjà actif (tenant_id filtré automatiquement par RLS policies).

**Dashboard admin** (optionnel) : masquer tenant `sci_mali_legacy_90pct` dans liste tenants UI (WHERE is_active = TRUE).

---

## MATRICE DÉCISION

| Critère | Option A (DELETE) | Option B (SOFT DELETE) | Option C (ISOLATION TENANT) |
|---|---|---|---|
| **Réversibilité** | ❌ Irréversible | ✅ Réversible | ✅ Réversible |
| **Audit trail** | ❌ Détruit | ✅ Préservé | ✅ Préservé |
| **Performance DB** | ✅ Volume réduit | ❌ Volume inchangé | ❌ Volume inchangé |
| **Complexité code** | ✅ Aucune modif | ❌ Filtre toutes queries | ✅ Aucune modif (RLS) |
| **Risque fuite legacy** | ✅ Impossible (données n'existent plus) | ⚠️  Possible (oubli filtre query) | ✅ Impossible (RLS bloque) |
| **Compliance légale** | ⚠️  Vérifier obligations conservation | ✅ Conforme conservation | ✅ Conforme conservation |
| **Coût maintenance** | ✅ Zéro | ❌ Élevé (filtrage partout) | ✅ Faible (RLS automatique) |

---

## RECOMMANDATION AGENT

**OPTION C — ISOLATION TENANT** (recommandée)

**Justification** :
1. **Aucune modification code DMS** (RLS filtre automatiquement)
2. **Audit trail préservé** (compliance + forensic futur)
3. **Réversible** (si erreur décision, migration retour possible)
4. **Zéro risque fuite legacy** (RLS bloque au niveau PostgreSQL)

**Alternative** : Option A (DELETE) **si et seulement si** CTO confirme que les 19 workspaces sont :
- Test/draft abandonnés (jamais utilisés en production)
- Aucune obligation légale conservation
- Backup SQL exporté avant suppression

**Option B déconseillée** : coût maintenance élevé (filtrage toutes queries) + risque oubli filtre.

---

## DÉCISION CTO REQUISE

**Questions validation** :

1. **Option choisie** : A (DELETE) / B (SOFT DELETE) / C (ISOLATION TENANT) ?

2. **Si Option A** : confirmer que les 19 workspaces sont test/draft (pas marchés réels) + backup SQL exporté ?

3. **Si Option B** : mécanisme choisi (`is_active` vs `status`) + audit grep queries complété ?

4. **Si Option C** : nom tenant legacy (`sci_mali_legacy_90pct` OK ?) + visible UI ou masqué admin ?

5. **Timeline** : exécution nettoyage **avant** migration P3.2 Alembic (bloquant backfill `weight_within_family`) ?

---

## APRÈS DÉCISION CTO

**Si Option A ou C** : SQL exécutable fourni → exécution CTO ou agent (si GO donné)

**Si Option B** : audit code + migration Alembic + tests → charge estimée 4-6h

**Validation post-nettoyage** :
```sql
-- Vérifier corpus actif = 1 workspace conforme uniquement
SELECT COUNT(*) FROM process_workspaces WHERE tenant_id = '0daf2d94...';
-- Attendu : 1 (CASE-28b05d85)
```

**Déblocage migration P3.2** : après nettoyage validé → GO Étape 3 Alembic migration.

---

**Proposition opposable. Décision CTO requise avant toute action DB.**
