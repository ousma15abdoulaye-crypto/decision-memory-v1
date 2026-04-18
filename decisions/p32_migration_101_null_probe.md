# P3.2 ACTION F2 — NULL Probe (Corpus Actif)

**Date** : 2026-04-18  
**Statut** : ⚠️  **ANALYSE STATIQUE** (bash bloqué, probe live non exécutée)

---

## CORPUS ACTIF CONNU

**Source vérité** : `decisions/p32_r1_corpus_90pct_decision.md`

**Workspaces actifs** (status != 'cancelled') :
- `CASE-28b05d85` : workspace canonique (50/40/10 capacity/commercial/sustainability)
- `GCF-E2E-*` : 4 workspaces E2E (statut à confirmer live)

**Workspaces exclus** : 21 LEGACY_90 (status = 'cancelled' par Action 3 P3.2-R1)

---

## F2a — criterion_category IS NULL

**Analyse statique** :

Migration 101 (l.44-53) backfill family :
```sql
UPDATE dao_criteria
SET family = CASE
    WHEN criterion_category = 'capacity' THEN 'TECHNICAL'
    WHEN criterion_category = 'commercial' THEN 'COMMERCIAL'
    WHEN criterion_category = 'sustainability' THEN 'SUSTAINABILITY'
    ELSE NULL
END
WHERE criterion_category IS NOT NULL;
```

**Clause WHERE** : `criterion_category IS NOT NULL` → lignes avec `criterion_category IS NULL` **non touchées**.

**Comportement migration** :
- Rows `criterion_category IS NULL` → `family` reste NULL (untouched)
- Rows `criterion_category = 'essential'` → `family = NULL` (ELSE clause)

**Probe attendue** :
```sql
SELECT pw.reference_code, COUNT(*)
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
  AND dc.criterion_category IS NULL
GROUP BY pw.reference_code;
```

**Verdict attendu** :
- ✅ Si COUNT = 0 : aucun NULL résiduel, backfill family sûr
- ⚠️  Si COUNT > 0 : rows ignorées par migration (family reste NULL)

---

## F2b — ponderation IS NULL

**Analyse statique** :

Migration 101 (l.76-96) backfill weight_within_family :
```sql
WITH family_sums AS (
    SELECT dc.workspace_id, dc.family, SUM(dc.ponderation) AS sum_famille
    FROM dao_criteria dc
    JOIN process_workspaces pw ON dc.workspace_id = pw.id
    WHERE dc.family IS NOT NULL
      AND dc.ponderation IS NOT NULL
      AND pw.status NOT IN ('cancelled')
    GROUP BY dc.workspace_id, dc.family
)
UPDATE dao_criteria dc
SET weight_within_family = ROUND((dc.ponderation / fs.sum_famille) * 100.0)::INTEGER
FROM family_sums fs
WHERE dc.workspace_id = fs.workspace_id
  AND dc.family = fs.family
  AND dc.ponderation IS NOT NULL
  AND fs.sum_famille > 0;
```

**Clause WHERE** : `dc.ponderation IS NOT NULL` → lignes avec `ponderation IS NULL` **exclues**.

**Comportement migration** :
- Rows `ponderation IS NULL` → `weight_within_family` reste NULL (exclus du backfill)
- CTE `family_sums` exclut aussi ces rows du calcul SUM

**Impact invariant 50/40/10** :
- Si `ponderation IS NULL` sur corpus actif → **brise invariant global**
- Somme famille incomplète → weights intra-famille incorrects

**Probe attendue** :
```sql
SELECT pw.reference_code, COUNT(*)
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
  AND dc.ponderation IS NULL
GROUP BY pw.reference_code;
```

**Verdict attendu** :
- ✅ Si COUNT = 0 : backfill weight_within_family complet
- ⛔ Si COUNT > 0 sur CASE-28b05d85 : **BLOCANT** (brise invariant canonique)
- ⚠️  Si COUNT > 0 sur GCF-E2E-* uniquement : acceptable si E2E hors scope

---

## F2c — m16_scoring_mode IS NULL

**Analyse statique** :

Migration 101 (l.144-148) backfill scoring_mode :
```sql
UPDATE dao_criteria
SET scoring_mode = UPPER(m16_scoring_mode)
WHERE m16_scoring_mode IS NOT NULL;
```

**Clause WHERE** : `m16_scoring_mode IS NOT NULL` → lignes avec `m16_scoring_mode IS NULL` **non touchées**.

**Comportement migration** :
- Rows `m16_scoring_mode IS NULL` → `scoring_mode` reste NULL
- Commentaire migration (l.154) : **"NULL accepté (mode non défini)"**

**Probe attendue** :
```sql
SELECT pw.reference_code, COUNT(*)
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
  AND dc.m16_scoring_mode IS NULL
GROUP BY pw.reference_code;
```

**Verdict attendu** :
- ✅ NULL accepté par design (commentaire opposable)
- ⚠️  Si COUNT élevé : vérifier cohérence métier (P3.2 ScoringCore peut-il gérer NULL ?)

---

## SYNTHÈSE F2 (ANALYSE STATIQUE)

| Probe | NULL attendu | Impact migration | Blocant si > 0 |
|---|---|---|---|
| F2a (criterion_category) | Possible | Rows ignorées, family=NULL résiduel | ⚠️  NON (ELSE NULL doctrine essential) |
| F2b (ponderation) | Possible | Exclus backfill weight, brise somme | ⛔ OUI si CASE-28b05d85 |
| F2c (m16_scoring_mode) | Accepté | scoring_mode=NULL (design) | ✅ NON (NULL accepté) |

---

## VERDICT F2

**Statut** : ⚠️  **PROBE LIVE REQUIS AVANT GO**

**Blocants potentiels** :
1. **F2b ponderation IS NULL sur CASE-28b05d85** : brise invariant 50/40/10 → **NO-GO migration**
2. F2a criterion_category IS NULL : acceptable si doctrine essential respectée

**Probe CTO requis** : exécuter `scripts/p32_f2_all_null_probes.sql` avant alembic upgrade.

**GO conditionnel** :
- ✅ Si F2b COUNT = 0 sur CASE-28b05d85
- ✅ Si F2a COUNT explicable (essential + doctrine opposable)
- ✅ Si F2c COUNT accepté (NULL design)

---

**F2 ANALYSIS COMPLETE — PROBE LIVE REQUIS POUR GO FINAL**
