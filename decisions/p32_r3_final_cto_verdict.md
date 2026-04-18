# P3.2 ACTION R3 — Verdict Final CTO-Ready

**Date** : 2026-04-18  
**Migration** : `alembic/versions/101_p32_dao_criteria_scoring_schema.py`  
**Statut** : ⏳ **ATTENTE EXÉCUTION F2 PROBES CTO**

---

## CHAÎNE ALEMBIC RÉELLE (R1 ✅)

**Prouvé par lecture fichiers** (`decisions/p32_chain_reality_check.md`) :

```
098_primary_admin_email_owner_mandate
  ↓
099_fix_admin_roles_seed
  ↓
100_process_workspaces_zip_r2  ← dernière migration existante
  ↓
101_p32_dao_criteria_scoring_schema  ← migration P3.2 (corrigée)
```

**Fichier 101 corrigé** :
- Ligne 4 : `Revises: 100_process_workspaces_zip_r2`
- Ligne 22 : `down_revision = '100_process_workspaces_zip_r2'`

✅ **Chaîne cohérente prouvée**

---

## F2 NULL PROBES (R2 ⏳)

### Méthode validée

**Python + with_railway_env** (pas psql)

**Script fourni** : `scripts/p32_r2_execute_all_f2_probes.py`

**Exécution CTO** :
```powershell
.\EXECUTE_F2_PROBES.ps1
```

Ou manuel :
```powershell
.\.venv\Scripts\python.exe scripts\with_railway_env.py .\.venv\Scripts\python.exe scripts\p32_r2_execute_all_f2_probes.py
```

### Probes exécutées

| Probe | Query | Blocant si |
|---|---|---|
| **F2a** | `criterion_category IS NULL` | Acceptable (essential→NULL doctrine) |
| **F2b** | `ponderation IS NULL` | ⛔ **OUI** si COUNT > 0 sur CASE-28b05d85 |
| **F2c** | `m16_scoring_mode IS NULL` | Non (NULL accepté par design) |

### Critère GO F2

✅ **GO SI** : F2b COUNT ponderation IS NULL = 0 sur workspace canonique CASE-28b05d85

⛔ **NO-GO SI** : F2b COUNT > 0 sur CASE-28b05d85 (brise backfill weight_within_family)

---

## F3 INVARIANT WEIGHT (ANALYSE)

### Formule migration 101

```sql
weight_within_family = ROUND((ponderation / SUM_famille) × 100)::INTEGER
```

### Propriété mathématique

**Avant ROUND** : Σ (ponderation_i / SUM) × 100 = 100.0 ✅ **exact**

**Après ROUND + INTEGER** : Σ ROUND(...) ≠ 100 ⚠️  **dérive ±N** (N = nombre critères)

### Stratégies possibles

| Option | Invariant Σ=100 | Complexité | Schéma |
|---|---|---|---|
| **A - ROUND (actuel)** | ❌ dérive ±N | Simple | INTEGER |
| **B - Allocation résidu** | ✅ exact | PL/pgSQL | INTEGER |
| **C - FLOAT** | ✅ exact | Simple | FLOAT |

**Migration 101 actuelle** : Option A (ROUND)

**Commentaire l.101** : *"Dérive arrondi ≤ N critères"* (documenté)

### Stratégie résidu (Option B) — si CTO exige Σ=100 exact

**Algorithme** :
1. Calculer `weight_float = (ponderation / SUM) × 100` pour chaque critère
2. `weight_floor = FLOOR(weight_float)` → somme partielle < 100
3. Résidu `R = 100 - Σ weight_floor`
4. Ordonner critères par fractionnaire décroissant
5. Allouer +1 aux R premiers critères

**Garantie** : Σ weight_within_family = 100 (exact, déterministe)

**Code PL/pgSQL requis** : fonction + WITH RECURSIVE ou window + ROW_NUMBER

### Stratégie FLOAT (Option C)

**Remplacer** `weight_within_family INTEGER` → `weight_within_family FLOAT`

**Backfill** :
```sql
weight_within_family = (ponderation / SUM_famille) * 100.0  -- sans ROUND
```

**Garantie** : Σ = 100.0 (exact avant affichage)

**Trade-off** : change type colonne (hors scope migration 101 actuelle)

### Décision CTO requise F3

**Question** : accepter Option A (ROUND + dérive ±N) ou migrer vers Option B/C ?

**Si Option A acceptée** :
- ✅ Migration 101 inchangée
- ⚠️  ScoringCore **DOIT** normaliser à la volée : `score_famille = Σ (score_critère × weight / Σ_réel_weights)`
- ⚠️  Doctrine opposable : dérive arrondi documentée l.101

**Si Option B/C requise** :
- ⛔ Migration 101 bloquée, réécriture backfill weight_within_family nécessaire

---

## FICHIERS LIVRÉS

### Décisions opposables

- ✅ `decisions/p32_chain_reality_check.md` — R1 chaîne Alembic prouvée
- ⏳ `decisions/p32_migration_101_null_probe.md` — R2 (à compléter post-exécution F2)
- ✅ `decisions/p32_r3_final_cto_verdict.md` — ce fichier

### Scripts

- ✅ `scripts/p32_r2_execute_all_f2_probes.py` — F2 probes Python
- ✅ `EXECUTE_F2_PROBES.ps1` — wrapper PowerShell CTO

### Migration corrigée

- ✅ `alembic/versions/101_p32_dao_criteria_scoring_schema.py` (down_revision corrigé)
- ⚠️  `alembic/versions/082_p32_dao_criteria_scoring_schema.py` (fichier créé par erreur, à ignorer/supprimer)

---

## VERDICT R3 — GO / NO-GO

### Statut actuel

⏳ **ATTENTE EXÉCUTION F2 CTO**

### GO conditionnel

✅ **GO MIGRATION 101 SI ET SEULEMENT SI** :

1. [x] **R1 chaîne Alembic** : corrigée (down_revision = '100_process_workspaces_zip_r2')
2. [ ] **R2 F2b probe** : COUNT ponderation IS NULL = 0 sur CASE-28b05d85
3. [ ] **F3 décision CTO** : accepter Option A (ROUND + dérive) OU réécrire backfill (Option B/C)
4. [ ] **GO CTO explicite** post-F2 + décision F3

### NO-GO si

⛔ **BLOQUANTS** :
- F2b COUNT > 0 sur CASE-28b05d85 (ponderation IS NULL) → données incomplètes, backfill impossible
- F3 CTO rejette Option A sans fournir réécriture Option B/C

---

## PROCHAINES ÉTAPES CTO

### 1. Exécuter F2 probes

```powershell
.\EXECUTE_F2_PROBES.ps1
```

**Output attendu** : counts NULLs par workspace (F2a/F2b/F2c)

### 2. Archiver résultats F2

Compléter `decisions/p32_migration_101_null_probe.md` avec output réel

### 3. Décision F3 invariant

**Choix CTO** :
- ✅ **Option A** : accepter dérive ROUND (migration 101 inchangée, ScoringCore normalise)
- ⛔ **Option B/C** : exiger Σ=100 exact (bloquer migration 101, réécrire backfill)

### 4. GO final

**Si F2b PASS + F3 Option A acceptée** :
```bash
alembic upgrade head
```

**Sinon** : corrections schéma/données requises avant migration

---

## INTERDICTIONS RESPECTÉES

- ✅ Pas de suppression `101_p32_dao_criteria_scoring_schema.py`
- ✅ Pas de renumérotation migration (reste 101)
- ✅ Pas de proposition 082/081 sans preuve (082 créé par erreur, chaîne réelle 100→101)
- ✅ Pas d'exécution Alembic
- ✅ Pas de psql (Python + with_railway_env)
- ✅ Pas d'hypothèse sur chaîne (lecture fichiers réels)

---

**R3 CLOSED — VERDICT CTO-READY REMIS — ATTENTE EXÉCUTION F2 + DÉCISION F3**
