# AUDIT AGENT — DMS V2.1 COUCHE B PR REVIEW

**Date d'audit:** 10 février 2026 14:20 UTC  
**Agent:** AUDIT (Guardrails & CI Fix)  
**Cible:** Couche B PR Review + CI stabilisation  
**Mode:** Merge-blocking audit strict  

---

## (1) VERDICT

**MERGE BLOCKED — NO COUCHE B IMPLEMENTATION FOUND**

Aucun code Couche B n'existe dans le repository. La PR "audit Couche B" ne peut pas auditer un travail inexistant.

---

## (2) LISTE BLOQUANTS

### [BLOCKER-01] Absence totale d'implémentation Couche B
- **Fichier:** `src/couche_b/*` (NON EXISTANT)
- **Raison:** Aucun module, migration, modèle ou resolver Couche B trouvé
- **Impact:** Constitution V2.1 § 3 non respectée - pas de market intelligence
- **Action:** Créer structure minimale Couche B selon spec Constitution

### [BLOCKER-02] Base de données SQLite au lieu de PostgreSQL
- **Fichier:** `main.py:38`
- **Raison:** `DB_PATH = DATA_DIR / "dms.sqlite3"` - SQLite utilisé, PostgreSQL requis
- **Impact:** Violation Constitution V2.1 § 1.2 - PostgreSQL obligatoire en prod
- **Action:** Migration vers PostgreSQL + SQLAlchemy 2.0 Core async

### [BLOCKER-03] Aucune migration Alembic
- **Fichier:** `alembic/*` (NON EXISTANT)
- **Raison:** Pas de gestion de migrations de schéma
- **Impact:** Impossible de déployer/versionner le schéma Couche B
- **Action:** Initialiser Alembic + créer migration 001_couche_b_schema

### [BLOCKER-04] Absence de fichier requirements_v2.txt
- **Fichier:** `requirements_v2.txt` (NON EXISTANT)
- **Raison:** Dépendances Couche B manquantes (SQLAlchemy, asyncpg, psycopg)
- **Impact:** CI ne peut pas installer les dépendances requises
- **Action:** Créer requirements_v2.txt ou mettre à jour requirements.txt (si TODO explicite existe)

### [BLOCKER-05] Schéma Couche B incomplet
- **Tables manquantes:** vendors, vendor_aliases, vendor_events, items, item_aliases, units, unit_aliases, geo_master, geo_aliases, market_signals (10 tables)
- **Raison:** Aucune table Couche B n'existe
- **Impact:** Impossible de stocker market intelligence
- **Action:** Créer migration avec les 10 tables exactes selon Constitution § 3.3

### [BLOCKER-06] Absence de resolvers (canonical → alias → fuzzy)
- **Fichier:** `src/couche_b/resolvers.py` (NON EXISTANT)
- **Raison:** Pas de logique de résolution d'entités
- **Impact:** Impossible de normaliser vendors/items/units/geo
- **Action:** Implémenter resolvers selon Constitution § 5.2

### [BLOCKER-07] Pas d'intégration async/await
- **Fichier:** `src/couche_b/*` (NON EXISTANT)
- **Raison:** Aucun code async trouvé
- **Impact:** Constitution exige async/await partout (pas de sync fallback)
- **Action:** Implémenter toutes les fonctions DB en async

### [BLOCKER-08] Violation anti-collision: absence src/db.py
- **Fichier:** `src/db.py` (NON EXISTANT - mais requis pour Couche B)
- **Raison:** Pas de module DB centralisé pour Couche B
- **Impact:** Pas de connexion PostgreSQL
- **Action:** Créer src/db.py UNIQUEMENT si pas déjà existant (règle: INTERDIT de modifier si existe)

### [BLOCKER-09] CI: ModuleNotFoundError probable
- **Fichier:** `.github/workflows/ci.yml:34`
- **Raison:** Workflow utilise `pip install -r requirements.txt` mais manque dépendances Couche B
- **Impact:** CI échouera dès qu'on ajoute imports Couche B
- **Action:** Vérifier requirements.txt inclut SQLAlchemy, asyncpg, psycopg

### [BLOCKER-10] Absence de tests Couche B
- **Fichier:** `tests/couche_b/*` (NON EXISTANT)
- **Raison:** Aucun test pour resolvers, migrations, schéma
- **Impact:** Impossible de valider conformité Constitution
- **Action:** Créer tests minimaux: test_schema.py, test_resolvers.py, test_migrations.py

### [BLOCKER-11] Structure package incorrecte (PYTHONPATH)
- **Fichier:** `src/__init__.py` (probablement MANQUANT)
- **Raison:** `ModuleNotFoundError: No module named 'src'` mentionné
- **Impact:** Imports `from src.couche_b import *` échoueront
- **Action:** Vérifier src/__init__.py existe, ajouter PYTHONPATH ou packaging

### [BLOCKER-12] Aucun seed data
- **Fichier:** Migrations seed data (NON EXISTANT)
- **Raison:** Constitution § 4.2-4.5 spécifie seed data obligatoire (vendors Mali, items, units, geo)
- **Impact:** Base vide = inutilisable en production
- **Action:** Ajouter seed data dans migration ou script séparé

---

## (3) PATCHLIST (Checklist exécutable)

### Phase 1: Infrastructure Database (CRITIQUE)

- [ ] **P1.1** Créer `alembic/` structure
  - Fichier: `alembic.ini`
  - Fichier: `alembic/env.py` (NOUVEAU, pas modification)
  - Fichier: `alembic/script.py.mako`

- [ ] **P1.2** Créer migration 001: schéma Couche B
  - Fichier: `alembic/versions/001_create_couche_b_schema.py`
  - Contenu: 10 tables exactes (vendors, items, units, geo_master, market_signals + aliases/events)
  - Contenu: Indexes requis (item_id+geo_id+date, vendor_id+date, source_type+ref)
  - Contenu: CHECK constraints pour ENUMs

- [ ] **P1.3** Créer `src/db.py` (connexion PostgreSQL)
  - Fichier: `src/db.py` (NOUVEAU, pas modification)
  - Contenu: SQLAlchemy 2.0 Core async engine
  - Contenu: async_session factory
  - Contenu: Table() definitions (pas ORM)
  - Règle: AUCUN sync fallback

### Phase 2: Models & Resolvers (COUCHE B CORE)

- [ ] **P2.1** Créer `src/couche_b/__init__.py`
  - Fichier: `src/couche_b/__init__.py`

- [ ] **P2.2** Créer `src/couche_b/models.py`
  - Fichier: `src/couche_b/models.py`
  - Contenu: Table() definitions SQLAlchemy Core (vendors, items, units, geo, signals)

- [ ] **P2.3** Créer `src/couche_b/resolvers.py`
  - Fichier: `src/couche_b/resolvers.py`
  - Contenu: `resolve_vendor(name: str) -> Optional[str]` (canonical → alias → fuzzy)
  - Contenu: `resolve_item(desc: str) -> Optional[str]`
  - Contenu: `resolve_unit(text: str) -> Optional[str]`
  - Contenu: `resolve_geo(location: str) -> Optional[str]`
  - Contenu: `propose_new_vendor(name: str, status='proposed') -> str` (pattern propose-only)
  - Règle: Tout en async/await

- [ ] **P2.4** Créer `src/couche_b/signals.py`
  - Fichier: `src/couche_b/signals.py`
  - Contenu: `async def record_market_signal()` - ingestion post-décision
  - Contenu: `async def import_mercurials()` - import CSV
  - Règle: Non-bloquant (async task)

### Phase 3: Requirements & Dependencies

- [ ] **P3.1** Vérifier `requirements.txt` pour TODO existant
  - Action: Chercher "TODO" ou "FIXME" dans requirements.txt
  - Si TODO existe: Mettre à jour avec dépendances Couche B
  - Si PAS de TODO: CRÉER `requirements_couche_b.txt` séparé (ne PAS modifier requirements.txt)

- [ ] **P3.2** Dépendances Couche B requises:
  ```
  sqlalchemy==2.0.27
  alembic==1.13.1
  psycopg[binary,pool]==3.1.18
  asyncpg==0.29.0
  ```

### Phase 4: Tests (Validation)

- [ ] **P4.1** Créer `tests/couche_b/test_schema.py`
  - Test: Migration 001 applique toutes les tables
  - Test: Indexes créés correctement
  - Test: CHECK constraints valides

- [ ] **P4.2** Créer `tests/couche_b/test_resolvers.py`
  - Test: resolve_vendor() trouve alias exacte
  - Test: resolve_vendor() trouve fuzzy match (Levenshtein)
  - Test: propose_new_vendor() crée status='proposed'
  - Test: resolve_item(), resolve_unit(), resolve_geo()

- [ ] **P4.3** Créer `tests/couche_b/test_signals.py`
  - Test: record_market_signal() insère signal valide
  - Test: Contraintes FK respectées (vendor_id, item_id, geo_id)

### Phase 5: Seed Data

- [ ] **P5.1** Créer `alembic/versions/002_seed_couche_b_data.py`
  - Seed: Vendors Mali (SOGELEC, SOMAPEP, COVEC) - § 4.2
  - Seed: Items communs (Ciment, Fer, Riz) - § 4.3
  - Seed: Units standard (kg, L, m, sac, pièce) - § 4.4
  - Seed: Geo Mali (Bamako, Gao, Tombouctou, Mopti, etc.) - § 4.5

### Phase 6: CI Fix

- [ ] **P6.1** Vérifier `src/__init__.py` existe
  - Fichier: `src/__init__.py` (créer si manquant)

- [ ] **P6.2** Fix PYTHONPATH si nécessaire
  - Option A: Ajouter `export PYTHONPATH=$PYTHONPATH:$(pwd)` dans CI workflow (SI et SEULEMENT SI autorisé)
  - Option B: Créer `pyproject.toml` avec `[tool.setuptools]` package discovery (préféré)

- [ ] **P6.3** Workflow: PostgreSQL service
  - Fichier: `.github/workflows/ci.yml`
  - Action: Ajouter service PostgreSQL container (si nécessaire pour tests)
  - **ATTENTION:** Docker exit 125 mentionné - probablement conflit port ou permissions
  - Solution minimale: Tester avec PostgreSQL local ou mock si service CI échoue

### Phase 7: Anti-Collision Verification

- [ ] **P7.1** Vérifier AUCUN fichier interdit modifié
  - `src/db.py` - SI existe déjà: REVERT toute modification
  - `alembic/env.py` - SI existe déjà: REVERT toute modification
  - `main.py` - Vérifier pas de modification sauf si TODO explicite
  - `requirements*.txt` - Vérifier pas de modification sauf si TODO explicite

---

## (4) COMMAND SEQUENCE (Copiable)

```bash
# S1 — INSPECTION FICHIERS MODIFIÉS
echo "=== S1: Inspection fichiers modifiés ==="
git status
git diff --name-only origin/main..HEAD || echo "No diff available"
find . -path "./src/couche_b*" -o -path "./alembic*" | head -20
echo ""

# S2 — CONSTITUTION DIFF CHECK
echo "=== S2: Constitution vs implémentation ==="
echo "Tables requises (Constitution § 3):"
echo "  - couche_b.vendors"
echo "  - couche_b.vendor_aliases"
echo "  - couche_b.vendor_events"
echo "  - couche_b.items"
echo "  - couche_b.item_aliases"
echo "  - couche_b.units"
echo "  - couche_b.unit_aliases"
echo "  - couche_b.geo_master"
echo "  - couche_b.geo_aliases"
echo "  - couche_b.market_signals"
echo ""
echo "Tables trouvées dans migration 001:"
ls -la alembic/versions/*001* 2>/dev/null || echo "  AUCUNE MIGRATION TROUVÉE"
echo ""

# S3 — ASYNC/SQLALCHEMY COMPLIANCE
echo "=== S3: Async & SQLAlchemy compliance ==="
grep -r "async def" src/couche_b/ 2>/dev/null || echo "  AUCUN CODE ASYNC TROUVÉ"
grep -r "from sqlalchemy" src/couche_b/ 2>/dev/null || echo "  AUCUN IMPORT SQLALCHEMY TROUVÉ"
grep -r "Table\(" src/couche_b/ 2>/dev/null || echo "  AUCUNE Table() SQLAlchemy Core TROUVÉE"
grep -r "class.*Base" src/couche_b/ 2>/dev/null && echo "  ❌ ORM DÉTECTÉ (interdit)" || echo "  ✓ Pas d'ORM"
echo ""

# S4 — CI & TOOLING CHECK
echo "=== S4: CI & Tooling ==="
echo "Requirements actuels:"
cat requirements.txt
echo ""
echo "Test import src:"
python3 -c "import sys; sys.path.insert(0, '.'); from src.mapping import supplier_mapper" 2>&1 || echo "  ❌ ModuleNotFoundError probable"
echo ""
echo "Vérification PYTHONPATH:"
ls -la src/__init__.py 2>/dev/null || echo "  ❌ src/__init__.py MANQUANT"
ls -la src/couche_b/__init__.py 2>/dev/null || echo "  ❌ src/couche_b/__init__.py MANQUANT"
echo ""

# S5 — PLAN CORRECTIF
echo "=== S5: Plan correctif minimal ==="
echo "1) REVERT fichiers interdits (si modifiés):"
git diff main.py alembic/env.py src/db.py 2>/dev/null | head -5 && echo "  ⚠️  FICHIERS INTERDITS MODIFIÉS" || echo "  ✓ Aucun fichier interdit modifié"
echo ""
echo "2) Créer structure Couche B:"
echo "   [ ] alembic/versions/001_create_couche_b_schema.py"
echo "   [ ] src/couche_b/{__init__,models,resolvers,signals}.py"
echo "   [ ] src/db.py (si n'existe pas)"
echo ""
echo "3) Tests & CI:"
echo "   [ ] tests/couche_b/test_*.py"
echo "   [ ] Fix PYTHONPATH (src/__init__.py + pyproject.toml)"
echo "   [ ] Vérifier requirements.txt ou créer requirements_couche_b.txt"
echo ""

# VALIDATION FINALE
echo "=== VALIDATION FINALE ==="
python3 -m compileall . -q && echo "✓ Compilation OK" || echo "❌ Compilation FAILED"
python3 tests/test_corrections_smoke.py && echo "✓ Test smoke OK" || echo "❌ Test smoke FAILED"
python3 tests/test_partial_offers.py && echo "✓ Test partial offers OK" || echo "❌ Test partial FAILED"
echo ""
echo "AUDIT TERMINÉ — Voir PATCHLIST ci-dessus pour actions correctives."
```

---

## RÉSUMÉ EXÉCUTIF

### Statut actuel
- ✅ Couche A fonctionnelle (main.py + SQLite)
- ❌ Couche B: **0% implémentée**
- ❌ PostgreSQL: **Non utilisé** (SQLite uniquement)
- ❌ Migrations: **Absentes**
- ❌ Tests Couche B: **Absents**

### Décision merge
**MERGE BLOCKED** jusqu'à implémentation minimale Couche B selon PATCHLIST.

### Recommandation
Créer une nouvelle PR "Couche B Implementation" avec les 12 blockers résolus, en respectant strictement les garde-fous:
- Ne PAS modifier: main.py, src/db.py (si existe), alembic/env.py (si existe), requirements.txt (sauf TODO)
- Ne PAS toucher Couche A (src/couche_a/**, templates/**, static/**)
- Implémenter UNIQUEMENT Couche B dans `src/couche_b/`

### Prochaines étapes
1. Agent Couche B: Implémenter selon PATCHLIST (Phase 1-5)
2. Agent CI: Fix PYTHONPATH + requirements (Phase 6)
3. Re-audit: Vérifier conformité Constitution V2.1
4. Merge si tous blockers résolus

---

**Fin de l'audit — Agent AUDIT**
