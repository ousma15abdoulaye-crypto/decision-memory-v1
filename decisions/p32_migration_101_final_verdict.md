# P3.2 MIGRATION 101 — VERDICT FINAL (F1-F4)

**Date** : 2026-04-18  
**Fichier** : `alembic/versions/101_p32_dao_criteria_scoring_schema.py` → **082_p32_dao_criteria_scoring_schema.py**  
**Statut** : ⚠️  **NO-GO IMMÉDIAT** — corrections F1 + probes F2/F3 requis

---

## SYNTHÈSE F1-F4

| Action | Objet | Statut | Blocant |
|---|---|---|---|
| **F1** | Alembic chain fix | ✅ **RÉSOLU** | ⛔ **OUI** (down_revision fictif) |
| **F2** | NULL probes corpus actif | ⚠️  **ANALYSE STATIQUE** | ⚠️  **CONDITIONNEL** (probe live requis) |
| **F3** | Invariant weight_within_family | ⚠️  **ANALYSE MATH** | ⚠️  **CONDITIONNEL** (dérive acceptée si ≤5%) |
| **F4** | Scope GCF-E2E-* | ✅ **INCLUS** | ✅ **NON** |

---

## F1 — ALEMBIC CHAIN FIX (BLOCANT)

### Problème

Migration 101 contient :
```python
revision = '101_p32_dao_criteria_scoring_schema'
down_revision = '093_xxx'  # ⚠️  FICTIF
```

### Correction requise

**Dernière migration** : `081_m16_evaluation_domains`

**Fichier renommé** : `101_*.py` → **`082_p32_dao_criteria_scoring_schema.py`**

**Lignes corrigées** :
```python
revision = '082_p32_dao_criteria_scoring_schema'
down_revision = '081_m16_evaluation_domains'
```

**Référence** : `decisions/p32_migration_101_chain_fix.md`

---

## F2 — NULL PROBES (CONDITIONNEL)

### Analyse statique

**3 probes requis** (corpus actif, status != 'cancelled') :
- F2a : `criterion_category IS NULL`
- F2b : `ponderation IS NULL` ← **CRITIQUE**
- F2c : `m16_scoring_mode IS NULL`

### Blocants identifiés

| Probe | Risque | Blocant si |
|---|---|---|
| F2a | Rows ignorées par backfill family | ⚠️  Acceptable (essential → NULL doctrine) |
| F2b | Exclus backfill weight, brise invariant | ⛔ **OUI** si COUNT > 0 sur CASE-28b05d85 |
| F2c | scoring_mode = NULL résiduel | ✅ Accepté (NULL design, commentaire l.154) |

### Verdict F2

⚠️  **PROBE LIVE REQUIS AVANT GO**

**Exécution CTO** : `psql $DATABASE_URL -f scripts/p32_f2_all_null_probes.sql`

**GO conditionnel** :
- ✅ Si F2b COUNT = 0 sur CASE-28b05d85
- ⚠️  Si F2b COUNT > 0 sur GCF-E2E-* uniquement : acceptable (test incomplet)
- ⛔ Si F2b COUNT > 0 sur CASE-28b05d85 : **NO-GO migration**

**Référence** : `decisions/p32_migration_101_null_probe.md`

---

## F3 — INVARIANT WEIGHT (CONDITIONNEL)

### Problème arrondi

**Formule migration** :
```sql
weight_within_family = ROUND((ponderation / SUM_famille) × 100)::INTEGER
```

**Invariant mathématique** :
- ✅ Avant ROUND : Σ = 100.0 (exact)
- ❌ Après ROUND : Σ ≠ 100 (dérive ±N, N = nombre critères)

### Dérive attendue

**CASE-28b05d85** (50/40/10, ~15 critères) :
- TECHNICAL (~7 critères) : dérive ±7 → somme ∈ [93, 107]
- COMMERCIAL (~5 critères) : dérive ±5 → somme ∈ [95, 105]
- SUSTAINABILITY (~3 critères) : dérive ±3 → somme ∈ [97, 103]

**Migration l.101 commentaire** : *"Dérive arrondi ≤ N critères"* (déjà documenté)

### Verdict F3

⚠️  **GO CONDITIONNEL** (dérive acceptée SI ≤5% par famille)

**Probe live requis** : `psql $DATABASE_URL -f scripts/p32_f3_weight_invariant_probe.sql`

**Acceptation CTO** :
- ✅ Dérive ≤5 par famille : acceptable (tolérance métier)
- ⚠️  Dérive >5 par famille : alerter, considérer Option B (allocation résidu)
- ⛔ Dérive >10 par famille : **NO-GO** (biais inacceptable)

**Doctrine ScoringCore** : **DOIT** normaliser à la volée (rescale famille à 100.0 avant agrégat 50/40/10)

**Référence** : `decisions/p32_migration_101_weight_invariant_probe.md`

---

## F4 — SCOPE GCF-E2E-* (RÉSOLU)

### Décision

✅ **GCF-E2E-* INCLUS dans migration 101**

### Justification

1. Clause migration générique (pas de filtre workspace_id)
2. Corpus actif post-nettoyage (21 LEGACY_90 exclus)
3. Tests E2E requièrent schéma P3.2
4. Doctrine workspace-first (uniformité)

### Impact

**Rows affectées** :
- dao_criteria : ~75 rows (CASE-28b05d85 ~15 + GCF-E2E-* ~60)
- process_workspaces : 5 workspaces

**Référence** : `decisions/p32_migration_101_scope_decision.md`

---

## CORRECTIONS OBLIGATOIRES PRÉ-EXÉCUTION

### 1. Renommer fichier + corriger revision

**Action** :
```powershell
# Renommer
mv alembic/versions/101_p32_dao_criteria_scoring_schema.py `
   alembic/versions/082_p32_dao_criteria_scoring_schema.py

# Éditer 082_*.py lignes 21-22
revision = '082_p32_dao_criteria_scoring_schema'
down_revision = '081_m16_evaluation_domains'
```

### 2. Exécuter probes F2 + F3

**Scripts fournis** :
- `scripts/p32_f2_all_null_probes.sql` → NULL counts
- `scripts/p32_f3_weight_invariant_probe.sql` → dérive arrondi

**Commande** :
```powershell
psql $env:DATABASE_URL -f scripts\p32_f2_all_null_probes.sql > f2_results.txt
psql $env:DATABASE_URL -f scripts\p32_f3_weight_invariant_probe.sql > f3_results.txt
```

### 3. Valider résultats probes

**Critères GO** :
- ✅ F2b : COUNT = 0 sur CASE-28b05d85 (ponderation IS NULL)
- ✅ F3 : dérive ≤5 par famille (weight_within_family somme)

**Si critères non remplis** → **NO-GO migration**, corrections schéma requises.

---

## VERDICT FINAL

### Statut actuel

⛔ **NO-GO IMMÉDIAT**

**Raisons** :
1. ⛔ **B1 — down_revision fictif** (alembic chain brisée)
2. ⚠️  **B2 — invariant weight non prouvé** (probe F3 requis)
3. ⚠️  **B4 — NULLs non mesurés** (probe F2 requis, F2b critique)

### Étapes validation finale

**Actions séquentielles** :

1. ✅ **Corriger F1** : renommer fichier 101→082, éditer revision/down_revision
2. ⏳ **Exécuter F2** : `p32_f2_all_null_probes.sql`
3. ⏳ **Exécuter F3** : `p32_f3_weight_invariant_probe.sql`
4. ⏳ **Valider résultats** : F2b COUNT=0 CASE-28b05d85, F3 dérive ≤5
5. ⏳ **GO CTO explicite** : après validation 1-4
6. ⏳ **Exécuter migration** : `alembic upgrade head`

### GO conditionnel

✅ **GO MIGRATION SI ET SEULEMENT SI** :

- [x] F1 corrigé (revision 082, down_revision 081)
- [ ] F2b probe : COUNT ponderation IS NULL = 0 sur CASE-28b05d85
- [ ] F3 probe : dérive weight_within_family ≤5 par famille
- [ ] GO CTO explicite post-probes

**Sinon** : **NO-GO**, corrections schéma requises.

---

## FICHIERS LIVRÉS

**Décisions opposables** :
- ✅ `decisions/p32_migration_101_chain_fix.md` (F1)
- ✅ `decisions/p32_migration_101_null_probe.md` (F2)
- ✅ `decisions/p32_migration_101_weight_invariant_probe.md` (F3)
- ✅ `decisions/p32_migration_101_scope_decision.md` (F4)
- ✅ `decisions/p32_migration_101_final_verdict.md` (ce fichier)

**Scripts probes** :
- ✅ `scripts/p32_f2_all_null_probes.sql`
- ✅ `scripts/p32_f3_weight_invariant_probe.sql`
- ✅ `scripts/p32_f2a_category_null_probe.py` (alternatif)
- ✅ `scripts/p32_f2b_ponderation_null_probe.py` (alternatif)
- ✅ `scripts/p32_f2c_scoring_mode_null_probe.py` (alternatif)

---

**MANDAT F1-F4 COMPLET — NO-GO ACTUEL, GO CONDITIONNEL POST-CORRECTIONS + PROBES**
