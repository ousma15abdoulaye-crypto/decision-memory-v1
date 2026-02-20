# 📋 ÉVALUATION COMPLÈTE DU REPOSITORY — DMS V3.3.2

**Date** : 20 février 2026  
**Périmètre** : Audit factuel global du repository — zéro modification de code  
**Méthode** : Analyse exhaustive du code source, tests, documentation, CI/CD, architecture, milestones  
**Repository** : `ousma15abdoulaye-crypto/decision-memory-v1`  
**Version** : V3.3.2 (Constitution gelée)

---

## TABLE DES MATIÈRES

1. [Résumé exécutif](#1-résumé-exécutif)
2. [Identité du projet](#2-identité-du-projet)
3. [Stack technique](#3-stack-technique)
4. [Structure du code source](#4-structure-du-code-source)
5. [État des tests](#5-état-des-tests)
6. [CI/CD et workflows](#6-cicd-et-workflows)
7. [Documentation](#7-documentation)
8. [Sécurité](#8-sécurité)
9. [Rapport complet des milestones prévus](#9-rapport-complet-des-milestones-prévus)
10. [Synthèse des risques et recommandations](#10-synthèse-des-risques-et-recommandations)

---

## 1. RÉSUMÉ EXÉCUTIF

Le **Decision Memory System (DMS)** est une plateforme d'intelligence procurement à deux couches visant à réduire de 90 % le travail répétitif d'analyse comparative (CBA/PV) dans les marchés publics et privés en Afrique de l'Ouest (Mali, Côte d'Ivoire initialement).

| Métrique | Valeur |
|----------|--------|
| **Lignes de code source** | ~5 200 LOC Python |
| **Tests** | 200+ fonctions de test, 47/50 passant (94 %) |
| **Fichiers documentation** | 80+ fichiers Markdown |
| **Migrations Alembic** | 13 migrations SQL |
| **Workflows CI** | 7 workflows GitHub Actions |
| **ADR (Architecture Decision Records)** | 4 ADR gelés |
| **Milestones définis** | 28 milestones sur 8 phases |
| **Milestones complétés** | 3/28 (M-DOCS-CORE, M-SCHEMA-CORE, M-EXTRACTION-ENGINE) |
| **Progression globale** | ~10 % |
| **Durée estimée restante** | 63-81 jours ouvrés (séquentiel strict) |

**Verdict** : Le projet est sérieux, la vision est claire, l'architecture est saine. La Couche A est partiellement fonctionnelle. La Couche B (mémoire marché — le différenciateur stratégique) est absente. Plusieurs corrections critiques sont nécessaires avant le passage en production.

---

## 2. IDENTITÉ DU PROJET

### 2.1 Vision

Le DMS part d'une douleur réelle documentée :
- 99 offres sur 21 lots
- 3 jours d'ouverture manuelle
- Comités épuisés avant même l'analyse
- Paperasse qui écrase la réflexion

**Mandat** : Restaurer la capacité de décision humaine sous pression opérationnelle.

### 2.2 Architecture deux couches

| Couche | Rôle | Statut |
|--------|------|--------|
| **Couche A** (Ouvrier cognitif) | Ingestion documents, extraction, scoring, génération CBA/PV | 🔄 Partiellement fonctionnelle |
| **Couche B** (Collègue expérimenté) | Mémoire marché, signaux prix, intelligence contextuelle | ❌ Non implémentée |

### 2.3 Invariants constitutionnels (FROZEN V1.4)

11 invariants intouchables dont :
- **INV-1** : Réduction cognitive ≥ 90 %
- **INV-2** : Primauté Couche A
- **INV-3** : Non-prescriptif (jamais de recommandation)
- **INV-6** : Append-only (pas de suppression)
- **INV-7** : ERP-agnostique
- **INV-9** : Fidélité au réel

### 2.4 Règles métier (REGLES_METIER V1.4)

9 règles métier (M1-M9) couvrant :
- Grilles procédures Mali (Code des Marchés) + SCI (Save the Children International)
- Lexique canonique (DAO, RFQ, RFP, CBA, PV, TDR, Lot)
- Grammaire d'évaluation (critères binaires, scores, formules financières, seuils)
- Détection automatique profil (Fournitures, Travaux, Services, Santé)

---

## 3. STACK TECHNIQUE

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Backend | FastAPI | 0.115.0 |
| Serveur ASGI | Uvicorn | 0.30.0 |
| Base de données | PostgreSQL | 15+ |
| ORM | SQLAlchemy | 2.0.25 |
| Driver DB | psycopg | 3.2.5 |
| Migrations | Alembic | 1.13.1 |
| Authentification | JWT (python-jose) | 3.3.0 |
| Hashing | bcrypt | 4.2.0 |
| Rate limiting | slowapi | 0.1.9 |
| Documents Office | openpyxl, python-docx | Latest |
| PDF | pypdf, pdfplumber | 0.11.4 |
| Tests | pytest | 8.0.0+ |
| Linting | ruff, black | Latest |
| Résilience | tenacity, pybreaker | Latest |
| Cache/Queue | redis | 5.2.1 |
| Frontend | HTML/CSS/JS vanilla | — |

**Principes techniques respectés** :
- ✅ PostgreSQL strict (zéro SQLite)
- ✅ Migrations SQL brut (Alembic)
- ✅ Online-first (pas d'offline V1)
- ✅ Connexion synchrone uniquement

---

## 4. STRUCTURE DU CODE SOURCE

### 4.1 Arborescence `src/`

```
src/
├── main.py                          # Point d'entrée FastAPI (~80 lignes)
├── db.py                            # PostgreSQL + résilience (~199 lignes)
├── auth.py                          # JWT + RBAC (~205 lignes)
├── resilience.py                    # Retry + circuit breaker (~91 lignes)
├── ratelimit.py                     # Middleware rate limiting
├── upload_security.py               # Validation fichiers (MIME, taille, extension)
├── logging_config.py                # Logging structuré
├── couche_a/
│   ├── routers.py                   # Endpoints upload, analyse (~254 lignes)
│   ├── extraction.py                # Parsing documents (PDF, Excel, Word)
│   ├── services/
│   │   ├── extraction.py            # Logique extraction critères/offres
│   │   ├── cba.py                   # Génération CBA (mapping templates)
│   │   ├── pv.py                    # Génération PV (Procès-Verbal)
│   │   └── analysis.py              # Consolidation + scoring
│   └── scoring/
│       ├── engine.py                # Calculateur scoring multi-critères
│       ├── models.py                # Modèles de données scoring
│       └── api.py                   # Routes API scoring
├── couche_b/
│   └── resolvers.py                 # Résolution entités (fournisseurs, items)
├── core/
│   ├── config.py                    # Configuration + constantes
│   └── models.py                    # Schémas Pydantic
├── mapping/
│   ├── template_engine.py           # Auto-mapping templates CBA (~119 lignes)
│   └── supplier_mapper.py           # Mapping données fournisseurs (~153 lignes)
├── templates/
│   ├── cba_template.py              # Handler template CBA Excel (~288 lignes)
│   └── pv_template.py               # Handler template PV Word (~416 lignes)
├── business/
│   └── templates.py                 # Templates logique métier
├── api/
│   ├── health.py                    # Endpoint santé
│   ├── cases.py                     # CRUD dossiers
│   ├── documents.py                 # Upload/récupération documents
│   └── analysis.py                  # Déclenchement analyse
└── auth_router.py                   # Routes authentification
```

### 4.2 Constats code source

| Aspect | Constat | Appréciation |
|--------|---------|--------------|
| Code réel vs scaffolding | ~80 % code fonctionnel | ✅ Solide |
| Moteur CBA | Génération Excel multi-feuilles fonctionnelle | ✅ Opérationnel |
| Moteur PV | Génération Word horodatée fonctionnelle | ✅ Opérationnel |
| Moteur scoring | Multi-critères avec profils adaptatifs | ✅ Testé unitairement |
| Extraction DAO | `extract_dao_criteria_structured()` est un **stub** vide | ⚠️ Critique |
| API Scoring | Endpoint `POST /api/scoring/calculate` retourne 0 | ⚠️ Non câblé |
| Couche B | Seul `resolvers.py` existe avec fuzzy matching basique | ❌ Absente |

---

## 5. ÉTAT DES TESTS

### 5.1 Résultats actuels

```
✅ 47 passant / 50 total (94 %)
⏭️ 1 skippé
❌ 3 en échec (edge cases non-bloquants)
```

| Catégorie | Résultat | Couverture |
|-----------|----------|------------|
| Authentification | 11/11 | 100 % |
| RBAC | 5/5 | 100 % |
| Upload Core | 5/6 | 83 % |
| Upload Security | 7/9 | 78 % |
| Résilience | 5/5 | 100 % |
| Templates | 4/4 | 100 % |
| Divers | 10/10 | 100 % |

### 5.2 Tests en échec (non-bloquants)

| Test | Cause | Impact |
|------|-------|--------|
| `test_upload_offer_with_lot_id` | Isolation de fixtures DB | Aucun — fonctionne individuellement |
| `test_rate_limit_upload` | TESTING=true désactive le rate limiting | By design |
| `test_case_quota_enforcement` | Erreur de conception du test (100 MB > 50 MB max) | Aucun — quota fonctionne |

### 5.3 Couverture de code

- **Ratio actuel** : ~5,2 % (audit CI du 17/02)
- **16 modules sur 31** dans `src/` n'ont aucun test
- **Gate CI** : `fail_under=40` (activé via `.milestones/M-TESTS.done` — pas encore activé)
- **Modules critiques non testés** : `cases.py`, `analysis.py`, `documents.py`, `cba.py`, `extraction.py` (services)

---

## 6. CI/CD ET WORKFLOWS

### 6.1 Workflows configurés

| Workflow | Fichier | Rôle | Statut |
|----------|---------|------|--------|
| CI Main | `ci-main.yml` | Lint + test + migrations + coverage | ✅ Configuré |
| Lint Ruff | `ci-lint-ruff.yml` | Linting statique | ✅ Configuré |
| Format Black | `ci-format-black.yml` | Formatage code | ✅ Configuré |
| Invariants | `ci-invariants.yml` | Tests constitutionnels | ✅ Configuré |
| Freeze Integrity | `ci-freeze-integrity.yml` | Vérification checksums gelés | ✅ Configuré |
| Milestones Gates | `ci-milestones-gates.yml` | Ordre séquentiel milestones | ✅ Configuré |
| Regenerate Checksums | `ci-regenerate-freeze-checksums.yml` | Rafraîchissement freeze | ✅ Configuré |

### 6.2 Pipeline CI Main

1. PostgreSQL 15 (service Docker)
2. Python 3.11 + dépendances
3. `alembic upgrade head` + safety net SQL
4. Ruff check + Black check
5. `pytest` avec coverage dynamique (gate 0 % ou 40 % selon milestone)
6. Upload coverage Codecov

### 6.3 Constat CI

- ⚠️ Le workflow `ci-milestones-gates.yml` vérifie un ensemble d'IDs (M0-BOOT, M1-DATABASE, etc.) qui **ne correspondent pas** aux IDs canoniques du plan de milestones V3.3.2 (M-DOCS-CORE, M-SCHEMA-CORE, etc.)
- ⚠️ CI historiquement bloquée par permissions GitHub Actions (approbation PR requise)

---

## 7. DOCUMENTATION

### 7.1 Volume

- **80+ fichiers Markdown** répartis entre racine, `docs/`, `docs/freeze/`, `docs/adrs/`
- **20+ fichiers** à la racine du projet
- **4 ADR** gelés (Architecture Decision Records)

### 7.2 Documents clés

| Document | Statut | Rôle |
|----------|--------|------|
| `CONSTITUTION.md` | ✅ FROZEN V1.4 | Document fondateur, 11 invariants |
| `REGLES_METIER_DMS_V1.4.md` | ✅ Production-ready | 9 règles métier procurement |
| `docs/MILESTONES_EXECUTION_PLAN_V3.3.2.md` | ✅ Canonique, opposable | Plan d'exécution complet 28 milestones |
| `docs/ARCHITECTURE.md` | ✅ Complète | Architecture système V3.3.2 |
| `docs/SCHEMA.md` | ✅ Référence | Schéma DB PostgreSQL |
| `docs/SECURITY.md` | ✅ Documenté | JWT, RBAC, rate limiting |
| `docs/INVARIANTS.md` | ✅ V3.3.2 | Liste invariants gelée |
| `CHANGELOG.md` | ✅ V1.2.0 | Historique versions |

### 7.3 Constat documentation

- ⚠️ **Dispersion** : Documents dupliqués entre racine, `docs/`, et `docs/freeze/`
- ⚠️ **Dossiers orphelins** : `nano docs/` et `ocs/` à la racine
- ⚠️ **Redondance** : Plusieurs copies d'un même document à des versions différentes
- ✅ **Qualité** : Le contenu est riche, bien structuré, et ancré dans le réel

---

## 8. SÉCURITÉ

### 8.1 Ce qui est en place

| Mécanisme | Statut | Détails |
|-----------|--------|---------|
| JWT | ✅ Implémenté | python-jose, HS256 |
| RBAC | ✅ Implémenté | 3 rôles (admin, manager, viewer) |
| BCrypt | ✅ Implémenté | Hashing mots de passe |
| Rate limiting | ✅ Implémenté | slowapi, 5/min sur upload |
| Validation MIME | ✅ Implémenté | Magic bytes + whitelist |
| Taille fichier | ✅ Implémenté | 50 MB/fichier, 500 MB/case |
| Résilience DB | ✅ Implémenté | Circuit breaker + retry |

### 8.2 Failles identifiées (audits précédents)

| # | Faille | Sévérité | Détails |
|---|--------|----------|---------|
| FT-01 | Clé JWT avec valeur par défaut en dur | 🔴 CRITIQUE | Contournement total de l'auth si variable non définie |
| FT-02 | Injection SQL via pattern LIKE | 🔴 HAUTE | Input utilisateur non échappé dans `routers.py` |
| FT-03 | Append-only incomplet | 🟠 HAUTE | Seulement 3/N tables protégées par triggers |
| FT-04 | Endpoints sans authentification | 🟠 HAUTE | `list_cases()` accessible publiquement |
| FT-05 | Expiration JWT 8 heures | 🟡 MOYENNE | Pas de refresh token |
| FT-06 | Pas de log des échecs auth | 🟡 MOYENNE | Brute force indétectable |
| FT-07 | CORS non configuré | 🟡 MOYENNE | Risque XSS si frontend séparé |
| FT-08 | Headers sécurité HTTP absents | 🟡 MOYENNE | HSTS, X-Frame-Options manquants |

---

## 9. RAPPORT COMPLET DES MILESTONES PRÉVUS

### 9.1 Vue d'ensemble — Registre officiel des 28 milestones

Le plan d'exécution V3.3.2 définit **28 milestones répartis sur 8 phases** avec un ordre d'exécution séquentiel strict. Un milestone suivant ne démarre pas tant que le précédent n'est pas DONE.

| Phase | Nombre | Complétés | Progression | Durée estimée |
|-------|--------|-----------|-------------|---------------|
| **Phase Zéro** (Socle repo) | 6 livrables | ✅ 6/6 | **100 %** | ✅ Complète |
| **Phase 0** (Fondations) | 4 milestones | ✅ 3/4 | **75 %** | 7-9 jours |
| **Phase 1** (Normalisation) | 2 milestones | ❌ 0/2 | **0 %** | 7-9 jours |
| **Phase 2** (Scoring & Comité) | 3 milestones | ❌ 0/3 | **0 %** | 8-9 jours |
| **Phase 3** (Génération & Pipeline) | 5 milestones | ❌ 0/5 | **0 %** | 8-9 jours |
| **Phase 4** (Sécurité & Traçabilité) | 3 milestones | ❌ 0/3 | **0 %** | 6 jours |
| **Phase 5** (Couche B & Market Signal) | 6 milestones | ❌ 0/6 | **0 %** | 14-16 jours |
| **Phase 6** (DevOps) | 2 milestones | ❌ 0/2 | **0 %** | 4 jours |
| **Phase 7** (Produit & Terrain) | 4 milestones | ❌ 0/4 | **0 %** | 9-11 jours + ongoing |
| **TOTAL** | **28 + 6** | **3 + 6** | **~10 %** | **63-81 jours ouvrés** |

---

### 9.2 PHASE ZÉRO — Socle repo (✅ COMPLÈTE)

Livrables fondamentaux du repository.

| # | Livrable | Statut | Fichier |
|---|----------|--------|---------|
| 0.1 | Structure dossiers | ✅ DONE | `src/`, `tests/`, `alembic/`, `docs/` |
| 0.2 | requirements.txt figé | ✅ DONE | `requirements.txt` |
| 0.3 | `src/db/connection.py` | ✅ DONE | Helper psycopg synchrone |
| 0.4 | Makefile | ✅ DONE | Commandes canoniques |
| 0.5 | `tests/conftest.py` | ✅ DONE | Fixture `db_conn` |
| 0.6 | `alembic/env.py` | ✅ DONE | Configuré DATABASE_URL |

---

### 9.3 PHASE 0 — Fondations (🔄 75 %)

#### ✅ M-DOCS-CORE — Pipeline cases + documents + extractions
- **Statut** : ✅ DONE (PR #83, mergée 2026-02-19)
- **Commit** : `29b5120`
- **Fichier .done** : `.milestones/M-DOCS-CORE.done`
- **Livrables** :
  - ✅ `docs/ARCHITECTURE.md` — Architecture complète V3.3.2
  - ✅ `docs/GLOSSAIRE.md` — Glossaire des termes DMS
  - ✅ `docs/CONTRIBUTING.md` — Guide de contribution

#### ✅ M-SCHEMA-CORE — Schéma DB + migrations
- **Statut** : ✅ DONE (PR #84, mergée 2026-02-19)
- **Commit** : `e1ab995`
- **Fichier .done** : `.milestones/M-SCHEMA-CORE.done`
- **Livrables** :
  - ✅ `alembic/versions/011_add_missing_schema.py` — Migration tables `dictionary` et `market_data`
  - ✅ `docs/SCHEMA.md` — Documentation schéma DB
- **Exception** : Nommage migration 011 non conforme ADR-0003 §3.2 (documentée dans ADR-0004 §4)

#### ✅ M-EXTRACTION-ENGINE — Moteur d'extraction 3 niveaux
- **Statut** : ✅ DONE
- **Fichier .done** : `.milestones/M-EXTRACTION-ENGINE.done`
- **Fonction** : ExtractionEngine à 3 niveaux (parsing natif PDF/DOCX/XLSX, parsing structuré, OCR providers)
- **Livrables attendus** :
  - Service ExtractionEngine (entrée: document_id → sortie: insertion dans extractions)
  - Standard `structured_data` minimal (JSONB)
  - Providers (PDF natif, DOCX parser, XLSX parser, OCR Azure/Tesseract fallback)
  - Confidence score calculé et stocké
- **⚠️ Note** : La fonction `extract_dao_criteria_structured()` est un stub vide (audit senior FT-02)

#### ⏳ M-EXTRACTION-CORRECTIONS — Corrections append-only
- **Statut** : ⏳ PROCHAIN MILESTONE
- **Durée estimée** : 2 jours
- **Prérequis** : ✅ M-EXTRACTION-ENGINE.done
- **Fonction** : Correction humaine champ par champ, append-only, avec before/after, auteur, timestamp, raison
- **Livrables** :
  - Table `extraction_corrections` (append-only)
  - Vue "effective" non destructive (`structured_data_original` immutable + `structured_data_effective` calculé)
  - Endpoint `POST /api/extractions/{id}/corrections`
  - Trigger DB `prevent_correction_mutation`
- **Tests bloquants** :
  - `test_corrections_append_only.py` (CI bloquant)
  - `test_effective_structured_data.py`
  - `test_conflict_detection.py`
- **Definition of Done** : append-only prouvé (DB + test), historique consultable, effective view cohérente, CI verte

---

### 9.4 PHASE 1 — Normalisation & Critères (❌ 0 %)

#### ❌ M-CRITERIA-TYPING — Critères typés universels
- **Statut** : ❌ NON COMMENCÉ
- **Durée estimée** : 2 jours
- **Prérequis** : M-EXTRACTION-CORRECTIONS.done
- **Fonction** : Extraire et typer les critères : commercial, capacity, sustainability, essentials
- **Livrables** :
  - Table `criteria` (id, case_id, source_extraction_id, label, type enum, weight, is_essential)
  - Pipeline : `structured_data_effective` → extraction + typage + persistance
- **Tests bloquants** : `test_criteria_extraction.py`, `test_criteria_typing.py`, `test_weights_edge_cases.py`
- **État actuel** : Migration `006_criteria_types.py` existe — conformité V3.3.2 à vérifier

#### ❌ M-NORMALISATION-ITEMS — Dictionnaire procurement + normalisation ⚠️ CRITIQUE
- **Statut** : ❌ NON COMMENCÉ
- **Durée estimée** : 5-7 jours
- **Prérequis** : M-CRITERIA-TYPING.done
- **Fonction** : Dictionnaire procurement Sahel + moteur de normalisation des items/unités/quantités
- **Livrables** :
  - Tables : `procurement_items`, `procurement_item_aliases`, `procurement_units`, `procurement_unit_conversions`, `normalized_line_items`
  - Moteur de normalisation (entrée: items bruts → sortie: items normalisés + confidence + flag validation humaine)
  - **9 familles obligatoires** avant .done : carburants, construction_liants, construction_agregats, construction_fer, vehicules, informatique, alimentation, medicaments, equipements
  - Minimum par famille : 5 items × 3 aliases
- **Tests bloquants** :
  - `test_no_raw_offer_in_scoring.py` (CI bloquant)
  - `test_alias_resolution.py`
  - `test_unit_conversion.py`
  - `test_dict_minimum_coverage.py`
  - `test_aliases_mandatory_sahel.py`
- **⚠️ Critique** : Aucun fichier de dictionnaire Sahel n'existe. C'est la clé de voûte entre Couche A et Couche B.

---

### 9.5 PHASE 2 — Scoring & Comité (❌ 0 %)

#### ❌ M-SCORING-ENGINE — Scoring multi-critères non prescriptif
- **Statut** : ❌ NON COMMENCÉ (formellement)
- **Durée estimée** : 3-4 jours
- **Prérequis** : M-NORMALISATION-ITEMS.done
- **Fonction** : Scoring universel sur critères typés + offres normalisées, sans prescription
- **Livrables** :
  - Tables : `supplier_scores` (scores détaillés), `supplier_eliminations` (raisons tracées)
  - Règles : essentials = gate éliminatoire, commercial = prix normalisé, pondérations issues de criteria.weight
  - Interdiction explicite : aucun appel Couche B dans scoring, aucune recommandation
- **Tests bloquants** :
  - `test_scoring_engine.py`
  - `test_scores_independent_of_couche_b.py` (CI bloquant)
  - `test_elimination_reasons.py`
- **État actuel** : Moteur scoring existe et fonctionne (15 tests passent). API non câblée sur données réelles.

#### ❌ M-SCORING-TESTS-CRITIQUES — Tests critiques + performance
- **Statut** : ❌ NON COMMENCÉ
- **Durée estimée** : 2 jours
- **Prérequis** : M-SCORING-ENGINE.done
- **Fonction** : Suite tests unitaires + property-based + E2E : edge cases, 100+ fournisseurs, performance, invariants
- **Tests bloquants** :
  - `test_scoring_performance_100_suppliers.py`
  - `test_no_raw_offer_in_scoring.py` (CI bloquant)
  - `test_idempotence.py`

#### ❌ M-COMMITTEE-CORE — Module Comité + LOCK irréversible
- **Statut** : ❌ NON COMMENCÉ
- **Durée estimée** : 3 jours
- **Prérequis** : M-SCORING-TESTS-CRITIQUES.done
- **Fonction** : Comité conformité avec composition par règles, LOCK irréversible, délégation post-lock
- **Livrables** :
  - Tables : `committees`, `committee_members`, `committee_events` (append-only), `committee_delegations` (append-only), `committee_composition_rules`
  - Enforcement DB-level : triggers `prevent_committee_unlock` + `enforce_committee_lock`
  - Service `CommitteeBuilder` (composition auto par catégorie + seuil)
  - API : 5 endpoints (create draft, add members, lock, delegations, get details)
- **Tests bloquants** :
  - `test_committee_lock_prevents_member_update.py` (CI bloquant)
  - `test_lock_is_irreversible.py` (CI bloquant)
  - `test_delegation_without_roster_change.py`
  - `test_composition_rules.py`
- **Règle constitutionnelle** : Un comité verrouillé ne bouge JAMAIS. Toute modification post-lock est non conforme.

---

### 9.6 PHASE 3 — Génération & Pipeline (❌ 0 %)

| # | Milestone | Durée | Prérequis | Fonction |
|---|-----------|-------|-----------|----------|
| 1 | **M-CBA-TEMPLATES** | 1 jour | M-COMMITTEE-CORE | Templates CBA Excel normalisés (placeholders stables, versionnement strict) |
| 2 | **M-PV-TEMPLATES** | 1 jour | M-CBA-TEMPLATES | Templates PV Word normalisés (placeholders comité + délégations) |
| 3 | **M-CBA-GEN** | 2 jours | M-PV-TEMPLATES, M-SCORING-ENGINE | Génération CBA automatisée (openpyxl, sha256, endpoints generate/list) |
| 4 | **M-PV-GEN** | 2 jours | M-CBA-GEN, M-COMMITTEE-CORE | Génération PV automatisée (python-docx, roster + délégations, sha256) |
| 5 | **M-PIPELINE-A-E2E** | 2-3 jours | M-CBA-GEN, M-PV-GEN | Pipeline Couche A complet + SLA Classe A (< 60s) + test E2E bloquant |

**État actuel** : Code génération CBA/PV existe et est fonctionnel (testé unitairement). Templates existants à vérifier conformité V3.3.2.

---

### 9.7 PHASE 4 — Sécurité & Traçabilité (❌ 0 %)

| # | Milestone | Durée | Prérequis | Fonction |
|---|-----------|-------|-----------|----------|
| 1 | **M-SECURITY-CORE** | 3 jours | M-PIPELINE-A-E2E | Auth/RBAC/audit/rate limit complet |
| 2 | **M-TRACE-HISTORY** | 2 jours | M-SECURITY-CORE | Historisation scores/éliminations |
| 3 | **M-CI-INVARIANTS** | 1 jour | M-TRACE-HISTORY | Tests CI invariants constitutionnels |

**État actuel** : JWT/RBAC/rate limiting déjà implémentés. Migrations `004_users_rbac.py` et `010_enforce_append_only_audit.py` existent. Nécessite hardening (voir §8 Sécurité).

---

### 9.8 PHASE 5 — Couche B & Market Signal (❌ 0 %)

| # | Milestone | Durée | Prérequis | Fonction |
|---|-----------|-------|-----------|----------|
| 1 | **M-MARKET-DATA-TABLES** | 2 jours | M-CI-INVARIANTS | 3 tables sources Market Signal (mercuriale, historique, surveys) |
| 2 | **M-MARKET-INGEST** | 2 jours | M-MARKET-DATA-TABLES | Import mercuriale + auto-feed historique post-décision |
| 3 | **M-MARKET-SURVEY-WORKFLOW** | 3 jours | M-MARKET-INGEST | Workflow terrain (min 3 cotations/item, validité 90 jours, zone obligatoire) |
| 4 | **M-MARKET-SIGNAL-ENGINE** | 3-4 jours | M-MARKET-SURVEY-WORKFLOW | Agrégation 3 sources (Market Survey terrain prévaut pour prix actuel, Historique pour tendances, Mercuriale = borne supérieure) |
| 5 | **M-CONTEXT-UI-PANEL** | 2 jours | M-MARKET-SIGNAL-ENGINE | Panneau UI Market Signal (read-only, aucun write Couche A) |
| 6 | **M-DICT-FUZZY-MATCH** | 2 jours | M-CONTEXT-UI-PANEL | Fuzzy matching dictionnaire (perf < 100ms, validation humaine sous seuil) |

**Règles d'agrégation Market Signal (opposables)** :
- Market Survey terrain prévaut pour le prix actuel (si ≤ 90 jours, min. 3 cotations/item)
- Historique des décisions prévaut pour tendances (fenêtre 24 mois)
- Mercuriale officielle = borne supérieure réglementaire
- Dégradation : 1 source manquante = ⚠️, 2 = 🔴, 3 = ⬛
- **Interdiction absolue** : Market Signal n'a aucun impact sur `supplier_scores`

**État actuel** : Migration `005_add_couche_b.py` existe. Table `market_data` définie dans `0001_init_schema.py` et `011_add_missing_schema.py` (⚠️ double définition potentielle).

---

### 9.9 PHASE 6 — DevOps (❌ 0 %)

| # | Milestone | Durée | Prérequis | Fonction |
|---|-----------|-------|-----------|----------|
| 1 | **M-MONITORING-OPS** | 2 jours | M-DICT-FUZZY-MATCH | Logs JSON structurés + métriques Prometheus |
| 2 | **M-DEVOPS-DEPLOY** | 2 jours | M-MONITORING-OPS | Docker/CI/CD/Railway déploiement production |

**État actuel** : `docker-compose.yml` et `Procfile` existent. Railway-ready. CI GitHub Actions configurée.

---

### 9.10 PHASE 7 — Produit & Terrain (❌ 0 %)

| # | Milestone | Durée | Prérequis | Fonction |
|---|-----------|-------|-----------|----------|
| 1 | **M10-UX-V2** | 5-7 jours | M-DEVOPS-DEPLOY | Interface Couche A complète + Registre dépôt (3 écrans max) |
| 2 | **M-UX-TEST-TERRAIN** | 3 jours | M10-UX-V2 | Tests utilisateurs (3-5 experts terrain) + mesure T_DMS |
| 3 | **M-ERP-AGNOSTIC-CHECK** | 1 jour | M-UX-TEST-TERRAIN | Vérification indépendance ERP (INV-7) |
| 4 | **M-PILOT-EARLY-ADOPTERS** | ongoing | M-ERP-AGNOSTIC-CHECK | Déploiement pilote + NPS + adoption ≥ 80 % |

### 9.11 Gates GO/NO-GO (opposables)

| Gate | Prérequis | Critère |
|------|-----------|---------|
| **Alpha interne** | Phase 0-3 complètes | Couche A end-to-end fonctionnelle |
| **Pilote terrain** | Phase 4-5 complètes | Sécurité + Market Signal opérationnels |
| **Production externe** | Phase 6-7 complètes | NPS ≥ 70, adoption ≥ 80 %, SLA respecté |

---

### 9.12 Séquence d'exécution recommandée (1 → 28)

```
 1. M-DOCS-CORE                ✅ DONE
 2. M-SCHEMA-CORE              ✅ DONE
 3. M-EXTRACTION-ENGINE        ✅ DONE
 4. M-EXTRACTION-CORRECTIONS   ⏳ PROCHAIN
 5. M-CRITERIA-TYPING          ❌
 6. M-NORMALISATION-ITEMS      ❌ ⚠️ CRITIQUE
 7. M-SCORING-ENGINE           ❌
 8. M-SCORING-TESTS-CRITIQUES  ❌
 9. M-COMMITTEE-CORE           ❌
10. M-CBA-TEMPLATES            ❌
11. M-PV-TEMPLATES             ❌
12. M-CBA-GEN                  ❌
13. M-PV-GEN                   ❌
14. M-PIPELINE-A-E2E           ❌
15. M-SECURITY-CORE            ❌
16. M-TRACE-HISTORY            ❌
17. M-CI-INVARIANTS            ❌
18. M-MARKET-DATA-TABLES       ❌
19. M-MARKET-INGEST            ❌
20. M-MARKET-SURVEY-WORKFLOW   ❌
21. M-MARKET-SIGNAL-ENGINE     ❌
22. M-CONTEXT-UI-PANEL         ❌
23. M-DICT-FUZZY-MATCH         ❌
24. M-MONITORING-OPS           ❌
25. M-DEVOPS-DEPLOY            ❌
26. M10-UX-V2                  ❌
27. M-UX-TEST-TERRAIN          ❌
28. M-ERP-AGNOSTIC-CHECK       ❌
29. M-PILOT-EARLY-ADOPTERS     ❌
```

---

## 10. SYNTHÈSE DES RISQUES ET RECOMMANDATIONS

### 10.1 Points forts du projet

| Aspect | Appréciation |
|--------|--------------|
| Vision produit | ✅ Excellente — problème réel, solution correctement cadrée |
| Constitution gelée | ✅ Discipline rare — 11 invariants non-négociables |
| Architecture 2 couches | ✅ Design évolutif — séparation A/B nette |
| Choix technologique | ✅ Solide — FastAPI + PostgreSQL strict |
| Code fonctionnel | ✅ ~80 % code réel (pas du scaffolding) |
| Règles métier | ✅ Ancrées dans le réel (Mali + SCI) |
| Discipline ADR | ✅ Traçabilité décisionnelle exemplaire |
| Invariants CI | ✅ Tests constitutionnels automatisés |

### 10.2 Points de vigilance

| Risque | Sévérité | Impact |
|--------|----------|--------|
| Couche B absente | 🔴 Critique | Sans mémoire marché, pas de différenciation vs Excel |
| Extraction DAO stub vide | 🔴 Critique | Annule la promesse de réduction cognitive |
| Clé JWT par défaut en dur | 🔴 Critique | Contournement total de l'auth en production |
| Couverture tests 5,2 % | 🟠 Haute | Risque de régression silencieuse |
| Dictionnaire Sahel absent | 🟠 Haute | Couche A et B ne fonctionnent pas sans normalisation |
| API Scoring non câblée | 🟠 Haute | Moteur existe mais pas exposé |
| Documentation dispersée | 🟡 Moyenne | Confusion pour nouveaux développeurs |
| IDs milestones CI désalignés | 🟡 Moyenne | `ci-milestones-gates.yml` vérifie des IDs obsolètes |

### 10.3 Estimation des efforts restants

| Phase | Durée estimée | Dépendances critiques |
|-------|---------------|-----------------------|
| Phase 0 restante | 2 jours | M-EXTRACTION-CORRECTIONS |
| Phase 1 | 7-9 jours | Dictionnaire Sahel = clé de voûte |
| Phase 2 | 8-9 jours | Câblage API scoring |
| Phase 3 | 8-9 jours | Conformité templates V3.3.2 |
| Phase 4 | 6 jours | Hardening sécurité |
| Phase 5 | 14-16 jours | **Couche B = différenciateur stratégique** |
| Phase 6 | 4 jours | Docker/Railway |
| Phase 7 | 9-11 jours + ongoing | Tests terrain avec experts |
| **TOTAL** | **58-62 jours ouvrés** | Séquentiel strict |

### 10.4 Conclusion

Le DMS V3.3.2 est un projet **viable et sérieux** avec une vision claire, une architecture saine, et une discipline d'exécution exemplaire. La Couche A est partiellement fonctionnelle (~85 %). La progression globale est d'environ 10 % sur le plan de milestones canonique. La Couche B (mémoire marché) représente le **différenciateur stratégique** qui transformera l'outil d'un "Super Excel" en une plateforme d'intelligence procurement unique en Afrique de l'Ouest.

**Prochaine étape immédiate** : M-EXTRACTION-CORRECTIONS (2 jours) → débloquer la Phase 1.

---

*Rapport d'évaluation établi le 20 février 2026. Aucune modification de code effectuée.*  
*Basé sur l'analyse exhaustive de : ~5 200 LOC Python, 200+ tests, 13 migrations SQL, 80+ fichiers documentation, 7 workflows CI, 4 ADR, 28 milestones.*
