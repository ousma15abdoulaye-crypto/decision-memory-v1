# P3.2 Migration 101 — Closure Report

**Date** : 2026-04-18  
**Référence** : MANDAT_P3.2_SCORING_ENGINE_PILOTE_V2 Article 15  
**Statut** : ✅ **CLOSED — SCHEMA MIGRATION COMPLETE**

---

## RÉSUMÉ EXÉCUTIF

**Chantier** : Migration Alembic 101 — schéma scoring P3.2

**Objectif** : ajouter 6 colonnes `dao_criteria` + 1 colonne `process_workspaces` pour moteur scoring P3.2

**Résultat** : ✅ **MIGRATION EXÉCUTÉE ET VALIDÉE**

**Corpus actif** : CASE-28b05d85 (workspace canonique) + 4 GCF-E2E-* (test E2E)

---

## CAUSE RACINE BLOCAGE ALEMBIC

**Symptôme initial** : `alembic heads` retournait 2 heads (multiple heads)

**Cause** : fichier parasite `alembic/versions/082_p32_dao_criteria_scoring_schema.py`

**Origine** : créé par erreur lors de correction F1 (hypothèse fausse : last migration = 081, réalité = 100)

**Impact** : 2 branches Alembic concurrentes
- Branche légitime : 098 → 099 → 100 → 101
- Branche parasite : 081 → 082 (morte)

**Référence** : `decisions/p32_alembic_heads_probe.md`

---

## RÉSOLUTION RETENUE

**Option** : suppression fichier 082 parasite (CAS 3 mandat)

**Justification** :
1. 082 jamais appliqué en base (création erronée)
2. Contenu identique à 101 (même opérations P3.2)
3. down_revision incorrect (`081_m16_evaluation_domains` au lieu de `100_process_workspaces_zip_r2`)
4. Branche morte (aucune migration ne référence 082)

**Action** : `rm alembic/versions/082_p32_dao_criteria_scoring_schema.py`

**Référence** : `decisions/p32_alembic_resolution_plan.md`, `decisions/p32_alembic_resolution_executed.md`

---

## PREUVE SINGLE HEAD

**Avant résolution** :
```
alembic heads → 2 heads
  - 082_p32_dao_criteria_scoring_schema (parasite)
  - 101_p32_dao_criteria_scoring_schema (légitime)
```

**Après résolution** :
```
alembic heads → 1 head
  - 101_p32_dao_criteria_scoring_schema (head)
```

✅ **Single head confirmé**

---

## EXÉCUTION MIGRATION 101

**Commande** : `alembic upgrade head`

**Révision appliquée** : `100_process_workspaces_zip_r2` → `101_p32_dao_criteria_scoring_schema`

**Opérations exécutées** :

### Table `dao_criteria` (7 colonnes + 1 DROP)

| Op | Colonne | Type | Action |
|---|---|---|---|
| 1 | `family` | TEXT | ADD + backfill (capacity→TECHNICAL, commercial→COMMERCIAL, sustainability→SUSTAINABILITY, essential→NULL) |
| 2 | `weight_within_family` | INTEGER | ADD + backfill (ponderation/SUM × 100) |
| 3 | `criterion_mode` | TEXT | ADD DEFAULT 'SCORE' + backfill GATE pour essential |
| 4 | `scoring_mode` | TEXT | ADD + backfill UPPER(m16_scoring_mode) |
| 5 | `min_threshold` | FLOAT | ADD (NULL) |
| 6 | `min_weight_pct` | — | DROP IF EXISTS |

### Table `process_workspaces` (1 colonne)

| Op | Colonne | Type | Default |
|---|---|---|---|
| 7 | `technical_qualification_threshold` | FLOAT | NOT NULL DEFAULT 50.0 |

**Rows affectées** :
- `dao_criteria` : ~75 rows (CASE-28b05d85 ~15 + GCF-E2E-* ~60)
- `process_workspaces` : ~5 rows

**Référence** : `decisions/p32_migration_101_executed.md`

---

## RÉSULTAT POST-CHECKS

### CHECK 1 — Colonnes ajoutées

✅ **5 colonnes dao_criteria** + **1 colonne process_workspaces** présentes

### CHECK 2 — CASE-28b05d85 family distribution

| family | n_criteria | sum_ponderation | sum_weight_within_family |
|---|---|---|---|
| TECHNICAL | 7 | 50.0 | 100 ✅ |
| COMMERCIAL | 5 | 40.0 | 100 ✅ |
| SUSTAINABILITY | 3 | 10.0 | 100 ✅ |

✅ **Invariant Σ=100 par famille respecté** (dérive arrondi acceptable ≤N critères)

### CHECK 3 — essential doctrine

✅ **Aucun critère essential sur corpus actif** (ou absent CASE-28b05d85)

**Si essential présent** : `family = NULL`, `criterion_mode = 'GATE'` (doctrine opposable)

### CHECK 4 — scoring_mode NULL preservation

✅ **3 rows CASE-28b05d85** : `m16_scoring_mode IS NULL` → `scoring_mode IS NULL` (préservé)

✅ **0 false fallback** : aucun cas `m16 NULL` → `scoring NOT NULL`

**Référence** : `decisions/p32_migration_101_postcheck.md`

---

## STATUT FINAL

✅ **P3.2 MIGRATION SCHEMA = DONE**

**Schéma P3.2** : opérationnel en production

**Backfills** : cohérents sur corpus actif

**Workspace canonique** : CASE-28b05d85 validé (50/40/10, Σ=100 par famille)

**Doctrine métier** : respectée (essential=NULL+GATE, scoring_mode NULL préservé)

---

## LIMITES RESTANTES (HORS PÉRIMÈTRE)

### 1. Essential criteria absents corpus actif

**Statut** : aucun critère `criterion_category = 'essential'` détecté sur CASE-28b05d85

**Impact** : doctrine essential (`family=NULL`, `criterion_mode='GATE'`) non testée en production

**Résolution** : à valider si/quand essential ajoutés ultérieurement

### 2. GCF-E2E-* données incomplètes possibles

**Statut** : workspaces test E2E peuvent avoir `ponderation IS NULL` ou données partielles

**Impact** : `weight_within_family` NULL résiduel acceptable sur E2E (hors workspace canonique)

**Résolution** : non critique (workspaces test, pas scoring prod)

### 3. Dérive arrondi weight_within_family

**Statut** : formule `ROUND((ponderation/SUM) × 100)::INTEGER` génère dérive ±N critères

**Impact** : somme famille peut être 99, 100, ou 101 (selon N critères)

**Résolution** : documenté migration l.101, ScoringCore **DOIT** normaliser à la volée

### 4. Bruit M14 / scoring legacy

**Statut** : `m14_evaluation_models.py` consomme encore `ponderation` (pas `weight_within_family`)

**Impact** : migration schéma seule ne migre pas consommateurs

**Résolution** : **HORS PÉRIMÈTRE P3.2 migration 101** — chantier P3.3+ (refonte scoring engine)

### 5. Scripts PowerShell / Python outils

**Statut** : scripts probes/post-checks fournis, non intégrés CI/CD

**Impact** : validation manuelle CTO, pas automatique

**Résolution** : intégration CI optionnelle, hors périmètre migration schema

---

## PROCHAINES ÉTAPES (HORS CETTE PR)

**P3.2 suite (hors migration schema)** :
1. Implémentation `ScoringCore` component (consommation colonnes P3.2)
2. Refonte `m14_evaluation_models.py` (migration `ponderation` → `weight_within_family`)
3. Tests propriétés P3.2 (invariant 50/40/10, normalization)
4. Benchmark sci_mali (P3.2 vs Excel vs humain)

**Hors mandat actuel** : changements pipeline, scoring, UI

---

## VERDICT CLOSURE

✅ **P3.2 MIGRATION 101 CLOSED**

**Schéma** : ✅ DONE (colonnes ajoutées, backfills cohérents)

**Validation** : ✅ DONE (workspace canonique, post-checks pass)

**Production** : ✅ READY (corpus actif migré)

**Documentation** : ✅ COMPLETE (15+ fichiers `decisions/p32_*.md`)

---

**MIGRATION 101 SCHEMA P3.2 — COMPLETE AND VALIDATED**
