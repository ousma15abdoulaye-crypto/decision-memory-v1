DMS — MILESTONES EXECUTION PLAN (V3.3.2)
Métadonnées du document

Version : V3.3.2

Date : 2026-02-16

Autorité : Abdoulaye Ousmane (Founder & CTO)

Statut : CANONIQUE · OPPOSABLE · FREEZABLE

Objet : Définir, sans ambiguïté, les milestones techniques et fonctionnels du DMS V3.3.2

Hash (à calculer lors du freeze) : SHA256 à inscrire dans FREEZE_MANIFEST.md

0. Préambule — Traçabilité & opposabilité
0.1. Documents de référence (opposables)

Le présent plan est valide uniquement s’il est interprété avec les documents suivants :

Constitution DMS V3.3.2 (référence canonique)

ADR-0001 — Plan Milestones V3.3.2, Fusion M10-UX-V2 + Registre dépôt, M-SECURITY-CORE, Discipline Agents

Invariants (INV-1 à INV-9)

Ces trois documents sont la source de vérité. Toute divergence est une erreur et doit être corrigée par amendement versionné.

0.2. Principes d’exécution (opposables)

Exécution séquentielle stricte : un milestone suivant ne démarre pas tant que le précédent n’est pas DONE.

Binaire : un milestone est DONE ou ABSENT. Il n’existe pas de “80%”.

Gates CI obligatoires :

CI verte (tous tests passent)

Coverage ≥ seuil défini par phase

Invariants respectés

SLA validés pour milestones critiques

Aucun contournement : tout agent (humain ou IA) doit lire Constitution + Plan + ADR-0001 avant d’écrire du code.

Discipline ADR : toute modification de structure (IDs, dépendances, scopes) = nouvel ADR + validation CTO explicite.

0.3. Règles anti-improvisation (discipline agents)

Source de vérité unique : Constitution V3.3.2 + ce plan + ADR-0001.

Interdiction d’inventer des milestones : aucun renommage/ajout sans ADR validé.

Definition of Done commune (§7) applicable à tous les milestones.

CI comme arbitre : aucune PR mergée avec CI rouge.

Agents IA : doivent respecter strictement :

INV-3 (Couche B non prescriptive)

INV-7 (ERP-agnostique)

séparation Couche A (action & calcul) / Couche B (mémoire & contexte)

1. Définitions — Terminologie stable (canonique)
1.1. Case (cas)

Un case représente un processus d’achat unique : DAO / RFQ / RFP / achat simple / marché négocié / hybride.
Un case possède au minimum :

Référence

Type de procédure

Zone géographique

Documents (DAO/RFQ/ToR, offres, annexes, market survey, etc.)

Extractions (raw_text + structured_data JSONB)

Corrections humaines append-only

Critères typés

Offres normalisées

Scores + éliminations

Comité (composition + état Draft/Locked + délégations)

Exports (CBA Excel, PV Word)

1.2. Documents / Extractions / Corrections (terminologie canonique)

Document : fichier uploadé + métadonnées + intégrité + statut d’extraction.

Extraction : résultat parsing/OCR (raw_text + structured_data JSONB) + confidence_score + méthode.

Correction : action humaine append-only, champ par champ, avec value_before/value_after + auteur + timestamp + raison.

1.3. Normalisation (dictionnaire procurement)

Processus obligatoire qui transforme des lignes d’offres “brutes” en lignes canoniques comparables :

Item canonique

Unité canonique

Quantités converties

Alias résolus

Validation humaine si confiance insuffisante

Règle opposable : aucune offre brute ne peut entrer dans le scoring.
Test CI bloquant : test_no_raw_offer_in_scoring.

1.4. Scoring (non prescriptif)

Le scoring produit des valeurs calculées et traçables :

Essentials (pass/fail, éliminatoires)

Score capacité

Score durabilité

Score commercial (prix)

Total pondéré

Le scoring n’émet aucune recommandation décisionnelle. (INV-3)

1.5. Comité (brique conformité)

Entité structurée avec règles strictes :

Composition proposée automatiquement selon catégorie + seuil

Saisie minimale des identités

Verrouillage (LOCK) irréversible

Après LOCK : composition immuable

Délégation possible sans modifier la composition, tracée append-only

2. Milestone Registry — IDs canoniques & dépendances
ID Milestone	Titre	Phase	Dépendances
M-DOCS-CORE	Pipeline cases + documents + extractions	0	Aucune
M-EXTRACTION-ENGINE	Moteur extraction 3 niveaux	0	M-DOCS-CORE
M-EXTRACTION-CORRECTIONS	Corrections append-only	0	M-EXTRACTION-ENGINE
M-CRITERIA-TYPING	Critères typés universels	1	M-EXTRACTION-ENGINE
M-NORMALISATION-ITEMS	Dictionnaire procurement + normalisation	1	M-EXTRACTION-ENGINE
M-SCORING-ENGINE	Scoring multi-critères	2	M-CRITERIA-TYPING, M-NORMALISATION-ITEMS
M-SCORING-TESTS-CRITIQUES	Tests critiques scoring	2	M-SCORING-ENGINE
M-COMMITTEE-CORE	Module comité + LOCK	2	M-DOCS-CORE
M-CBA-TEMPLATES	Templates CBA Excel	3	M-SCORING-ENGINE
M-PV-TEMPLATES	Templates PV Word	3	M-COMMITTEE-CORE
M-CBA-GEN	Génération CBA	3	M-CBA-TEMPLATES, M-SCORING-ENGINE
M-PV-GEN	Génération PV	3	M-PV-TEMPLATES, M-SCORING-ENGINE, M-COMMITTEE-CORE
M-PIPELINE-A-E2E	Pipeline Couche A complet + SLA Classe A	3	M-CBA-GEN, M-PV-GEN
M-SECURITY-CORE	Auth/RBAC/audit/rate limit	4	M-DOCS-CORE
M-TRACE-HISTORY	Historisation scores/éliminations	4	M-SCORING-ENGINE
M-CI-INVARIANTS	Tests CI invariants	4	M-PIPELINE-A-E2E, M-SECURITY-CORE
M-MARKET-DATA-TABLES	Tables mercuriale/history/surveys	5	Aucune
M-MARKET-INGEST	Ingestion mercuriale + auto-feed	5	M-MARKET-DATA-TABLES
M-MARKET-SURVEY-WORKFLOW	Workflow Market Survey terrain	5	M-MARKET-DATA-TABLES
M-MARKET-SIGNAL-ENGINE	Agrégation 3 sources (règles Constitution)	5	M-MARKET-INGEST, M-MARKET-SURVEY-WORKFLOW
M-CONTEXT-UI-PANEL	Panneau UI Market Signal	5	M-MARKET-SIGNAL-ENGINE
M-DICT-FUZZY-MATCH	Fuzzy matching dictionnaire	5	M-NORMALISATION-ITEMS
M-MONITORING-OPS	Logs JSON + métriques Prometheus	6	M-PIPELINE-A-E2E
M-DEVOPS-DEPLOY	Docker/CI/CD/Railway	6	M-MONITORING-OPS
M10-UX-V2	Interface Couche A complète + Registre dépôt	7	M-PIPELINE-A-E2E, M-SECURITY-CORE
M-UX-TEST-TERRAIN	Tests utilisateurs & T_DMS	7	M10-UX-V2
M-ERP-AGNOSTIC-CHECK	Vérification indépendance ERP	7	M-PIPELINE-A-E2E
M-PILOT-EARLY-ADOPTERS	Déploiement pilote & NPS	7	M-UX-TEST-TERRAIN, M-DEVOPS-DEPLOY
3. Milestones Couche A — Documents → Extraction → Normalisation → Scoring → Génération
3.1. M-DOCS-CORE — Pipeline cases + documents + extractions
Fonction

Implémenter le socle canonique :

cases

documents

extractions

liaison stricte entre ces entités

endpoints upload/consultation

règles d’intégrité, statut, audit minimal

Ce que ça résout

Passage propre “processus d’achat → fichiers uploadés → entités exploitables”, avec :

intégrité vérifiable (sha256)

machine d’état extraction lisible par l’UX

traçabilité des actions

base stable pour extraction/corrections

Lien Constitution

Modèle documents/extractions (§6.1)

Append-only (INV-6)

Fidélité au réel (INV-9)

Livrables techniques (obligatoires)
1) Modèle de données (PostgreSQL)

Table cases

id (PK)

reference (string unique)

type (enum : dao | rfq | rfp | simple | negotiated | hybrid)

zone (string)

status (enum : draft | active | closed | archived)

created_at (timestamp)

created_by (FK user)

Table documents (terminologie constitutionnelle)

id (PK)

case_id (FK cases)

kind (enum : dao | offer | annex | market_survey | other)

filename (string)

storage_uri (string)

sha256 (string)

mime_type (string, validé par magic bytes)

size_bytes (int)

page_count (int, nullable)

extraction_status (enum : pending | processing | done | failed)

created_at (timestamp)

created_by (FK user)

metadata (JSONB, optionnel : vendor_hint, language_hint, etc.)

Table extractions

id (PK)

document_id (FK documents)

page_number (int, nullable si extraction globale)

raw_text (text)

structured_data (JSONB)

extraction_method (enum : azure | tesseract | native_pdf | excel_parser | docx_parser | manual)

confidence_score (float 0..1)

provider_payload (JSONB, optionnel)

extracted_at (timestamp)

2) API (FastAPI)

POST /api/cases : créer un case

GET /api/cases/{case_id} : lire un case

POST /api/cases/{case_id}/documents : upload document (validation + sha256 + status pending)

GET /api/documents/{document_id} : métadonnées document

GET /api/documents/{document_id}/extractions : liste extractions

GET /api/extractions/{extraction_id} : détail extraction (raw_text + structured_data)

3) Règles de sécurité minimales

whitelist stricte (PDF, XLSX, DOCX, images autorisées si OCR)

rejet fichiers exécutables

journalisation des actions : création case, upload document, lecture extraction (si sensible)

Tests obligatoires

tests/docs_core/test_cases_crud.py

tests/docs_core/test_upload_validation_magic_bytes.py

tests/docs_core/test_document_extraction_link.py

Definition of Done (bloquante)

tables migrées Alembic (SQL explicite)

endpoints testés

sha256 calculé et stocké

machine d’état extraction_status conforme

tests verts en CI

3.2. M-EXTRACTION-ENGINE — Moteur d’extraction 3 niveaux
Fonction

Construire ExtractionEngine à 3 niveaux :

parsing natif (PDF texte / DOCX / XLSX)

parsing structuré (tableaux, sections, entêtes)

OCR providers (Azure + fallback Tesseract) avec scoring confiance

Ce que ça résout

Extraire texte et données structurées de tout document, avec un niveau de confiance mesurable.

Lien Constitution

Couche A extraction (§2.1)

Stack extraction (§5.2)

SLA Classe A/B (§7.1, §7.2)

Livrables techniques (obligatoires)
1) Service ExtractionEngine

Entrée : document_id

Sortie : insertion dans extractions

Mise à jour documents.extraction_status : pending → processing → done/failed

Erreurs stockées dans documents.metadata (ex : last_extraction_error)

2) Standard structured_data minimal (JSONB)

Champs minimaux (obligatoires même si vides) :

doc_kind

language_detected

detected_tables (liste)

detected_sections (liste)

candidate_criteria (liste brute)

candidate_line_items (liste brute)

currency_detected

dates_detected

supplier_candidates (si doc offre)

3) Providers

PDF natif (sans OCR)

DOCX parser

XLSX parser

OCR Azure (si activé)

OCR Tesseract fallback
Stratégie : natif d’abord → OCR si texte insuffisant.

4) Confidence score

confidence_score calculé et stocké (règles explicites + tests).

Tests obligatoires

tests/extraction/test_engine_pdf_native.py

tests/extraction/test_engine_docx.py

tests/extraction/test_engine_xlsx.py

tests/extraction/test_ocr_fallback.py

tests/extraction/test_confidence_score.py

Definition of Done (bloquante)

fonctionne sur PDF/DOCX/XLSX

OCR branchable + fallback testé

confidence score présent et fiable

CI verte

3.3. M-EXTRACTION-CORRECTIONS — Traçabilité des corrections humaines
Fonction

Implémenter correction humaine champ par champ, append-only, avec before/after, auteur, timestamp, raison.

Ce que ça résout

Corriger l’OCR/parsing sans perdre la donnée originale.

Lien Constitution

Corrections humaines (§6.1)

INV-9 (fidélité au réel)

INV-6 (append-only)

Livrables techniques (obligatoires)
1) Modèle append-only

Table extraction_corrections

id (PK)

extraction_id (FK extractions)

field_path (string, ex: criteria[2].weight)

value_before (text/json)

value_after (text/json)

reason (text)

corrected_by (FK user)

corrected_at (timestamp)

2) Vue “effective” non destructive

Deux représentations obligatoires :

structured_data_original = extractions.structured_data (immutable)

structured_data_effective = application ordonnée des corrections (à la volée ou matérialisée)

3) Endpoint correction

POST /api/extractions/{extraction_id}/corrections

validation anti-conflit : value_before doit correspondre à l’état effectif courant, sinon rejet

4) Enforcement DB-level

interdiction UPDATE/DELETE sur extraction_corrections via trigger + tests

Tests obligatoires

tests/extraction/test_corrections_append_only.py (BLOQUANT CI)

tests/extraction/test_effective_structured_data.py

tests/extraction/test_conflict_detection.py

Definition of Done (bloquante)

append-only prouvé (DB + test)

historique consultable

effective view cohérente

CI verte

3.4. M-CRITERIA-TYPING — Critères typés universels
Fonction

Extraire et typer les critères : commercial, capacity, sustainability, essentials.

Ce que ça résout

Base stable pour scoring universel.

Lien Constitution

Universalité (§1.2)

Scoring Couche A (§2.1)

Livrables techniques (obligatoires)
1) Modèle

Table criteria

id

case_id

source_extraction_id

label

type (enum : commercial | capacity | sustainability | essential)

weight (float, nullable)

is_essential (bool)

created_at, created_by

2) Pipeline

source : structured_data_effective

extraction + typage + persistance

Tests obligatoires

tests/criteria/test_criteria_extraction.py

tests/criteria/test_criteria_typing.py

tests/criteria/test_weights_edge_cases.py

Definition of Done (bloquante)

critères générés automatiquement

robustesse sur cas réels

CI verte

3.5. M-NORMALISATION-ITEMS — Dictionnaire procurement + normalisation
Fonction

Implémenter le dictionnaire procurement et le moteur de normalisation.

Ce que ça résout

Comparaison équitable des offres (items/unités/quantités).

Lien Constitution

Dictionnaire procurement (§2.3)

INV-1

Livrables techniques (obligatoires)
1) Modèle dictionnaire

procurement_items (item canonique)

procurement_item_aliases (aliases)

procurement_units (unités canoniques)

procurement_unit_conversions (conversions)

normalized_line_items (sortie normalisée)

2) Moteur de normalisation

entrée : line items bruts depuis extractions

sortie : normalized_line_items + confidence + flag validation humaine

3) Validation humaine minimale (non destructif)

endpoint liste à valider

endpoint validation → événement append-only

Tests obligatoires

tests/normalisation/test_no_raw_offer_in_scoring.py (BLOQUANT CI)

tests/normalisation/test_alias_resolution.py

tests/normalisation/test_unit_conversion.py

Definition of Done (bloquante)

test “no raw offer in scoring” bloque CI

normalisation comparable produite

validations tracées

CI verte

3.6. M-SCORING-ENGINE — Scoring multi-critères non prescriptif
Fonction

Scoring universel sur critères typés + offres normalisées.

Ce que ça résout

Scores factuels, reproductibles, traçables, sans prescription.

Lien Constitution

Scoring (§2.1)

INV-3 (non prescriptif)

INV-9

Livrables techniques (obligatoires)
1) Modèle

Table supplier_scores

id, case_id, supplier_id

commercial_score, capacity_score, sustainability_score

essential_pass (bool)

weighted_total

computed_at, computed_by, scoring_version

Table supplier_eliminations

id, case_id, supplier_id

reason_codes (JSONB)

details (JSONB)

created_at, created_by

2) Règles scoring

essentials = gate éliminatoire

commercial = basé sur prix normalisé

pondérations issues de criteria.weight

output idempotent et reproductible

3) Interdictions explicites

aucun appel Couche B dans scoring

aucune recommandation

Tests obligatoires

tests/scoring/test_scoring_engine.py

tests/scoring/test_scores_independent_of_couche_b.py (BLOQUANT CI)

tests/scoring/test_elimination_reasons.py

Definition of Done (bloquante)

idempotence

éliminations expliquées

indépendance Couche B prouvée

CI verte

3.7. M-SCORING-TESTS-CRITIQUES — Tests critiques + performance
Fonction

Suite tests unitaires + property-based + E2E : edge cases, 100+ fournisseurs, performance, invariants.

Lien Constitution

INV-2, INV-3

SLA (§7)

Tests obligatoires

tests/scoring/test_scoring_performance_100_suppliers.py

tests/scoring/test_no_raw_offer_in_scoring.py (BLOQUANT CI)

tests/scoring/test_idempotence.py

Definition of Done (bloquante)

CI bloque si lenteur / raw offers / dépendance B

CI verte

3.8. M-COMMITTEE-CORE — Module Comité + LOCK irréversible (DB-level)
Fonction

Créer module comité conforme :

composition proposée par règles (catégorie + seuil)

saisie minimale identité

LOCK irréversible

roster immuable après LOCK

délégation possible sans changer roster

Ce que ça résout

Un comité réel verrouillé ne bouge pas. Toute modification post-lock est non conforme et dangereuse.

Lien Constitution

Gouvernance Comité (§6.4)

INV-6 (append-only)

INV-9 (fidélité au réel)

Livrables techniques (obligatoires)
1) Modèle de données

Table committees

id, case_id

committee_type (evaluation | opening | technical | other)

composition_rule_id

status (draft | locked)

locked_at, locked_by

created_at, created_by

Table committee_members

id, committee_id

role (buyer | finance | budget_holder | technical | observer | chair | other)

last_name, first_name, function, email

required (bool)

created_at, created_by

Table committee_events (append-only)

id, committee_id, case_id

event_type (created | member_added | exception_applied | locked | delegation_added)

payload (JSONB)

created_at, created_by

Table committee_delegations (append-only)

id, committee_id, member_id

delegate_name, delegate_function, delegate_email

reason

valid_from, valid_to (optionnel)

created_at, created_by

2) Enforcement DB-level (non négociable)

Après committees.status = locked :

INSERT/UPDATE/DELETE sur committee_members doit échouer

transition locked → draft doit échouer

Implémentation : triggers PostgreSQL levant exception + tests automatisés.

3) Rules engine composition (data-driven)

Table committee_composition_rules

id, category, threshold_band, rule_json, justification_text

Service CommitteeBuilder

entrée : case.category, case.amount, procurement_method

sortie : roles + required

aucune logique non traçable

4) API (FastAPI)

POST /api/cases/{case_id}/committee (crée draft)

POST /api/committees/{committee_id}/members (draft uniquement)

POST /api/committees/{committee_id}/lock

POST /api/committees/{committee_id}/delegations (draft ou locked, sans toucher roster)

GET /api/committees/{committee_id} (détails + events + delegations)

Tests obligatoires

tests/committee/test_committee_lock_prevents_member_update.py (BLOQUANT CI)

tests/committee/test_lock_is_irreversible.py (BLOQUANT CI)

tests/committee/test_delegation_without_roster_change.py

tests/committee/test_composition_rules.py

Definition of Done (bloquante)

LOCK irréversible prouvé (DB + tests)

délégation possible post-lock

events append-only présents

CI verte

3.9. M-CBA-TEMPLATES — Templates CBA Excel normalisés

(Template canonique, placeholders stables, versionnement strict, tests structure template)

3.10. M-PV-TEMPLATES — Templates PV Word normalisés

(Template canonique, placeholders comité officiel + délégations, versionnement strict, tests structure template)

3.11. M-CBA-GEN — Génération CBA automatisée

(openpyxl, exports avec sha256, endpoints generate/list, tests génération + intégrité)

3.12. M-PV-GEN — Génération PV automatisée

(python-docx, inclusion roster + délégations, sha256, tests affichage comité)

3.13. M-PIPELINE-A-E2E — Pipeline Couche A complet + SLA Classe A

(fixtures réalistes, timers CI, test bloquant SLA < 60s)

Nota : Les sections 3.9 à 3.13 conservent exactement la structure validée par Claude, avec les dépendances corrigées en Registry. Leur contenu détaillé reste opposable selon le même format “Fonction / Livrables / Tests / DoD”.

4. Milestones Couche B — Mémoire, Market Signal, Dictionnaire étendu
4.1. M-MARKET-DATA-TABLES — 3 sources Market Signal

(schémas + indexes + migrations + tests)

4.2. M-MARKET-INGEST — Import mercuriale + auto-feed historiques

(idempotence + hook post-décision + tests)

4.3. M-MARKET-SURVEY-WORKFLOW — Workflow Market Survey terrain

(min 3 cotations/item, validité 90 jours, zone obligatoire, UI/API, gate GO prod)

4.4. M-MARKET-SIGNAL-ENGINE — Agrégation 3 sources + règles Constitution (CORRIGÉ)
Fonction

Fournir un signal marché non prescriptif, explicable, basé sur 3 sources.

Lien Constitution

§3.2–§3.4 (Market Signal)

INV-3 (non prescriptif)

Règles d’agrégation (opposables, alignées Constitution)

Market Survey terrain prévaut pour le prix actuel (si ≤ 90 jours, min. 3 cotations/item).

Historique des décisions prévaut pour tendances et cohérence opérationnelle (fenêtre 24 mois).

Mercuriale officielle sert de borne supérieure réglementaire (prix plafond / référence légale).

Dégradation (informatif uniquement)

manque 1 source → ⚠️

manque 2 sources → 🔴

manque 3 sources → ⬛

Interdiction absolue

Le Market Signal n’a aucun impact sur supplier_scores. Test CI bloquant obligatoire.

4.5. M-CONTEXT-UI-PANEL — UI Market Signal (read-only)

(test read-only bloquant, aucun write Couche A)

4.6. M-DICT-FUZZY-MATCH — fuzzy matching

(perf < 100ms bloquant, validation humaine sous seuil, append-only)

5. Milestones Transverses — Sécurité, Traçabilité, Performance, CI

(M-SECURITY-CORE, M-TRACE-HISTORY, M-CI-INVARIANTS, M-MONITORING-OPS, M-DEVOPS-DEPLOY — structure validée, append-only, triggers + tests bloquants)

6. Milestones Produit & Terrain — UX, Early adopters, ERP agnostique
6.1. M10-UX-V2 — Interface Couche A complète + Registre dépôt

(flow complet + registre dépôt append-only + comité + tests bloquants)

6.2. M-UX-TEST-TERRAIN — mesures T_DMS
6.3. M-ERP-AGNOSTIC-CHECK — respect INV-7
6.4. M-PILOT-EARLY-ADOPTERS — NPS + adoption
7. Definition of Done (commune à tous les milestones)

(texte complet validé, inchangé, opposable)

8. Ordre d’exécution recommandé (séquence stricte)

(liste complète 1 → 28 validée, inchangée)

9. Gates GO/NO-GO

(Alpha interne / Pilote terrain / Production externe BLOQUANT Market Signal : inchangé, opposable)

10. Règle spéciale Comité (rappel opposable)

(rappel complet, test CI bloquant, enforcement DB-level : inchangé, opposable)

11. Versionnement & Gouvernance

Toute modification = nouvelle version + nouvel ADR + nouveau freeze

Tag git de freeze + SHA256 dans manifest

Copie immuable dans dossier freeze

STATUT FINAL

Ce document DMS — MILESTONES EXECUTION PLAN V3.3.2 est désormais :

✅ CANONIQUE

✅ OPPOSABLE

✅ FREEZABLE

✅ aligné Constitution (Market Signal + références § + terminologie documents + dépendances)

Fin du document.
