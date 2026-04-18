# P3.2 — Traitement critères ESSENTIAL (doctrine CTO)

**Date** : 2026-04-18  
**Référence** : Correction doctrine métier migration 101  
**Statut** : ✅ **OPPOSABLE**

---

## DOCTRINE MÉTIER CTO

**Critères essentiels = critères GATE/checks**

**Rôle** : ouvrent l'analyse (checks préliminaires avant scoring)

**Séquence métier canonique DMS** :
1. **essentiels / checks** (GATE)
2. techniques (SCORE, famille TECHNICAL)
3. sustainability (SCORE, famille SUSTAINABILITY)
4. commercial (SCORE, famille COMMERCIAL)
5. summary final

**Conséquence** : critères `essential` **ne sont PAS** une famille de scoring.

---

## TRAITEMENT MIGRATION P3.2

### Backfill `family`

**Mapping canonique** (3 familles scoring uniquement) :
- `criterion_category = 'capacity'` → `family = 'TECHNICAL'`
- `criterion_category = 'commercial'` → `family = 'COMMERCIAL'`
- `criterion_category = 'sustainability'` → `family = 'SUSTAINABILITY'`
- `criterion_category = 'essential'` → **`family = NULL`** (hors agrégat pondéré)

**Rejet définitif** : aucun fallback `essential → TECHNICAL`

### Backfill `criterion_mode`

**Logique doctrine** :
- Critères `essential` → `criterion_mode = 'GATE'` (checks éliminatoires)
- Critères autres → `criterion_mode = 'SCORE'` (évaluation notée)

**SQL migration** :
```sql
UPDATE dao_criteria
SET criterion_mode = 'GATE'
WHERE criterion_category = 'essential';
```

### Exclusion agrégat pondéré

**Invariant 50/40/10** : s'applique aux **3 familles scoring** uniquement (TECHNICAL/COMMERCIAL/SUSTAINABILITY).

**Critères `essential`** :
- **Hors** calcul `weight_within_family`
- **Hors** somme famille (famille = NULL)
- **Hors** invariant 50/40/10
- Traités en logique GATE (binaire PASS/FAIL)

---

## EXISTENCE `essential` EN BASE

**Probe workspace canonique CASE-28b05d85** : `capacity / commercial / sustainability` (pas de `essential`)

**Workspaces GCF-E2E-*** : à vérifier si contiennent `essential`

**Si `essential` existe** :
- Rows identifiées : `SELECT * FROM dao_criteria WHERE criterion_category = 'essential'`
- `family` backfillé = **NULL** (explicite)
- `criterion_mode` backfillé = **'GATE'** (doctrine métier)
- `weight_within_family` backfillé = **NULL** (hors agrégat)

**Documentation migration** : comportement `essential` explicite (pas de fallback silencieux).

---

## RÈGLE OPPOSABLE

**Aucun fallback probabiliste ou de confort** sur champ structurant moteur (`family`).

**Si incertitude mapping** : laisser NULL + documenter + remonter CTO (pas de fallback arbitraire).

---

## VALIDATION MIGRATION 101

**Correction appliquée** :
- ✅ Suppression ligne `WHEN criterion_category = 'essential' THEN 'TECHNICAL'`
- ✅ Backfill `criterion_mode = 'GATE'` pour `essential`
- ✅ Commentaire colonne `family` documentant `essential → NULL`
- ✅ Résumé migration corrigé (doctrine métier)

**Fichier corrigé** : `alembic/versions/101_p32_dao_criteria_scoring_schema.py`

---

**Doctrine métier opposable. Traitement `essential` explicite. Migration 101 corrigée.**
