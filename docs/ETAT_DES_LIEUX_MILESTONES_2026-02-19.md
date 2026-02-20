# État des Lieux — Milestones DMS V3.3.2

**Date :** 2026-02-19  
**Référence :** ADR-0003 §2.3 + ADR-0004 §2 — Séquence des phases (opposable)  
**Constitution :** V3.3.2 (freeze actif)  
**Commit HEAD :** `e1ab995` (Merge PR #84 — M-SCHEMA-CORE)  
**ADR-0004 :** ✅ GELÉ (tag v3.3.2-freeze-patch3)

---

## 📊 Vue d'ensemble

| Phase | Milestones | Complétés | En cours | À faire | Progression |
|-------|-----------|-----------|----------|---------|-------------|
| **Phase Zéro** | 6 livrables | ✅ 6/6 | - | - | **100%** |
| **Phase 0** | 4 | ✅ 2/4 | - | 2/4 | **50%** |
| **Phase 1** | 2 | ❌ 0/2 | - | 2/2 | **0%** |
| **Phase 2** | 3 | ❌ 0/3 | - | 3/3 | **0%** |
| **Phase 3** | 5 | ❌ 0/5 | - | 5/5 | **0%** |
| **Phase 4** | 3 | ❌ 0/3 | - | 3/3 | **0%** |
| **Phase 5** | 6 | ❌ 0/6 | - | 6/6 | **0%** |
| **Phase 6** | 2 | ❌ 0/2 | - | 2/2 | **0%** |
| **Phase 7** | 4 | ❌ 0/4 | - | 4/4 | **0%** |
| **TOTAL** | **35** | **2** | - | **33** | **~6%** |

---

## ✅ PHASE ZÉRO — Socle repo (COMPLÈTE)

**Gate :** ✅ `make test` → tous skipped (0 échec), CI verte sur main

| Livrable | Statut | Fichier | Vérification |
|----------|--------|---------|--------------|
| 0.1 Structure dossiers | ✅ | `src/`, `tests/`, `alembic/`, `docs/` | Présent |
| 0.2 requirements.txt figé | ✅ | `requirements.txt` | Versions exactes V3.3.2 |
| 0.3 src/db/connection.py | ✅ | `src/db/connection.py` | Helper psycopg2 synchrone |
| 0.4 Makefile | ✅ | `Makefile` | Commandes canoniques |
| 0.5 tests/conftest.py | ✅ | `tests/conftest.py` | Fixture db_conn psycopg2 raw |
| 0.6 alembic/env.py | ✅ | `alembic/env.py` | Configuré DATABASE_URL |

**✅ Phase Zéro : COMPLÈTE** — Prêt pour milestones métier

---

## 🔄 PHASE 0 — Milestones fondations

### ✅ M-DOCS-CORE (DONE)

**Durée estimée :** 2-3 jours  
**Statut :** ✅ **COMPLÉTÉ** (PR #83 mergée le 2026-02-19)  
**Commit :** `29b5120` — Merge pull request #83  
**Référence :** ADR-0004 §2 — Phase 0 corrigée

**Livrables :**
- ✅ `docs/ARCHITECTURE.md` — Architecture complète V3.3.2
- ✅ `docs/GLOSSAIRE.md` — Glossaire des termes DMS
- ✅ `docs/CONTRIBUTING.md` — Guide de contribution

**Fichier .done :** ✅ **CRÉÉ** — `.milestones/M-DOCS-CORE.done`

---

### ✅ M-SCHEMA-CORE (DONE)

**Durée estimée :** Non spécifiée dans ADR-0003 (ajouté via ADR-0004)  
**Statut :** ✅ **COMPLÉTÉ** (PR #84 mergée le 2026-02-19)  
**Commit :** `e1ab995` — Merge pull request #84  
**Référence :** ADR-0004 §2 — Phase 0 corrigée

**Séquence Phase 0 selon ADR-0004 §2 :**
1. ✅ M-SCHEMA-CORE — DONE (mergé 2026-02-19)
2. ✅ M-DOCS-CORE — DONE (mergé 2026-02-19)
3. ⏳ M-EXTRACTION-ENGINE — PROCHAIN MILESTONE
4. ⏳ M-EXTRACTION-CORRECTIONS

**Livrables créés :**
- ✅ `alembic/versions/011_add_missing_schema.py` — Migration tables `dictionary` et `market_data`
- ✅ `docs/SCHEMA.md` — Documentation schéma DB
- ✅ `.milestones/M-SCHEMA-CORE.done` — Fichier de complétion

**Exception documentée (ADR-0004 §4) :**
- Nommage migration `011_add_missing_schema.py` non conforme ADR-0003 §3.2
- Acceptée par exception documentée (migration déjà mergée, principe de stabilité)
- Toutes migrations futures doivent respecter convention stricte

---

### ⏳ M-EXTRACTION-ENGINE (PROCHAIN MILESTONE)

**Durée estimée :** 3-4 jours  
**Statut :** ⏳ **PROCHAIN MILESTONE**  
**Prérequis :** ✅ M-SCHEMA-CORE.done + ✅ M-DOCS-CORE.done

**Livrables attendus (ADR-0003 §2.2) :**
1. Migration Alembic (si tables manquantes)
2. Tests DB-level (`tests/db_integrity/`)
3. Service Python (`src/couche_a/extraction/`)
4. Endpoints FastAPI
5. Tests API
6. `.milestones/M-EXTRACTION-ENGINE.done`

**État actuel :**
- Migration `002_add_couche_a.py` contient tables `offers`, `documents`, `extractions`
- Code extraction existant dans `src/` (à vérifier conformité V3.3.2)

---

### ❌ M-EXTRACTION-CORRECTIONS (À FAIRE)

**Durée estimée :** 2 jours  
**Statut :** ❌ **NON COMMENCÉ**  
**Prérequis :** M-EXTRACTION-ENGINE.done

**Règles spéciales (ADR-0003 §3.3) :**
- Trigger `prevent_correction_mutation` dans migration
- Tests DB-level OBLIGATOIRES : `pytest tests/db_integrity/test_triggers_db_level.py -v`
- Vue `structured_data_effective` calculée à la volée (jamais matérialisée)

---

## ❌ PHASE 1 — Normalisation & critères

### ❌ M-CRITERIA-TYPING (À FAIRE)

**Durée estimée :** 2 jours  
**Statut :** ❌ **NON COMMENCÉ**  
**Prérequis :** M-EXTRACTION-CORRECTIONS.done

**État actuel :**
- Migration `006_criteria_types.py` existe — à vérifier conformité V3.3.2

---

### ❌ M-NORMALISATION-ITEMS (À FAIRE) ⚠️ MILESTONE CRITIQUE

**Durée estimée :** 5-7 jours  
**Statut :** ❌ **NON COMMENCÉ**  
**Prérequis :** M-CRITERIA-TYPING.done

**Règles spéciales (ADR-0003 §3.3) :**
- Dictionnaire seedé via migration Alembic dédiée (jamais script Python ad-hoc)
- Seed idempotent : `INSERT ... ON CONFLICT DO NOTHING`
- **9 familles obligatoires** avant .done :
  - `carburants`, `construction_liants`, `construction_agregats`,
  - `construction_fer`, `vehicules`, `informatique`,
  - `alimentation`, `medicaments`, `equipements`
- Minimum par famille : **5 items × 3 aliases**
- Tests bloquants :
  - `test_dict_minimum_coverage.py`
  - `test_aliases_mandatory_sahel.py`

**État actuel :**
- Table `dictionary` définie dans `0001_init_schema.py` et `011_add_missing_schema.py`
- **⚠️ Pas de seed migration** — dictionnaire vide

---

## ❌ PHASE 2 — Scoring & comité

### ❌ M-SCORING-ENGINE (À FAIRE)

**Durée estimée :** 3-4 jours  
**Statut :** ❌ **NON COMMENCÉ**  
**Prérequis :** M-NORMALISATION-ITEMS.done

**Règles spéciales (ADR-0003 §3.3) :**
- Dès que `.milestones/M-SCORING-ENGINE.done` existe, test AST `test_couche_a_b_boundary.py` s'active automatiquement
- Vérifier localement avant créer .done : `pytest tests/invariants/test_couche_a_b_boundary.py -v`

**État actuel :**
- Migration `007_add_scoring_tables.py` existe
- Migration `009_add_supplier_scoring_tables.py` existe
- Code scoring existant dans `src/` (à vérifier conformité V3.3.2)

---

### ❌ M-SCORING-TESTS-CRITIQUES (À FAIRE)

**Durée estimée :** 2 jours  
**Statut :** ❌ **NON COMMENCÉ**  
**Prérequis :** M-SCORING-ENGINE.done

---

### ❌ M-COMMITTEE-CORE (À FAIRE)

**Durée estimée :** 3 jours  
**Statut :** ❌ **NON COMMENCÉ**  
**Prérequis :** M-SCORING-TESTS-CRITIQUES.done

**Règles spéciales (ADR-0003 §3.3) :**
- Deux triggers obligatoires dans migration :
  - `prevent_committee_unlock` (LOCK irréversible)
  - `enforce_committee_lock` (membres immuables post-LOCK)
- Tests DB-level OBLIGATOIRES : `pytest tests/db_integrity/test_lock_committee_db_level.py -v`
- Si un seul test rouge → PR BLOQUÉE

---

## ❌ PHASE 3 — Génération & pipeline

| Milestone | Durée | Statut | Prérequis |
|-----------|-------|--------|-----------|
| M-CBA-TEMPLATES | 1 jour | ❌ | M-COMMITTEE-CORE.done |
| M-PV-TEMPLATES | 1 jour | ❌ | M-CBA-TEMPLATES.done |
| M-CBA-GEN | 2 jours | ❌ | M-PV-TEMPLATES.done |
| M-PV-GEN | 2 jours | ❌ | M-CBA-GEN.done |
| M-PIPELINE-A-E2E | 2-3 jours | ❌ | M-PV-GEN.done |

**État actuel :**
- Code génération existant dans `src/` (à vérifier conformité V3.3.2)

---

## ❌ PHASE 4 — Sécurité & traçabilité

| Milestone | Durée | Statut | Prérequis |
|-----------|-------|--------|-----------|
| M-SECURITY-CORE | 3 jours | ❌ | M-PIPELINE-A-E2E.done |
| M-TRACE-HISTORY | 2 jours | ❌ | M-SECURITY-CORE.done |
| M-CI-INVARIANTS | 1 jour | ❌ | M-TRACE-HISTORY.done |

**État actuel :**
- Migration `004_users_rbac.py` existe (auth + RBAC)
- Migration `010_enforce_append_only_audit.py` existe (audit)

---

## ❌ PHASE 5 — Couche B & Market Signal

| Milestone | Durée | Statut | Prérequis |
|-----------|-------|--------|-----------|
| M-MARKET-DATA-TABLES | 2 jours | ❌ | M-CI-INVARIANTS.done |
| M-MARKET-INGEST | 2 jours | ❌ | M-MARKET-DATA-TABLES.done |
| M-MARKET-SURVEY-WORKFLOW | 3 jours | ❌ | M-MARKET-INGEST.done |
| M-MARKET-SIGNAL-ENGINE | 3-4 jours | ❌ | M-MARKET-SURVEY-WORKFLOW.done |
| M-CONTEXT-UI-PANEL | 2 jours | ❌ | M-MARKET-SIGNAL-ENGINE.done |
| M-DICT-FUZZY-MATCH | 2 jours | ❌ | M-CONTEXT-UI-PANEL.done |

**État actuel :**
- Migration `005_add_couche_b.py` existe (tables Couche B)
- Table `market_data` définie dans `0001_init_schema.py` et `011_add_missing_schema.py`
- **⚠️ CONFLIT POTENTIEL** : Double définition

---

## ❌ PHASE 6 — DevOps

| Milestone | Durée | Statut | Prérequis |
|-----------|-------|--------|-----------|
| M-MONITORING-OPS | 2 jours | ❌ | M-DICT-FUZZY-MATCH.done |
| M-DEVOPS-DEPLOY | 2 jours | ❌ | M-MONITORING-OPS.done |

---

## ❌ PHASE 7 — Produit & terrain

| Milestone | Durée | Statut | Prérequis |
|-----------|-------|--------|-----------|
| M10-UX-V2 | 5-7 jours | ❌ | M-DEVOPS-DEPLOY.done |
| M-UX-TEST-TERRAIN | 3 jours | ❌ | M10-UX-V2.done |
| M-ERP-AGNOSTIC-CHECK | 1 jour | ❌ | M-UX-TEST-TERRAIN.done |
| M-PILOT-EARLY-ADOPTERS | ongoing | ❌ | M-ERP-AGNOSTIC-CHECK.done |

---

## ⚠️ PROBLÈMES IDENTIFIÉS

### 1. Fichiers .done manquants

**Problème :** Aucun milestone n'est marqué `.done` dans `.milestones/`

**Impact :**
- Gates CI ne sont pas activés (ADR-0003 §4 — Gates GO/NO-GO)
- Impossible de suivre progression réelle
- Risque de violation ordre séquentiel

**Action requise :**
```bash
# Créer fichiers .done pour milestones complétés
touch .milestones/M-DOCS-CORE.done
# M-SCHEMA-CORE.done après résolution conflit migrations
```

---

### 2. Conflit migrations Alembic

**Problème :** Double définition tables `dictionary` et `market_data`

**Détails :**
- `0001_init_schema.py` définit `dictionary` et `market_data` (revision: 0001, down_revision: None)
- `011_add_missing_schema.py` définit aussi `dictionary` et `market_data` (revision: 011, down_revision: 010)
- Chaîne actuelle : `002` → `003` → `004` → `005` → ... → `011`
- Migration `0001` n'est **pas intégrée** à la chaîne

**Impact :**
- Risque d'erreur si migration 0001 appliquée après 011
- Schéma DB incohérent selon ordre d'application

**Action requise :**
1. Décider : garder `0001` ou `011` pour `dictionary` et `market_data`
2. Supprimer définition dupliquée
3. Vérifier chaîne Alembic : `alembic history`
4. Tester migrations : `alembic upgrade head` puis `alembic downgrade base`

---

### 3. ✅ ADR-0004 créé et gelé

**Statut :** ✅ **RÉSOLU** — ADR-0004 créé et gelé selon règles freeze

**Actions complétées :**
- ✅ ADR-0004 créé dans `docs/adrs/ADR-0004.md`
- ✅ Copie immuable dans `docs/freeze/v3.3.2/adrs/ADR-0004.md`
- ✅ SHA256 calculé et ajouté dans FREEZE_MANIFEST.md : `3add6013efd74a3cd58bcf15d1aa71801fd4941858c4200217be2fa18bb0c8b3`
- ✅ SHA256 ajouté dans SHA256SUMS.txt
- ✅ Tag git : `v3.3.2-freeze-patch3` (existant)
- ✅ Phase 0 corrigée documentée dans ADR-0004 §2
- ✅ Exception migration 011 documentée dans ADR-0004 §4

---

## 📋 ACTIONS IMMÉDIATES RECOMMANDÉES

### ✅ Priorité 0 — Conformité ADR-0003 (RÉSOLU)

**Statut :** ✅ **COMPLÉTÉ** — ADR-0004 créé et gelé selon règles freeze

**Actions complétées :**
1. ✅ ADR-0004 créé et validé
2. ✅ FREEZE_MANIFEST.md mis à jour avec SHA256 ADR-0004
3. ✅ Tag git `v3.3.2-freeze-patch3` vérifié (existant)
4. ✅ Copie immuable dans `docs/freeze/v3.3.2/adrs/ADR-0004.md`
5. ✅ SHA256SUMS.txt mis à jour

### Priorité 1 — Résoudre conflit migrations

1. **Audit chaîne Alembic complète**
   ```bash
   alembic history
   alembic current
   ```

2. **Décider stratégie :**
   - Option A : Supprimer `0001_init_schema.py`, garder `011_add_missing_schema.py`
   - Option B : Intégrer `0001` dans chaîne (modifier down_revision de 002)

3. **Tester migrations :**
   ```bash
   alembic upgrade head
   alembic downgrade base
   alembic upgrade head
   ```

### Priorité 2 — Créer fichiers .done

```bash
# Après résolution conflit migrations
touch .milestones/M-SCHEMA-CORE.done
touch .milestones/M-DOCS-CORE.done
```

### Priorité 3 — Vérifier conformité code existant

- Code extraction (`src/couche_a/extraction/`) conforme V3.3.2 ?
- Code scoring (`src/couche_a/scoring/`) conforme V3.3.2 ?
- Code génération (`src/couche_a/generation/`) conforme V3.3.2 ?
- Tests DB-level présents pour triggers ?

---

## 📈 MÉTRIQUES DE PROGRESSION

**Durées estimées (ADR-0003 §2.4) :**
- Phase Zéro : ✅ 1 jour (COMPLÈTE)
- Phase 0 : 7-9 jours (1/3 complété = ~33%)
- Phase 1 : 7-9 jours (0%)
- Phase 2 : 8-9 jours (0%)
- Phase 3 : 8-9 jours (0%)
- Phase 4 : 6 jours (0%)
- Phase 5 : 14-16 jours (0%)
- Phase 6 : 4 jours (0%)
- Phase 7 : 9-11 jours + ongoing (0%)

**TOTAL estimé restant :** 63-81 jours ouvrés (séquentiel strict)

**Progression actuelle :** ~3% (1 milestone sur 34 selon ADR-0003)

**⚠️ NOTE :** M-SCHEMA-CORE existe mais n'est pas dans ADR-0003 — nécessite ADR-0004

---

## 🔍 RÉFÉRENCES

- **Constitution :** `docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md`
- **Plan exécution :** `docs/freeze/v3.3.2/adrs/ADR-0003.md`
- **Phase 0 corrigée :** `docs/freeze/v3.3.2/adrs/ADR-0004.md`
- **Milestones :** `docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md`
- **Architecture :** `docs/ARCHITECTURE.md`
- **Schéma DB :** `docs/SCHEMA.md`

---

*© 2026 — Decision Memory System — État des Lieux Milestones V3.3.2*
