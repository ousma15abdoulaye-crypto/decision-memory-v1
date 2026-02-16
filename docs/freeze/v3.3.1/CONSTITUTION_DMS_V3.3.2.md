📘 CONSTITUTION DU DECISION MEMORY SYSTEM (DMS)
VERSION V3.3.2 — FROZEN (RÉFÉRENCE CANONIQUE)
Auteur : Abdoulaye Ousmane
Rôle : Founder & CTO — System Engineer · Tech Lead · Procurement Analyst
Statut : OFFICIEL · OPPOSABLE · FROZEN
Date de gel : 2026-02-16 (CET)
Cible : États · ONG · Entreprises privées · Mines
Portée géographique : Mali · Afrique de l’Ouest · extensible internationalement
Mode : Online-first · Haute performance · Zéro saisie manuelle répétitive — l’humain intervient pour contrôle et arbitrage uniquement

§0 — RAISON D’ÊTRE
Le Decision Memory System (DMS) est un système logiciel de procurement conçu pour :

Automatiser 80–90 % du travail cognitif entre l’ouverture d’un processus d’achat et la décision humaine finale.
Accélérer la production des dossiers de décision à un niveau incompatible avec le travail manuel.
Structurer et conserver la mémoire décisionnelle de chaque organisation utilisatrice.
Établir un standard de référence du procurement moderne en Afrique.
Constat fondateur :
Les organisations ne manquent pas de règles.
Elles manquent de vitesse, de mémoire exploitable et de rigueur reproductible.

§1 — PORTÉE FONCTIONNELLE
§1.1 — Universalité des processus d’achat
Le DMS couvre l’ensemble des processus d’achat formalisés et informels :

Type	Description	Couvert
DAO	Dossier d’Appel d’Offres (national/international)	✅
RFQ	Request for Quotation	✅
RFP	Request for Proposal	✅
Achat simple	Consultation directe, achat récurrent	✅
Marché négocié	Gré à gré encadré	✅
Procédure hybride	ONG, entreprises, mines	✅
Règle : le terme “DAO” est utilisé comme exemple de processus formel. Il ne constitue en aucun cas une limitation du périmètre fonctionnel.

§1.2 — Abstraction canonique
Le DMS repose sur une abstraction unique :

Processus d’achat = Règles + Critères + Offres + Décision humaine

Les différences entre types de processus portent sur :

le niveau de formalité (nombre d’étapes, validations),
la structure des critères (pondérations, seuils),
les livrables requis (CBA, PV, rapport).
Elles ne portent jamais sur :

l’architecture du moteur (Couche A/B),
la logique de traçabilité,
la mémoire décisionnelle.
Règle : le moteur de scoring est configurable (pondérations/formules/critères actifs) mais repose sur une base algorithmique unique.

§2 — ARCHITECTURE FONDATRICE À DEUX COUCHES
§2.1 — Couche A : Moteur d’exécution
La Couche A est le cœur opérationnel du DMS.

Mission : automatiser le travail cognitif entre la réception des documents et la décision humaine.

§2.1.1 — Responsabilités Couche A (exhaustives et non négociables)
Fonction	Description	Entrée	Sortie
Ingestion	Réception et classement des documents (PDF, scans, Excel, Word)	Fichiers bruts	Documents indexés en base
Extraction	Extraction texte + identification critères/lots/éligibilité	Documents indexés	Extractions (raw_text + structured_data JSONB)
Normalisation	Standardisation des offres via dictionnaire procurement (§2.3)	Offres brutes	Items normalisés, unités alignées
Scoring	Calcul scores multi-critères (commercial/capacity/sustainability/essentials/total)	Critères typés + offres normalisées	supplier_scores + supplier_eliminations
Génération	Production livrables officiels	Scores + données + templates	Excel CBA + Word PV
Traçabilité	Journalisation append-only des actions/événements	Toute mutation	Audit trail immutable
§2.1.2 — Règle cardinale Couche A
Toute opération qu’un utilisateur effectue actuellement dans Excel et qui est automatisable est considérée comme un échec de la Couche A.

§2.1.3 — Classement calculé (rank) : clarification opposable
Le DMS peut calculer un rank (tri mathématique par total_score) à des fins d’affichage.

Règle :

le rank est un résultat arithmétique (tri),
il ne constitue ni recommandation, ni prescription, ni arbitrage,
la décision finale appartient au comité.
§2.2 — Couche B : Mémoire décisionnelle (non prescriptive)
La Couche B est la mémoire vivante et l’intelligence contextuelle du DMS.

Mission : capitaliser, structurer et restituer la connaissance marché/décisionnelle sans jamais prescrire.

§2.2.1 — Responsabilités Couche B
Fonction	Description
Historisation	Archivage automatique des décisions passées : prix payés, fournisseurs, délais, zones, volumes
Contextualisation	Restitution de comparables : tendances, écarts, anomalies factuelles
Market Signal	Agrégation des 3 sources de vérité (§3)
Alertes factuelles	Signalement d’écarts statistiques (ex: ±30%) sans jugement de valeur
§2.2.2 — Interdictions absolues Couche B
La Couche B :

❌ ne décide pas
❌ ne recommande pas
❌ ne prescrit pas
❌ ne modifie jamais l’état d’un processus Couche A
❌ ne classe pas les fournisseurs
❌ ne change aucun score
§2.2.3 — Principe de séparation structurelle (inviolable)
Couche A = ACTION & CALCUL (mute l’état du système)
Couche B = MÉMOIRE & CONTEXTE (read-only sur processus en cours)
Aucune fonctionnalité ne peut chevaucher les deux couches.

§2.3 — Dictionnaire Procurement (brique partagée A/B)
Le dictionnaire procurement est une brique fondatrice partagée entre les Couches A et B.

Rôle : fournir un référentiel canonique pour normaliser items, unités, identités fournisseurs.

§2.3.1 — Contenu obligatoire
Composant	Description	Exemple
Items canoniques	nom standard + aliases + code mercuriale	“Rame papier A4 80g”
Unités	unité canonique + équivalences + ratios	“Rame = 500 feuilles”
Fournisseurs	nom canonique + variantes + identifiants	“ETS KONATÉ SARL”
Catégories	classification hiérarchique alignée mercuriale	Groupe → Sous-groupe
Résolution ambiguïtés	fuzzy + validation humaine	seuil 80%
§2.3.2 — Règle de validation humaine
Algorithme fuzzy matching (Levenshtein + token-based).
Seuil configurable (défaut 80%).
En dessous du seuil : validation humaine requise.
§3 — MARKET SURVEY & MARKET SIGNAL
§3.1 — Statut constitutionnel
Le Market Survey est une brique critique du DMS.
Il n’est ni optionnel, ni secondaire.

§3.2 — Les trois sources de vérité
#	Source	Nature	Fraîcheur	Autorité
1	Mercuriale officielle	Prix réglementés (par zone/année)	annuelle	référence légale
2	Historique décisions	Prix réellement payés (organisation)	continue (auto-feed)	référence opérationnelle
3	Market Survey terrain	Enquête prix avant lancement (min 3 cotations/item)	90 jours	référence conjoncturelle
§3.3 — Règles d’agrégation
§3.3.1 — Priorité en cas de conflit
Market Survey terrain (prix du moment)
Historique décisions (tendances / fiabilité)
Mercuriale (borne supérieure/plafond légal)
§3.3.2 — Comportement quand une source manque
Source manquante	Comportement	Indicateur UI
Mercuriale	signal réduit à 2 sources, mention “Pas de référence officielle”	⚠️
Historique	signal réduit à 2 sources, mention “Aucun précédent”	⚠️
Market Survey	signal réduit à 2 sources, mention “Pas d’enquête terrain”	⚠️
2 sources manquantes	signal dégradé, “Contexte insuffisant”	🔴
3 sources manquantes	aucun signal, “Aucune donnée marché”	⬛
§3.3.3 — Politique de fraîcheur
Source	Fenêtre de validité	Au-delà
Mercuriale	année en cours + année précédente	“obsolète” + coefficient inflation configurable
Historique	24 mois glissants	archivé, non inclus dans signal actif
Market Survey	90 jours	“à actualiser”
§3.4 — Flux Market Signal → Couche A (read-only)
Market Survey ──┐
Mercuriale ─────┼──→ MarketSignalProvider ──→ UI Context Panel
Historique ─────┘

Règle : le signal est affiché mais ne modifie pas les scores.

§4 — INVARIANTS FONDAMENTAUX (OPPOSABLES)
Toute évolution du DMS doit respecter les invariants suivants.
Chaque invariant implique une règle opérationnelle et un test CI de conformité (Annexe A).

INV-1 — Réduction de la charge cognitive
Règle : chaque fonctionnalité doit réduire le temps/effort vs manuel.
Test : T_DMS < T_manuel × 0.2 (sur opérations mesurables).

INV-2 — Primauté de la Couche A
Règle : la Couche A doit produire CBA/PV même si Couche B indisponible.
Test : Couper Couche B → export valide.

INV-3 — Mémoire non prescriptive
Règle : Couche B n’alimente aucun score ni classement.
Test : supplier_scores ne dépend d’aucune query Couche B.

INV-4 — Online-first
Règle : pas de mode offline produit.
Test : absence de composants offline sync / durable local store.

INV-5 — CI verte obligatoire
Règle : aucun merge si CI rouge.
Test : branch protection + checks required.

INV-6 — Append-only & traçabilité
Règle : mutations métier journalisées immutable.
Test : DELETE/UPDATE interdits sur tables de trace.

INV-7 — ERP-agnostique
Règle : aucune dépendance ERP, seulement API + exports.
Test : scan imports/strings + règles CI.

INV-8 — Survivabilité & lisibilité
Règle : un senior doit comprendre en 48h.
Test : README à jour + schéma DB documenté + ADRs présents.

INV-9 — Fidélité au réel & neutralité
Règle : scores calculés, jamais “ajustés”.
Corrections humaines append-only with before/after + reason.
Test : score == formule + test extraction_corrections append-only.

§5 — STACK TECHNIQUE CANONIQUE
§5.1 — Backend & Data
Composant	Choix	Justification
Langage	Python 3.11+	écosystème data/ML, performance suffisante
Framework API	FastAPI	async + validation + OpenAPI
DB	PostgreSQL 15+	source unique vérité, JSONB, index
Migrations	Alembic	SQL brut uniquement — pas d’autogenerate
Accès DB	SQL paramétré via helpers synchrones	contrôle total
Cache	Redis (optionnel V3)	cache non-autoritaire
Qualification Redis (opposable)
Redis est un cache reconstructible. PostgreSQL est l’unique source de vérité.

Interdiction de stocker dans Redis :

entités métier (scores/décisions/éliminations),
traçabilité (audit),
toute donnée non reconstructible sans Redis.
§5.2 — Extraction & Génération
Composant	Choix	Rôle
OCR primaire	Azure Document Intelligence	scans/PDF
OCR fallback	Tesseract	fallback
Excel	openpyxl	CBA formules/onglets/styles
Word	python-docx	PV placeholders
PDF parsing	pdfplumber / PyMuPDF	texte natif
§5.3 — DevOps & Déploiement
Composant	Choix
Repo	GitHub (mono-repo)
CI	GitHub Actions
CD	Railway (Nixpacks)
Conteneurs	Docker + docker-compose
Healthcheck	GET /api/health
§5.4 — Sécurité
Composant	Choix
Auth	JWT (access + refresh)
Autorisation	RBAC 5 rôles (admin/manager/buyer/viewer/auditor)
Audit	audit_log append-only + log_action()
Rate limit	par user + endpoint
Upload	magic bytes + taille max + whitelist
Secrets	env vars uniquement
CORS	domaine prod uniquement
§6 — MODÈLE DE DONNÉES CANONIQUE (POSTGRES)
§6.1 — Entité d’entrée : documents → extractions → extraction_corrections
documents

id (PK)

case_id (FK)

kind (enum) # dao | offer | annex | market_survey | other

filename

storage_uri

sha256 # intégrité

mime_type # validé magic bytes

size_bytes

page_count

extraction_status # pending | processing | done | failed

created_at

created_by (FK users)

extractions

id (PK)

document_id (FK)

page_number (nullable)

raw_text

structured_data (jsonb)

extraction_method # azure | tesseract | native_pdf | manual

confidence_score

extracted_at

extraction_corrections (append-only)

id (PK)

extraction_id (FK)

field_path # ex: "lots[0].criteria[2].weight"

value_before

value_after

reason

corrected_by (FK users)

corrected_at

§6.2 — Entités fondamentales (Couche A)
cases

id (PK)

reference

type (enum) # dao | rfq | rfp | simple | negotiated | hybrid

status

zone (nullable)

amount (nullable)

metadata (jsonb)

created_at

created_by (FK users)

suppliers

id (PK)

name_canon

aliases (text[])

tin (nullable)

metadata (jsonb)

offers

id (PK)

case_id (FK)

supplier_id (FK)

items (jsonb) # brut (avant normalisation)

total_price

currency

submitted_at

created_at

§6.3 — Critères & scoring (Couche A)
criteria

id (PK)

case_id (FK)

name

category (enum) # commercial | capability | sustainability | essential

weight (numeric)

formula (text)

is_essential (bool)

created_at

supplier_scores

id (PK)

case_id (FK)

supplier_id (FK)

commercial_score (numeric)

capacity_score (numeric)

sustainability_score (numeric)

essential_pass (bool)

total_score (numeric)

rank (int, nullable) # tri mathématique (non prescriptif)

calculated_at

supplier_eliminations

id (PK)

case_id (FK)

supplier_id (FK)

reason (text)

rule_ref (text)

eliminated_at

§6.4 — Gouvernance Comité (LOCK immuable + délégation)
§6.4.1 — Tables canoniques
committee

id (PK)

case_id (FK, UNIQUE) # 1 comité par case

status (enum) # draft | locked

rule_ref (text) # référence règle appliquée (ex: SCI_MLI_PROC_2024_§...)

justification (text) # justification lisible

locked_at (timestamp, nullable)

locked_by (FK users, nullable)

created_at

created_by (FK users)

committee_members (ROSTER OFFICIEL)

id (PK)

committee_id (FK)

role (text) # buyer | finance | budget_holder | technical | observer | chair | ...

last_name

first_name

function_title

email (nullable)

required (bool)

min_level (text, nullable)

created_at

created_by (FK users)

committee_delegations (POST-LOCK ONLY, append-only)

id (PK)

committee_id (FK)

member_id (FK committee_members)

delegate_last_name

delegate_first_name

delegate_function_title

delegate_email (nullable)

reason (text)

starts_at (nullable)

ends_at (nullable)

created_at

created_by (FK users)

committee_events (append-only)

id (PK)

committee_id (FK)

event_type (text) # created | rule_applied | member_added | exception_logged | locked | delegation_added | export_generated | ...

payload (jsonb)

created_at

created_by (FK users)

§6.4.2 — Contraintes d’enforcement DB-level (obligatoires)
LOCK irréversible : committee.status ne peut pas passer de locked à draft.
Immutabilité roster : si committee.status = locked, toute tentative INSERT/UPDATE/DELETE sur committee_members doit échouer.
Délégation autorisée après LOCK : INSERT sur committee_delegations autorisé, sans toucher committee_members.
Events append-only : committee_events = INSERT only.
Audit global : chaque action critique doit produire un audit_log (append-only).
(Implémentation typique : triggers PostgreSQL + REVOKE droits UPDATE/DELETE.)

§6.5 — Entités Market Signal (Couche B)
mercurials

id (PK)

item_code

item_name

unit

zone

year

price_min

price_avg

price_max

group_code

source

decision_history

id (PK)

case_id (FK)

item_id (FK procurement_dictionary)

supplier_id (FK suppliers)

price_paid

quantity

decision_date

zone

market_surveys

id (PK)

case_id (FK)

item_id (FK procurement_dictionary)

supplier_name

price_quoted

date_surveyed

location

surveyor

procurement_dictionary

id (PK)

item_name_canonical

aliases (text[])

unit_canonical

unit_aliases (text[])

category_code

mercuriale_ref (jsonb)

procurement_type (text)

tags (text[])

§6.6 — Tables de traçabilité (append-only)
audit_log (append-only)

id (PK)

user_id

action

entity

entity_id

payload (jsonb)

timestamp

score_history (append-only)

id (PK)

case_id

supplier_id

scores (jsonb)

calculated_at

version

elimination_log (append-only)

id (PK)

case_id

supplier_id

reason

rule_ref

timestamp

by_user

Contraintes SQL obligatoires
REVOKE DELETE, UPDATE sur audit_log, score_history, elimination_log, extraction_corrections, committee_events, committee_delegations
Seul INSERT est autorisé sur ces tables.
§7 — CONTRAINTES DE PERFORMANCE (SLA INTERNES)
Toute régression au-delà des seuils définis bloque le merge en CI.

§7.1 — Classe A — Documents natifs (PDF texte, Excel, Word)
Métrique	Cible	Mesure
Pipeline DAO → CBA complet	< 60s	timer end-to-end CI
Upload + extraction 1 doc	< 15s	timer CI
Génération Excel CBA	< 10s	timer CI
Génération Word PV	< 5s	timer CI
§7.2 — Classe B — Scans OCR
Métrique	Cible	Mesure
Upload + mise en queue	< 5s	timer CI
OCR asynchrone	budget séparé	monitoring
OCR ne bloque pas app	queue + callback	test intégration
§7.3 — Commun
Métrique	Cible	Mesure
Query Market Signal (1 item)	< 200ms	benchmark CI
Fuzzy match dictionnaire	< 100ms	benchmark CI
Charge	10 DAO concurrents sans dégradation >2×	test charge
Cold start Railway	< 30s	healthcheck
§8 — POSITIONNEMENT ERP & INTÉGRATION
§8.1 — Principe d’indépendance
Le DMS est ERP-agnostique :

ne dépend d’aucun ERP pour fonctionner,
ne remplace pas un ERP,
structure la décision d’achat (zone non couverte par ERP).
§8.2 — Formats d’intégration
Type	Format	Usage
Export CBA	Excel (.xlsx)	comité + archivage
Export PV	Word (.docx)	PV officiel
API REST	JSON (FastAPI)	intégration ERP/BI
Export données	CSV/JSON	audit/migration
§8.3 — Positionnement
DMS structure la décision | ERP enregistre l’exécution

§9 — GOUVERNANCE & CLAUSES JURIDIQUES
§9.1 — Propriété intellectuelle
Le DMS (code, architecture, Constitution, documentation) est la propriété exclusive d’Abdoulaye Ousmane et de toute entité légale qu’il désignera.

§9.2 — Confidentialité des données
Les données ingérées appartiennent à l’organisation utilisatrice. Le DMS :

ne partage pas les données entre organisations,
ne les utilise pas pour entraînement/profilage,
garantit la suppression sur demande.
§9.3 — Réversibilité
Toute organisation peut :

exporter l’intégralité des données en formats ouverts,
résilier sans perte de données.
§9.4 — Autorité interprétative
En cas de litige d’interprétation, l’auteur est l’autorité finale. Toute interprétation divergente par un tiers requiert validation explicite.

§9.5 — Clause de freeze (V3.3.2)
Cette Constitution V3.3.2 est gelée par décision du fondateur. Toute évolution future :

doit démontrer l’alignement avec les invariants (§4),
doit être documentée comme amendement versionné,
nécessite l’approbation explicite du fondateur,
n’invalide pas rétroactivement les décisions prises sous version précédente.
§10 — FORMULE FONDATRICE
Le DMS est un système à deux couches :

un moteur d’exécution (Couche A),
une mémoire intelligente non prescriptive (Couche B), articulé autour d’un dictionnaire procurement et d’un Market Signal à trois sources de vérité, conçu pour automatiser, accélérer et structurer tous les processus d’achat, sans jamais décider à la place du comité.
ANNEXE A — Concordance Invariants ↔ Tests CI (OPPOSABLE)
Invariant	Test CI correspondant	Type
INV-1	test_pipeline_under_60s	Performance
INV-2	test_couche_a_standalone_exports_without_couche_b	Intégration
INV-3	test_scores_independent_of_couche_b	Unitaire
INV-4	test_no_offline_components_static_scan	Statique
INV-5	required_checks_branch_protection + coverage_gate	CI
INV-6	test_append_only_tables_reject_update_delete	Sécurité
INV-7	test_no_erp_dependency_scan	Statique
INV-8	test_readme_exists + test_schema_documented + test_adrs_present	Documentation
INV-9	test_score_equals_formula_output + test_extraction_corrections_append_only	Unitaire/Sécurité
Tests CI comité (dérivés INV-6 / INV-9, obligatoires)
test_committee_lock_irreversible
test_committee_roster_immutable_after_lock
test_committee_delegation_allowed_post_lock
test_committee_events_append_only
ANNEXE B — Changelog (versionné)
Version	Date	Changements
V1.0	2024-Q3	Vision initiale, Couche A uniquement
V2.0	2024-Q4	Ajout Couche B, Market Survey
V3.0	2025-01	Stack technique, invariants
V3.2	2025-02	Portée universelle (DAO/RFQ/RFP), ERP-agnostique
V3.3	2025-02-15	Dictionnaire + Market Signal 3 sources + modèle données + SLA + clauses juridiques + tests invariants
V3.3.1	2026-02-15	Patch : SLA dual-class, INV-4/INV-9, Redis qualifié, documents/extractions/corrections
V3.3.2	2026-02-16	Ajout gouvernance comité (LOCK immuable + délégation), enforcement DB-level, tables comité, correction clause freeze, clarification rank non prescriptif, extension Annex A tests comité
🔐 STATUT FINAL
Ce document CONSTITUTION DMS V3.3.2 est désormais : ✅ OFFICIEL
✅ FROZEN
✅ RÉFÉRENCE CANONIQUE UNIQUE
✅ OPPOSABLE au code, aux PR, aux agents IA, aux choix techniques, et aux extensions futures
