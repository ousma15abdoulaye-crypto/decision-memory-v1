# DMS — MILESTONES EXECUTION PLAN (V3.3.2)

- Version: V3.3.2
- Date: 2026-02-16
- Autorité: Abdoulaye Ousmane (Founder & CTO)
- Statut: CANONIQUE · OPPOSABLE
- Objet: Définir, sans ambiguïté, les milestones techniques et fonctionnels du DMS V3.3.2.

## 0. Définitions (terminologie stable)

### 0.1. Cas (case)
Un “case” représente un processus d’achat unique (DAO/RFQ/RFP/achat simple/marché négocié/hybride).  
Un case possède:
- une référence
- un type de procédure
- une zone géographique
- des documents (DAO/RFQ/ToR, offres, annexes)
- des extractions (texte + données structurées)
- des critères typés
- des offres normalisées
- des scores
- un comité (composition + état de verrouillage)
- des exports (CBA, PV)

### 0.2. Documents / Extractions / Corrections
- Document: fichier uploadé (PDF/Excel/Word/image) + métadonnées + statut.
- Extraction: résultat de parsing/OCR (raw_text + structured_data JSON) + confidence score + provenance.
- Correction: action humaine append-only, champ par champ, avec before/after + auteur + timestamp + raison.

### 0.3. Normalisation (dictionnaire procurement)
Processus obligatoire qui transforme des lignes d’offres “brutes” en lignes “canoniques” comparables:
- item canonique
- unité canonique
- quantités converties
- alias résolus
- validation humaine si confiance insuffisante

### 0.4. Scoring (non prescriptif)
Le scoring produit des valeurs calculées et traçables:
- conformité essentiels (pass/fail)
- score capacité
- score durabilité
- score commercial (prix)
- total pondéré
Le scoring n’émet pas de recommandation décisionnelle.

### 0.5. Comité (brique conformité)
Le comité est une entité structurée, avec règles:
- composition proposée automatiquement selon catégorie + seuil
- saisie minimale des identités
- verrouillage (“LOCK”) irréversible
- après LOCK: la composition ne change jamais
- délégation autorisée sans modifier la composition (proxy), tracée append-only

---

## 1. Milestones Couche A — Documents → Extraction → Normalisation → Scoring → Génération

### 1.1. M DOCS CORE — Pipeline documents & extractions

**Fonction**
Implémenter le socle “documents → extractions → corrections”, avec intégrité, statuts, endpoints, et règles append-only.

**Ce que ça résout**
Passage propre “fichiers uploadés → données exploitables”, avec:
- stockage fiable
- statut lisible par l’UX
- extraction associée au bon document
- corrections humaines traçables sans écraser l’original

**Lien Constitution**
- Entités documents/extractions/corrections
- Append-only (INV-6)
- Fidélité au réel (INV-9)

**Livrables techniques (obligatoires)**
1) Modèle de données (PostgreSQL)
- Table `documents`
  - `id`, `case_id`, `doc_type`, `original_filename`, `content_type`, `file_size_bytes`
  - `storage_backend`, `storage_path` (ou key), `sha256`, `uploaded_by`, `uploaded_at`
  - `status` (ex: `uploaded`, `queued`, `extracted`, `failed`)
  - `metadata` (jsonb) : zone, vendor supposé, pages, etc.
- Table `extractions`
  - `id`, `document_id`, `case_id` (duplication volontaire pour requêtes rapides)
  - `raw_text` (text)
  - `structured_data` (jsonb)
  - `confidence_score` (0..1)
  - `extraction_method` (ex: `pdf_text`, `ocr_azure`, `ocr_tesseract`, `excel_parser`)
  - `provider_payload` (jsonb, optionnel)
  - `created_by`, `created_at`
  - `status` (ex: `success`, `partial`, `failed`)
- Table `extraction_corrections` (append-only)
  - `id`, `extraction_id`, `document_id`, `case_id`
  - `field_path` (ex: `criteria[2].weight`)
  - `value_before` (text)
  - `value_after` (text)
  - `reason` (text)
  - `corrected_by`, `corrected_at`

2) API (FastAPI)
- POST upload document:
  - validation content-type
  - validation magic bytes
  - size limit
  - calcul sha256
  - réponse: `document_id`, `status`
- GET document metadata
- GET extractions by document
- GET extraction détail (raw_text + structured_data)
- POST correction extraction (append-only)
- POST “rebuild structured view” (appliquer corrections sans supprimer l’original)

3) Règles de sécurité minimales
- aucun fichier exécutable accepté
- whitelist explicite: PDF, XLSX, DOCX, images (si OCR)
- logs d’audit des actions (au moins: upload, extraction created, correction created)

**Definition of Done (bloquante)**
- Toutes les tables existent, migrées par Alembic
- Endpoints fonctionnels avec tests
- Append-only garanti:
  - interdiction UPDATE/DELETE sur `extraction_corrections`
- Un document uploadé doit être consultable et lié à un case
- Une extraction doit être consultable et liée au bon document
- Une correction doit être visible dans l’historique et ne pas modifier l’original

---

### 1.2. M EXTRACTION ENGINE — Moteur d’extraction 3 niveaux

**Fonction**
Construire `ExtractionEngine` à 3 niveaux:
1) parsing natif (PDF text / DOCX / XLSX)
2) parsing structuré (tableaux, sections, entêtes)
3) OCR providers (Azure + fallback Tesseract) avec scoring confiance

**Ce que ça résout**
Extraire du texte et des données structurées de tout type de document, avec un niveau de confiance mesurable.

**Lien Constitution**
- Extraction (Couche A)
- OCR / parsing
- SLA Classe A/B

**Livrables techniques (obligatoires)**
1) Service `ExtractionEngine`
- Entrée: `document_id`
- Sortie: insertion `extractions` (raw_text + structured_data + confidence_score)
- Gestion erreurs:
  - statut document `failed` si extraction impossible
  - stockage message d’erreur dans `metadata` document ou `provider_payload`

2) Structured_data minimal standard (JSON) produit par l’extraction
- `doc_kind` (dao, offer, tdr, annex)
- `language`
- `detected_tables` (liste)
- `detected_sections` (liste)
- `candidate_criteria` (liste brute)
- `candidate_line_items` (liste brute)
- `currency_detected`
- `dates_detected`
- `supplier_candidates` (si document offre)

3) Providers
- PDF text extractor (sans OCR)
- DOCX parser
- XLSX parser
- OCR Azure (si activé)
- OCR Tesseract fallback (optionnel)
- Stratégie:
  - essayer parsing natif d’abord
  - basculer OCR si texte vide ou trop faible

4) Mesure confiance
- confidence calculée et stockée
- règles simples:
  - taux de caractères non reconnus
  - cohérence tables détectées
  - présence champs attendus (ex: fournisseur / prix / items)

**Definition of Done (bloquante)**
- ExtractionEngine fonctionne sur PDF, DOCX, XLSX
- Au moins 1 provider OCR branchable
- confidence_score présent et testé
- Tests:
  - extraction sur fichiers fixtures
  - cas “texte vide → OCR”
  - cas “OCR fail → failed”

---

### 1.3. M EXTRACTION CORRECTIONS — Traçabilité des corrections humaines

**Fonction**
Implémenter une correction humaine champ par champ, append-only, avec “before/after”, auteur, timestamp, et raison.

**Ce que ça résout**
Permettre de corriger l’OCR/parsing sans perdre la donnée originale.

**Lien Constitution**
- humain contrôle
- extraction_corrections
- INV-9 (fidélité au réel)

**Livrables techniques (obligatoires)**
1) Mécanisme “vue corrigée”
- L’extraction originale reste immutable
- Les corrections sont appliquées pour produire une “structured_data_effective”
- Deux modes acceptables:
  - (A) calcul à la volée (apply corrections)
  - (B) materialized view / champ JSON recalculé stocké (mais l’original reste)

2) Endpoint correction
- POST correction: `extraction_id`, `field_path`, `value_before`, `value_after`, `reason`
- validation:
  - `value_before` doit correspondre à l’état courant effectif, sinon rejet (éviter conflits)

3) Audit
- Chaque correction produit une entrée audit (action, user, extraction_id)

**Definition of Done (bloquante)**
- correction append-only vérifiée (pas de DELETE/UPDATE)
- correction visible (historique)
- structured_data_effective cohérente et testée

---

### 1.4. M CRITERIA TYPING — Critères typés universels

**Fonction**
Extraire et typer les critères:
- commercial
- capacity
- sustainability
- essentials (éliminatoires)

**Ce que ça résout**
Donner une base structurée au scoring, quel que soit le type de procédure.

**Lien Constitution**
- universalité procédures
- scoring

**Livrables techniques (obligatoires)**
1) Modèle
- Table `criteria`
  - `id`, `case_id`, `source_extraction_id`
  - `label`, `category`, `weight`, `is_essential`
  - `expected_evidence` (optionnel)
  - `created_at`, `created_by`

2) Pipeline
- À partir de structured_data_effective:
  - détecter candidats critères
  - typage
  - stockage

3) Tests
- typage stable sur fixtures DAO/RFQ/RFP
- edge cases: critères sans poids, poids total ≠ 100 (règles)

**Definition of Done**
- critères générés automatiquement
- corrigibles via corrections extraction (pas via UPDATE destructive)
- tests passants

---

### 1.5. M NORMALISATION ITEMS — Dictionnaire procurement (items + unités)

**Fonction**
Implémenter un dictionnaire procurement et un moteur de normalisation.

**Ce que ça résout**
Standardiser les lignes d’offre pour comparaison équitable.

**Lien Constitution**
- dictionnaire procurement
- INV-1 (réduction charge cognitive)

**Livrables techniques (obligatoires)**
1) Modèle dictionnaire
- Table `procurement_items`
  - `id`, `canonical_name`, `category`, `default_unit`, `active`
- Table `procurement_item_aliases`
  - `id`, `item_id`, `alias`, `lang`, `source`
- Table `procurement_units`
  - `id`, `canonical_unit`, `unit_family` (poids, volume, longueur, unité)
- Table `procurement_unit_conversions`
  - `from_unit`, `to_unit`, `factor`
- Table `normalized_line_items`
  - `id`, `case_id`, `supplier_id`, `raw_label`, `raw_unit`, `raw_qty`, `raw_price`
  - `item_id`, `canonical_unit`, `canonical_qty`, `canonical_price`
  - `normalization_confidence`, `needs_human_validation` (bool)
  - `created_at`

2) Moteur de normalisation
- entrée: line items bruts issus des extractions
- sortie: normalized_line_items
- règles:
  - mapping alias → item canonique
  - conversion unités si possible
  - calcul confidence
  - si sous seuil: `needs_human_validation = true`

3) UX / endpoints validation humaine (minimal)
- GET items à valider
- POST validation item (append-only événement)

**Definition of Done**
- aucune offre brute n’entre dans scoring
- normalisation produit une structure comparable
- validations humaines tracées

---

### 1.6. M SCORING ENGINE — Scoring multi critères non prescriptif

**Fonction**
Moteur scoring universel sur:
- critères typés
- offres normalisées

**Ce que ça résout**
Convertir critères + offres en scores factuels, traçables, sans prescrire.

**Lien Constitution**
- scoring
- Couche B ne modifie pas
- INV-3 non prescriptif
- INV-9 traçabilité

**Livrables techniques (obligatoires)**
1) Modèle
- Table `supplier_scores`
  - `id`, `case_id`, `supplier_id`
  - `capacity_score`, `commercial_score`, `sustainability_score`
  - `weighted_total`
  - `essential_pass` (bool)
  - `computed_at`, `computed_by`, `scoring_version`
- Table `supplier_eliminations`
  - `id`, `case_id`, `supplier_id`
  - `reason_codes` (jsonb)
  - `details` (jsonb)
  - `created_at`

2) Règles scoring
- essentials = gate: si fail → essential_pass false, score total non comparable
- commercial scoring basé sur prix normalisé
- poids = basé sur criteria.weight
- output stable et reproductible

3) Interdictions explicites
- aucun appel Couche B dans le scoring
- aucune règle “recommandation”
- aucune écriture dans tables Couche B

**Definition of Done**
- scoring reproductible (idempotent)
- éliminations expliquées (reason_codes)
- tests passants sur cas réels

---

### 1.7. M SCORING TESTS CRITIQUES — Tests critiques + performance

**Fonction**
Suite de tests unitaires, property-based et E2E couvrant:
- edge cases
- performance
- idempotence
- indépendance Couche B

**Ce que ça résout**
Garantir scoring correct, stable, rapide.

**Lien Constitution**
- Couche A autonome
- non prescriptif
- SLA

**Livrables techniques (obligatoires)**
- tests unitaires scoring
- tests “100+ fournisseurs”
- tests “aucune dépendance Couche B”
- tests “no raw offer in scoring” (bloquant CI)

**Definition of Done**
- CI bloque si:
  - scoring lent au-delà seuil
  - raw offers détectées
  - dépendance Couche B détectée

---

### 1.8. M COMMITTEE CORE — Module Comité (règles + data model + LOCK irréversible)

**Fonction**
Créer un module comité conforme:
- configuration automatique selon catégorie + seuil
- saisie minimale (nom, prénom, fonction, email optionnel)
- verrouillage irréversible
- composition immuable après verrouillage
- délégation autorisée sans changer les membres

**Ce que ça résout**
Un comité réel, une fois verrouillé, ne bouge pas.  
Le système doit refléter cette réalité: toute flexibilité “post-lock” est non conforme et dangereuse.

**Lien Constitution**
- conformité process
- append-only (INV-6)
- fidélité au réel (INV-9)

**Livrables techniques (obligatoires)**
1) Modèle de données (PostgreSQL)
- Table `committees`
  - `id`, `case_id`
  - `committee_type` (evaluation, opening, technical, etc. si besoin)
  - `composition_rule_id` (référence interne règle appliquée)
  - `status` : `draft` → `locked`
  - `locked_at`, `locked_by`
  - `created_at`
- Table `committee_members`
  - `id`, `committee_id`
  - `role` (buyer, finance, budget_holder, technical, observer, chair, etc.)
  - `last_name`, `first_name`, `function`, `email`
  - `required` (bool)
  - `created_at`, `created_by`
- Table `committee_events` (append-only, obligatoire)
  - `id`, `committee_id`, `case_id`
  - `event_type` : `created`, `member_added`, `locked`, `delegation_added`
  - `payload` (jsonb)
  - `created_at`, `created_by`

2) Verrouillage irréversible (enforcement DB, pas seulement code)
- Après `committees.status = locked`:
  - interdiction INSERT/UPDATE/DELETE sur `committee_members`
  - interdiction UPDATE statut locked → draft
- Implémentation recommandée:
  - trigger PostgreSQL qui lève une exception si tentative de modification
  - tests automatisés qui prouvent l’interdiction

3) Délégation (sans modifier la composition)
- Table `committee_delegations` (append-only)
  - `id`, `committee_id`, `member_id` (le membre officiel)
  - `delegate_name`, `delegate_function`, `delegate_email` (optionnel)
  - `reason`
  - `valid_from`, `valid_to` (optionnel)
  - `created_at`, `created_by`
- Règle:
  - une délégation n’ajoute pas un membre, elle ne modifie pas `committee_members`
  - c’est une “procuration” tracée, consultable, imprimable dans PV

4) Rules engine composition (data-driven)
- Table `committee_composition_rules`
  - `id`, `category`, `threshold_band`, `rule_json`
  - `justification_text`
- `CommitteeBuilder`:
  - entrée: `case.category`, `case.amount`, `procurement_method`
  - sortie: composition roles + required + min_level
  - aucune logique hardcodée non traçable: la règle doit être lisible et versionnable

5) API (FastAPI)
- POST create committee (draft) pour case
- POST set members (draft uniquement)
- POST lock committee
- POST add delegation (locked ou draft, mais sans toucher membres)
- GET committee details + events + delegations

**Definition of Done (bloquante)**
- LOCK irréversible prouvé par tests
- aucune modification membres post-lock possible (DB trigger + tests)
- délégation possible post-lock sans modifier roster
- événements append-only présents
- le PV peut afficher:
  - composition officielle
  - délégations éventuelles

---

### 1.9. M CBA TEMPLATES + M PV TEMPLATES — Templates normalisés

**Fonction**
Créer templates canoniques:
- CBA Excel
- PV Word

**Ce que ça résout**
Standardiser les livrables officiels, éviter dérive manuelle.

**Lien Constitution**
- livrables requis
- exports

**Livrables techniques (obligatoires)**
1) Templates CBA (.xlsx)
- multi-onglets
- formules
- mise en forme stable
- zones réservées aux données injectées

2) Templates PV (.docx)
- placeholders:
  - identifiants case
  - liste membres comité (officiel)
  - délégations (si présentes)
  - scores synthétiques
  - décision et justification (humaine)

**Definition of Done**
- templates validés sur cas réels
- placeholders complets
- versionnement strict

---

### 1.10. M CBA GEN + M PV GEN — Génération CBA/PV automatisée

**Fonction**
Générer CBA + PV depuis données Couche A.

**Ce que ça résout**
Automatiser ce que l’utilisateur fait à la main, tout en gardant la décision humaine.

**Lien Constitution**
- génération
- INV-1 réduction charge
- INV-9 fidélité

**Livrables techniques (obligatoires)**
- `CBAGenerator` (openpyxl)
- `PVGenerator` (python-docx)
- Table `exports`
  - `id`, `case_id`, `export_type`, `file_path`, `sha256`, `generated_by`, `generated_at`
- API:
  - POST generate CBA
  - POST generate PV
  - GET list exports

**Definition of Done**
- exports produisent fichiers ouvrables
- hash sha256 stocké
- traçabilité export append-only (pas de suppression)

---

### 1.11. M PIPELINE A E2E — Pipeline Couche A complet + SLA Classe A

**Fonction**
Tests end-to-end sur documents natifs:
“PDF/Excel/Word → extraction → normalisation → scoring → exports”.

**Ce que ça résout**
Prouver que Couche A fonctionne seule et respecte la vitesse.

**Lien Constitution**
- SLA Classe A
- INV-1

**Livrables techniques**
- fixtures réalistes
- timers intégrés
- rapport performance en CI

**Definition of Done**
- SLA vérifié en CI (seuil défini)
- pipeline complet reproductible

---

## 2. Milestones Couche B — Mémoire, Market Signal, Dictionnaire étendu

### 2.1. M MARKET DATA TABLES — Mercuriale, historique décisions, Market Surveys

**Fonction**
Créer les tables des 3 sources.

**Livrables**
- `mercurials`
- `decision_history`
- `market_surveys`

**Definition of Done**
- schémas stables
- indexes sur item/zone/date
- migrations + tests

---

### 2.2. M MARKET INGEST — Ingestion mercuriale & auto-feed décisions

**Fonction**
Ingestion mercuriale + alimentation automatique decision_history après décision.

**Livrables**
- import mercuriale (CSV/XLSX)
- hook post-decision:
  - quand un PV est finalisé (ou décision enregistrée), écrire decision_history

**Definition of Done**
- ingestion idempotente
- auto-feed fiable
- audit entries

---

### 2.3. M MARKET SURVEY WORKFLOW — Workflow Market Survey terrain

**Fonction**
Permettre la saisie terrain contrôlée.

**Règles**
- minimum 3 cotations par item
- validité max 90 jours
- zone obligatoire
- source/collecteur obligatoire

**Livrables**
- API CRUD market surveys
- UI minimal: création survey + ajout cotations

**Definition of Done**
- validations strictes
- tests sur fraîcheur

---

### 2.4. M MARKET SIGNAL ENGINE — Agrégation 3 sources + règles de priorité

**Fonction**
Agrégateur Market Signal.

**Livrables**
- `MarketSignalProvider`
- règles:
  - priorité mercuriale officielle si fraîche
  - sinon history
  - sinon surveys
  - états dégradés (informatifs) sans prescription

**Definition of Done**
- explicabilité: chaque signal indique sa( ses) source(s)
- aucun impact sur scoring
- tests d’agrégation

---

### 2.5. M CONTEXT UI PANEL — Panneau UI Market Signal (Couche B → Couche A)

**Fonction**
Panneau latéral “contexte marché”.

**Livrables**
- UI affichant:
  - min/avg/max
  - sources disponibles
  - fraîcheur
  - état dégradé
- garantie technique:
  - lecture seule

**Definition of Done**
- panel fonctionne sans influencer scoring
- tests “read only” (pas d’écriture Couche A)

---

### 2.6. M DICT FUZZY MATCH — Fuzzy matching dictionnaire (items & fournisseurs)

**Fonction**
Résolution variations écriture.

**Livrables**
- algos token + levenshtein
- seuil configurable
- si sous seuil:
  - validation humaine obligatoire
  - événement append-only

**Definition of Done**
- performance < seuil défini
- tests sur cas réels
- aucune “auto-normalisation silencieuse” sous seuil

---

## 3. Milestones Transverses — Sécurité, Traçabilité, Performance, CI

### 3.1. M SECURITY CORE — Auth, RBAC, audit_log, rate limiting

**Fonction**
Sécuriser et tracer.

**Livrables**
- JWT access/refresh
- RBAC 5 rôles
- `audit_log` append-only
- rate limiting
- upload validation (magic bytes, taille, whitelist)

**Definition of Done**
- tests auth/rbac/rate limit
- audit log généré sur actions critiques
- interdiction DELETE/UPDATE sur audit_log

---

### 3.2. M TRACE HISTORY — score_history & elimination_log

**Fonction**
Historiser les résultats.

**Livrables**
- `score_history` append-only
- `elimination_log` append-only
- triggers anti delete/update
- tests

**Definition of Done**
- prouve l’historique inviolable

---

### 3.3. M CI INVARIANTS — Tests CI pour chaque invariant

**Fonction**
Rendre chaque invariant testable.

**Livrables**
- suite `tests/invariants/` couvrant:
  - no raw offer in scoring
  - no Couche B dependency in Couche A scoring
  - append-only enforcement (committee_members post-lock, audit_log, corrections)
  - ERP agnostique (scan imports / endpoints)
  - SLA basique

**Definition of Done**
- CI bloque toute violation

---

### 3.4. M MONITORING OPS — Logs JSON & métriques Prometheus

**Fonction**
Observabilité SLA et régressions.

**Livrables**
- logger JSON
- métriques Prometheus:
  - latence extraction
  - latence scoring
  - latence export
  - latence market signal
- endpoint `/api/health`

**Definition of Done**
- métriques visibles
- seuils d’alerte possibles

---

### 3.5. M DEVOPS DEPLOY — Docker, CI/CD, santé

**Fonction**
Déploiement reproductible.

**Livrables**
- docker compose (app + postgres)
- GitHub Actions:
  - tests
  - coverage
  - lint
- déploiement Railway
- healthcheck

**Definition of Done**
- déploiement reproductible
- CI bloque merge

---

## 4. Milestones Produit & Terrain — UX, Early adopters, ERP agnostique

### 4.1. M UX FLOW 3 SCREENS — 3 écrans canoniques

**Fonction**
Implémenter le flow canonique:
- Ingestion
- Structuration
- Décision

**Inclut explicitement**
- registre dépôt comme écran “2bis” (append-only)
- écran comité:
  - configuration identités en draft
  - action LOCK irréversible
  - délégation sans changement de membres
- écran analyse comparative
- écran export

**Definition of Done**
- workflow complet utilisable
- comité lock irréversible appliqué
- registre dépôt append-only

---

### 4.2. M UX TEST TERRAIN — Tests utilisateurs & T_DMS

**Fonction**
Mesurer gains réels.

**Livrables**
- protocole test
- métriques:
  - T_DMS vs T_manuel
  - nombre corrections
  - taux “retour Excel”
- rapport pilot

**Definition of Done**
- preuve d’efficacité terrain

---

### 4.3. M ERP AGNOSTIC CHECK — Vérification indépendance ERP

**Fonction**
Garantir neutralité ERP.

**Livrables**
- scans dépendances
- tests
- documentation intégration par exports/API

**Definition of Done**
- aucune dépendance ERP imposée

---

### 4.4. M PILOT EARLY ADOPTERS — Déploiement pilote & NPS

**Fonction**
Pilote production contrôlé.

**Livrables**
- déploiement pilote
- suivi adoption
- NPS
- backlog correctifs

**Definition of Done**
- adoption validée
- stabilité démontrée

---

## 5. Ordre d’exécution recommandé (séquence stricte)

1) M DOCS CORE  
2) M EXTRACTION ENGINE  
3) M EXTRACTION CORRECTIONS  
4) M CRITERIA TYPING  
5) M NORMALISATION ITEMS  
6) M SCORING ENGINE  
7) M SCORING TESTS CRITIQUES  
8) M COMMITTEE CORE  
9) M CBA/PV TEMPLATES  
10) M CBA/PV GEN  
11) M PIPELINE A E2E  
12) M SECURITY CORE  
13) M CI INVARIANTS  
14) M MARKET DATA TABLES  
15) M MARKET INGEST  
16) M MARKET SURVEY WORKFLOW  
17) M MARKET SIGNAL ENGINE  
18) M CONTEXT UI PANEL  
19) M DICT FUZZY MATCH  
20) M MONITORING OPS  
21) M DEVOPS DEPLOY  
22) M UX FLOW 3 SCREENS  
23) M UX TEST TERRAIN  
24) M ERP AGNOSTIC CHECK  
25) M PILOT EARLY ADOPTERS

---

## 6. Règle spéciale Comité (rappel opposable)

- Tant que le comité est en `draft`, on peut saisir les membres.
- Dès que le comité passe en `locked`:
  - la composition (liste de membres) est immuable.
  - toute tentative de modification doit échouer au niveau base de données.
- La délégation est autorisée:
  - elle ne modifie pas le roster
  - elle se trace append-only
  - elle doit apparaître dans les exports PV.

Fin du document.
