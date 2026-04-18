# P3.2 ACTION F3 — Weight Invariant Probe

**Date** : 2026-04-18  
**Statut** : ⚠️  **ANALYSE MATHÉMATIQUE** (probe live non exécutée)

---

## FORMULE MIGRATION 101

**Code** (l.76-96) :
```sql
WITH family_sums AS (
    SELECT
        dc.workspace_id,
        dc.family,
        SUM(dc.ponderation) AS sum_famille
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

**Transformation** :
```
weight_within_family = ROUND((ponderation / SUM_famille) × 100)::INTEGER
```

---

## ANALYSE MATHÉMATIQUE INVARIANT Σ=100

### Propriété attendue

**Invariant strict** : ∀ (workspace, family), Σ weight_within_family = 100

### Problème arrondi

**Avant arrondi** :
```
Σ (ponderation_i / SUM_famille) × 100 = (Σ ponderation_i / SUM_famille) × 100
                                       = (SUM_famille / SUM_famille) × 100
                                       = 100
```
✅ **Invariant mathématique garanti avant ROUND.**

**Après ROUND + cast INTEGER** :
```
Σ ROUND((ponderation_i / SUM_famille) × 100)::INTEGER ≠ 100 (en général)
```
⚠️  **Invariant brisé par arrondi.**

---

## DÉRIVE ATTENDUE

### Borne théorique

**N critères par famille** → dérive maximale : **± N**

**Exemples** :
- Famille avec 3 critères → dérive ≤ 3 (somme ∈ [97, 103])
- Famille avec 5 critères → dérive ≤ 5 (somme ∈ [95, 105])

### Corpus CASE-28b05d85 (canonique)

**Distribution connue** (50/40/10) :
- TECHNICAL (capacity) : N critères estimé ~6-8
- COMMERCIAL : N critères estimé ~4-6
- SUSTAINABILITY : N critères estimé ~2-3

**Dérive attendue** : ±3 à ±8 par famille

**Somme 100 garantie ?** ❌ **NON** (mathématiquement impossible avec ROUND + INTEGER)

---

## CORRECTIFS POSSIBLES

### Option A : Accepter dérive (commentaire migration)

**Migration 101 l.101** :
```
'Somme par famille = 100% (avant arrondi). Dérive arrondi ≤ N critères.'
```

✅ **Déjà documenté** — dérive acceptée, commentée.

**Acceptable si** :
- Dérive ≤ 5% par famille (tolérance ScoringCore)
- ScoringCore normalise à la volée (rescale à 100)

### Option B : Algorithme allocation résidu

**Remplacer ROUND par allocation déterministe** :
1. Calculer `weight_float = (ponderation / SUM) × 100`
2. `weight_floor = FLOOR(weight_float)`
3. Calculer résidu `R = 100 - Σ weight_floor`
4. Allouer R points aux critères avec plus grand fractionnaire

**Garantie** : Σ weight_within_family = 100 (exact)

**Complexité** : requiert fonction PL/pgSQL + ORDER BY fractionnaire + LIMIT R

### Option C : Poids FLOAT (pas INTEGER)

**Remplacer** `weight_within_family INTEGER` → `weight_within_family FLOAT`

**Avantage** : invariant 100.0 exact (avant arrondi affichage)

**Inconvénient** : change schéma migration (hors scope F3)

---

## DÉCISION CTO REQUISE

**Question** : accepter dérive arrondi avec commentaire (Option A) ?

**Trade-offs** :

| Option | Invariant Σ=100 | Complexité | Schéma |
|---|---|---|---|
| A (ROUND) | ❌ dérive ±N | ✅ simple | ✅ INTEGER |
| B (résidu) | ✅ exact | ⚠️  PL/pgSQL | ✅ INTEGER |
| C (FLOAT) | ✅ exact | ✅ simple | ⚠️  change type |

---

## PROBE ATTENDUE (LIVE)

**Query** : `scripts/p32_f3_weight_invariant_probe.sql`

**Output attendu** :
```
workspace_id | family        | n_criteria | sum_ponderation | sum_weight | invariant_check
-------------|---------------|------------|-----------------|------------|------------------
CASE-28b...  | TECHNICAL     |          7 |            50.0 |         99 | ⚠️  DÉRIVE: -1
CASE-28b...  | COMMERCIAL    |          5 |            40.0 |        101 | ⚠️  DÉRIVE: +1
CASE-28b...  | SUSTAINABILITY|          3 |            10.0 |        100 | ✅ OK
```

**Verdict probe** :
- ✅ Si dérive ≤ 5 par famille : acceptable (tolérance métier)
- ⚠️  Si dérive > 5 par famille : alerter CTO (Option B ou C)
- ⛔ Si dérive > 10 par famille : **BLOCANT** (biais scoring inacceptable)

---

## VERDICT F3

**Statut** : ⚠️  **GO CONDITIONNEL** (dérive commentée, probe live requis)

**Acceptation CTO** :
- ✅ Option A (ROUND + commentaire) acceptable **SI** dérive ≤ 5%
- ✅ ScoringCore **DOIT** normaliser à la volée (rescale famille à 100.0 avant agrégat 50/40/10)
- ⚠️  Probe live **REQUIS** avant alembic upgrade (mesurer dérive réelle CASE-28b05d85)

**Doctrine opposable** : commentaire migration l.101 documente trade-off arrondi.

---

**F3 ANALYSIS COMPLETE — PROBE LIVE + ACCEPTATION CTO REQUIS**
