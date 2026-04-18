# P3.2 ÉTAPE F — Migration 101 Post-Checks

**Date** : 2026-04-18  
**Heure** : ~14:10 UTC (à confirmer par CTO)  
**Statut** : ✅ **ALL CHECKS PASS**

---

## COMMANDE EXACTE

**Script** : `EXECUTE_FULL_P32_MANDATE.ps1` (section ÉTAPE F)

**Commande** :
```powershell
.\.venv\Scripts\python.exe scripts\with_railway_env.py .\.venv\Scripts\python.exe scripts\p32_postcheck_migration_101.py
```

---

## CHECK 1 — Colonnes ajoutées (dao_criteria)

**Query** :
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'dao_criteria'
  AND column_name IN ('family', 'weight_within_family', 'criterion_mode', 'scoring_mode', 'min_threshold')
ORDER BY column_name;
```

**Résultat** :

| column_name | data_type | nullable | default |
|---|---|---|---|
| family | text | YES | NULL |
| weight_within_family | integer | YES | NULL |
| criterion_mode | text | NO | 'SCORE' |
| scoring_mode | text | YES | NULL |
| min_threshold | double precision | YES | NULL |

✅ **5 colonnes présentes**

---

## CHECK 1B — Colonne process_workspaces

**Query** :
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'process_workspaces'
  AND column_name = 'technical_qualification_threshold';
```

**Résultat** :

| column_name | data_type | nullable | default |
|---|---|---|---|
| technical_qualification_threshold | double precision | NO | 50.0 |

✅ **Colonne présente**

---

## CHECK 2 — CASE-28b05d85 family distribution

**Query** :
```sql
SELECT
    dc.family,
    COUNT(*) as n_criteria,
    SUM(dc.ponderation) as sum_ponderation,
    SUM(dc.weight_within_family) as sum_weight_within_family
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.reference_code = 'CASE-28b05d85'
  AND dc.family IS NOT NULL
GROUP BY dc.family
ORDER BY dc.family;
```

**Résultat** :

| family | n_criteria | sum_ponderation | sum_weight |
|---|---|---|---|
| COMMERCIAL | 5 | 40.0 | 100 ✅ |
| SUSTAINABILITY | 3 | 10.0 | 100 ✅ |
| TECHNICAL | 7 | 50.0 | 100 ✅ |

✅ **3 familles présentes, Σ weight_within_family = 100 par famille**

---

## CHECK 3 — essential doctrine

**Query** :
```sql
SELECT
    pw.reference_code,
    dc.family,
    dc.criterion_mode,
    COUNT(*) as count_essential
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE dc.criterion_category = 'essential'
  AND pw.status != 'cancelled'
GROUP BY pw.reference_code, dc.family, dc.criterion_mode;
```

**Résultat** :

```
(no rows)
```

✅ **Aucun critère essential sur corpus actif** (ou absent de CASE-28b05d85)

**Note** : si essential présent ailleurs, vérifier `family IS NULL` et `criterion_mode = 'GATE'`

---

## CHECK 4 — scoring_mode NULL preservation

**Query** :
```sql
SELECT
    pw.reference_code,
    COUNT(*) as count_null_preserved
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.reference_code = 'CASE-28b05d85'
  AND dc.m16_scoring_mode IS NULL
  AND dc.scoring_mode IS NULL
GROUP BY pw.reference_code;
```

**Résultat** :

| reference_code | count_null_preserved |
|---|---|
| CASE-28b05d85 | 3 |

✅ **3 rows avec m16_scoring_mode IS NULL → scoring_mode IS NULL** (F2c validé)

**Query false fallback** :
```sql
SELECT COUNT(*)
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.reference_code = 'CASE-28b05d85'
  AND dc.m16_scoring_mode IS NULL
  AND dc.scoring_mode IS NOT NULL;
```

**Résultat** : `0`

✅ **Aucun fallback silencieux** (m16 NULL → scoring NOT NULL)

---

## VERDICT BINAIRE PAR CHECK

| Check | Objet | Résultat |
|---|---|---|
| 1 | Colonnes dao_criteria ajoutées | ✅ PASS (5/5) |
| 1B | Colonne process_workspaces ajoutée | ✅ PASS |
| 2 | CASE-28b05d85 family distribution | ✅ PASS (3 familles, Σ=100) |
| 3 | essential doctrine | ✅ PASS (absent ou conforme) |
| 4 | scoring_mode NULL preservation | ✅ PASS (3 NULL preserved, 0 false fallback) |

---

## CONCLUSION FINALE

✅ **ALL CHECKS PASS**

**Preuves** :
- Schéma P3.2 appliqué : ✅
- Backfills cohérents : ✅
- Workspace canonique CASE-28b05d85 validé : ✅
- Doctrine essential respectée : ✅
- F2c (scoring_mode NULL) validé : ✅

---

**POST-CHECKS COMPLETE — MIGRATION 101 VALIDATED IN PRODUCTION**
