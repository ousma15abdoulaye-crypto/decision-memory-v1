# Architecture du Decision Memory System (DMS) V3.3.2

**Référence :** Constitution V3.3.2 (freeze actif et opposable)  
**Date :** 2026-02-19  
**Phase :** Zéro — Milestone M-DOCS-CORE

---

## Vue d'ensemble du système

Le Decision Memory System (DMS) est un assistant intelligent de procurement structuré en deux couches complémentaires et hiérarchisées. Il transforme des processus compétitifs formels en dossiers d'analyse structurés, prêts à être défendus, tout en construisant une mémoire vivante des marchés sans effort supplémentaire pour l'utilisateur.

**Raison d'être :** Amplifier la capacité de décision des experts, sans jamais décider à leur place.

**Formule fondatrice :** « Le DMS est la mémoire intelligente et le cerveau auxiliaire du procurement — jamais son juge. »

---

## Couche A (Scoring, règles constitutionnelles, SLA 60s)

**Rôle :** Accomplir 80–90 % du travail cognitif répétitif entre l'ouverture d'un processus et la décision humaine.

**Responsabilités principales :**
- Ingestion des DAO/RFQ/RFP, TDR, offres (PDF, Excel, Word)
- Extraction et structuration des critères (techniques, financiers, administratifs)
- Construction d'un dossier d'analyse unique, consolidé par lot et soumissionnaire
- Calcul des notes selon les règles officielles de l'organisation
- Pré-classement factuel et horodaté
- Génération des exports officiels : CBA, PV

**Interfaces principales :** Ingestion · Structuration · Décision & Exports

**Contraintes techniques :**
- **SLA obligatoire :** Toutes les opérations de la Couche A doivent respecter un SLA de 60 secondes maximum
- **Règles constitutionnelles :** Les calculs de scoring sont factuels et non prescriptifs (Constitution V3.3.2 §7)
- **Primauté absolue :** La Couche A est la seule autorisée à modifier les scores, classements et exports (Invariant V3)

**Modules principaux :**
- `src/couche_a/extraction/` — Extraction de données depuis documents
- `src/couche_a/normalisation/` — Normalisation des items selon dictionnaire Sahel
- `src/couche_a/scoring/` — Moteur de calcul des scores
- `src/couche_a/pipeline/` — Pipeline end-to-end de traitement
- `src/couche_a/generation/` — Génération des exports (CBA, PV)

---

## Couche B (Résolution, enrichissement, async)

**Rôle :** Se souvenir, rapprocher, contextualiser — sans prescrire.

**Responsabilités principales :**
- Capitalisation automatique des marchés passés
- Historisation des prix, délais, zones, attributaires
- Mise à disposition de cas comparables et signaux factuels
- Résolution d'entités (fournisseurs, items, unités) via dictionnaire Sahel
- Enrichissement contextuel des processus en cours

**Contrainte absolue :** La Couche B n'émet **jamais** de décision, de recommandation ou de verdict.

**Architecture :**
- **Read-only vis-à-vis de la Couche A :** Aucun module de la Couche B ne peut modifier un score, recalculer un classement, altérer un export ou influencer l'état d'un processus en cours (Constitution V3.3.2 §7)
- **Traitement asynchrone :** Les opérations d'enrichissement et de capitalisation sont exécutées de manière asynchrone pour ne pas impacter le SLA de la Couche A
- **Mémoire vivante :** Les données de la Couche B sont automatiquement mises à jour lors de chaque processus terminé, sans intervention humaine

**Modules principaux :**
- `src/couche_b/market_data/` — Tables de données marché
- `src/couche_b/resolution/` — Résolution d'entités via dictionnaire
- `src/couche_b/signal/` — Moteur de signaux marché
- `src/couche_b/survey/` — Workflow de survey terrain

---

## Séparation stricte A/B avec référence à ADR-0003

La séparation entre Couche A et Couche B est **structurelle et non négociable** (Constitution V3.3.2 §7).

**Règles d'isolation (ADR-0003 §3.1) :**
- ❌ **Interdit :** Importer un module de la Couche B dans les modules de la Couche A (`src/scoring/`, `src/pipeline/`, `src/normalisation/`, `src/criteria/`, `src/extraction/`, `src/committee/`, `src/generation/`)
- ✅ **Test CI bloquant :** `test_couche_a_b_boundary.py` vérifie automatiquement cette séparation via analyse AST
- ✅ **Architecture :** Les deux couches communiquent uniquement via la base de données PostgreSQL, jamais via imports Python directs

**Frontière technique :**
- La Couche A écrit dans les schémas `couche_a.*` (cases, submissions, scores, exports)
- La Couche B écrit dans les schémas `couche_b.*` (market_data, vendors, items, signals)
- Aucune dépendance circulaire n'est autorisée

**Référence :** `docs/freeze/v3.3.2/adrs/ADR-0003.md` §3.1 — Règles agent — Interdictions absolues

---

## Stack technique : Python 3.11, FastAPI, PostgreSQL, Alembic, GitHub Actions

**Backend :**
- **Langage :** Python 3.11
- **Framework :** FastAPI (async/await pour performance)
- **Base de données :** PostgreSQL (unique, pas de DB secondaire)
- **Migrations :** Alembic (migrations SQL brutes, pas d'ORM)
- **Auth :** JWT + RBAC (5 rôles : buyer, evaluator, committee, admin, viewer)

**Règles techniques (Constitution V3.3.2 §3) :**
- ❌ Pas d'ORM (SQLAlchemy, Tortoise, Beanie interdits)
- ❌ Pas de DB secondaire (PostgreSQL only)
- ✅ Requêtes paramétrées exclusivement (protection injection SQL)
- ✅ Helpers DB synchrones (`src/db/connection.py`)

**CI/CD :**
- **CI :** GitHub Actions (gates bloquants pour chaque milestone)
- **CD :** Railway (Nixpacks) — déploiement automatique sur merge main
- **Tests :** pytest avec couverture par phase (0/40/60/75%)

**Outils de développement :**
- **Linting :** ruff
- **Formatage :** black
- **Tests :** pytest + pytest-cov
- **Migrations :** Alembic avec migrations SQL explicites

---

## Flux de données : offre brute → normalisation → scoring → résolution → export

### 1. Ingestion (Couche A)
- Upload de documents (DAO, RFQ, RFP, TDR, offres)
- Validation magic bytes (python-magic)
- Calcul SHA256 pour intégrité
- Stockage dans `couche_a.documents`

### 2. Extraction (Couche A)
- Extraction de texte depuis PDF/Excel/Word
- Détection automatique de critères, items, prix
- Structuration en JSONB (`structured_data`)
- Marquage de confiance (`_low_confidence`, `_requires_human_review`)

### 3. Normalisation (Couche A)
- Normalisation des items selon dictionnaire Sahel
- Résolution d'entités via Couche B (read-only)
- Consolidation par lot et soumissionnaire

### 4. Scoring (Couche A)
- Calcul des scores selon critères officiels
- Vérification des critères éliminatoires
- Pré-classement factuel (non prescriptif)
- Stockage dans `couche_a.scores`

### 5. Résolution & Enrichissement (Couche B — async)
- Résolution des fournisseurs via dictionnaire
- Enrichissement avec historique marché (prix, délais)
- Génération de signaux factuels (non prescriptifs)
- Capitalisation automatique pour mémoire future

### 6. Export (Couche A)
- Génération CBA (Comparative Bid Analysis)
- Génération PV (Procès-Verbal)
- Validation complétude avant export
- Doctrine d'échec explicite : exports incomplets = marqués comme tels

**Machine d'état des processus :**
DRAFT → OPENED → EVALUATION → COMMITTEE_READY → ATTRIBUTED → ARCHIVED

Chaque transition est explicite, horodatée et liée à un rôle autorisé (Constitution V3.3.2 §8).

---

## Invariants système (référence Constitution V3.3.2)

Les invariants suivants sont **opposables à toute évolution** (Constitution V3.3.2 §2) :

1. **Réduction de charge cognitive** — Le système doit réduire, jamais augmenter, la charge cognitive de l'utilisateur
2. **Primauté absolue de la Couche A** — La Couche A est la seule autorisée à modifier les scores et décisions
3. **Mémoire vivante, non prescriptive** — La Couche B fournit des faits, jamais des recommandations
4. **Online-only assumé** — Pas de mode offline, pas de synchronisation complexe
5. **CI verte obligatoire** — Aucun commit sur main sans CI verte
6. **Append-only & traçabilité** — Toutes les modifications sont tracées, jamais supprimées
7. **ERP-agnostique & stack claire** — Pas de dépendance à un ERP spécifique
8. **Survivabilité & lisibilité** — Le code doit survivre à son créateur et rester lisible
9. **Fidélité au réel & neutralité** — Le système reflète la réalité, sans biais ni manipulation

**Référence complète :** `docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md` §2

---

## Périmètre négatif (ce qui n'est PAS dans ce repo)

Le DMS **n'est pas** :

- ❌ Un système de décision automatique — la décision finale reste intégralement humaine
- ❌ Un outil de recommandation de fournisseur — aucun verdict n'est émis
- ❌ Un système de scoring fournisseur transversal — seules les offres individuelles sont évaluées
- ❌ Un outil disciplinaire ou de surveillance individuelle — pas de tracking comportemental
- ❌ Un ERP ou système de gestion financière — pas de comptabilité, pas de facturation
- ❌ Un système de gestion de contrats — uniquement la phase d'appel d'offres
- ❌ Un système de e-procurement complet — pas de plateforme de soumission en ligne
- ❌ Un système de business intelligence généraliste — focus exclusif sur procurement

**Référence :** Constitution V3.3.2 §1.2 — Ce que le système N'EST PAS

---

*© 2026 — Decision Memory System — Architecture V3.3.2*
