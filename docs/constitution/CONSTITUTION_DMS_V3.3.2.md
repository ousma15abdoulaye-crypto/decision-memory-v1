
📘 CONSTITUTION DU DECISION MEMORY SYSTEM
VERSION V3.3.1 — FROZEN (RÉFÉRENCE CANONIQUE)
Auteur : Abdoulaye Ousmane
Rôle : Founder & CTO — System Engineer · Tech Lead · Procurement Analyst
Statut : OFFICIEL · OPPOSABLE · FROZEN
Date de gel : 2026-02-15
Cible : États · ONG · Entreprises privées · Mines
Portée géographique : Mali · Afrique de l’Ouest · extensible internationalement
Mode : Online-first · Haute performance · Zéro saisie manuelle répétitive — l’humain intervient pour contrôle et arbitrage uniquement
§0 — RAISON D’ÊTRE
Le Decision Memory System (DMS) est un système logiciel de procurement conçu pour :
1.	Automatiser 80–90 % du travail cognitif entre l’ouverture d’un processus d’achat et la décision humaine finale.
2.	Accélérer la production des dossiers de décision à un niveau incompatible avec le travail manuel.
3.	Structurer et conserver la mémoire décisionnelle de chaque organisation utilisatrice.
4.	Établir un standard de référence du procurement moderne en Afrique.
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
Le terme DAO est utilisé dans la documentation comme exemple de processus formel. Il ne constitue en aucun cas une limitation du périmètre fonctionnel.
________________________________________
§1.2 — Abstraction canonique
Le DMS repose sur une abstraction unique :
$$\text{Processus d’achat} = \text{Règles} + \text{Critères} + \text{Offres} + \text{Décision humaine}$$
Les différences entre types de processus portent sur :
•	le niveau de formalité (nombre d’étapes, validations requises),
•	la structure des critères (pondérations, seuils),
•	les livrables requis (CBA, PV, rapport).
Elles ne portent jamais sur :
•	l’architecture du moteur (Couche A/B),
•	la logique de traçabilité,
•	la mémoire décisionnelle.
Le moteur de scoring est configurable par type de processus (pondérations, formules, critères actifs) mais repose sur une base algorithmique unique.
________________________________________
§2 — ARCHITECTURE FONDATRICE À DEUX COUCHES
§2.1 — Couche A : Moteur d’exécution
La Couche A est le cœur opérationnel du DMS.
Mission : Automatiser le travail cognitif entre la réception des documents et la décision humaine.
Responsabilités (exhaustives et non négociables) :
Fonction	Description	Entrée	Sortie
Ingestion	Réception et classement des documents (PDF, scans, Excel, Word)	Fichiers bruts	Documents indexés en base
Extraction	Extraction du texte, identification des critères, lots, règles d’éligibilité	Documents indexés	Données structurées JSON
Normalisation	Standardisation des offres via le dictionnaire procurement (§2.3)	Données brutes fournisseur	Items normalisés, unités alignées
Scoring	Calcul des scores multi-critères (commercial, capacity, sustainability, essentials, total)	Critères typés + offres normalisées	supplier_scores + supplier_eliminations
Enrichissement	Injection du Market Signal (§3) dans le contexte de décision	3 sources de vérité	Indicateurs contextuels (non prescriptifs)
Génération	Production automatique des livrables officiels	Scores + données + templates	Fichiers Excel CBA + Word PV
Traçabilité	Journalisation append-only de chaque action	Toute mutation	Audit trail horodaté, immutable
Règle cardinale :
Toute opération qu’un utilisateur effectue actuellement dans Excel et qui est automatisable est considérée comme un échec de la Couche A.
________________________________________
§2.2 — Couche B : Mémoire décisionnelle
La Couche B est la mémoire vivante et l’intelligence contextuelle du DMS.
Mission : Capitaliser, structurer et restituer la connaissance marché et décisionnelle sans jamais prescrire.
Responsabilités :
Fonction	Description
Historisation	Archivage automatique des décisions passées, prix payés, fournisseurs, délais, zones, volumes
Contextualisation	Fourniture de données comparables (historiques, tendances, écarts, anomalies factuelles)
Market Signal	Agrégation des 3 sources de vérité (§3)
Alertes factuelles	Signalement des écarts statistiques (±30% du prix moyen) sans jugement de valeur
Interdictions absolues — la Couche B :
•	❌ Ne décide pas.
•	❌ Ne recommande pas.
•	❌ Ne prescrit pas.
•	❌ Ne modifie jamais l’état d’un processus de la Couche A.
•	❌ Ne classe pas les fournisseurs.
Principe de séparation :
Couche A = ACTION & CALCUL (mute l’état du système)
Couche B = MÉMOIRE & CONTEXTE (read-only sur les processus en cours)
La frontière entre les deux est structurelle et inviolable. Aucune fonctionnalité ne peut chevaucher les deux couches.
________________________________________
§2.3 — Dictionnaire Procurement
Le dictionnaire procurement est une brique fondatrice partagée entre les Couches A et B.
Rôle : Fournir un référentiel canonique pour la normalisation des items, unités, et identités fournisseurs.
Contenu obligatoire :
Composant	Description	Exemple
Items canoniques	Nom standardisé + aliases + code mercuriale	"Rame papier A4 80g" → aliases: ["papier A4", "rame A4", "papier photocopie A4"]
Unités	Unité canonique + équivalences + ratios de conversion	"Rame" = 500 feuilles ; "Carton" = 5 rames
Fournisseurs	Nom canonique + variantes + identifiants	"ETS KONATÉ SARL" → ["Konaté", "KONATE", "Ets Konate"]
Catégories	Classification hiérarchique alignée sur la mercuriale	Groupe → Sous-groupe → Item
Résolution des ambiguïtés :
•	Algorithme de fuzzy matching (Levenshtein + token-based).
•	Seuil de confiance configurable (défaut : 80%).
•	En dessous du seuil : validation humaine requise.
________________________________________
§3 — MARKET SURVEY & MARKET SIGNAL
§3.1 — Statut constitutionnel
Le Market Survey est une brique critique du DMS. Il constitue la source la plus actuelle du contexte prix. Il n’est ni optionnel, ni secondaire.
________________________________________
§3.2 — Les trois sources de vérité
Le Market Signal repose obligatoirement sur l’agrégation de trois sources :
#	Source	Nature	Fraîcheur	Autorité
1	Mercuriale officielle	Prix réglementés publiés par l’État (par zone, par année)	Annuelle	Référence légale — prix plafond
2	Historique des décisions	Prix réellement payés par l’organisation lors de processus passés	Continue (auto-feed post-décision)	Référence opérationnelle — réalité terrain
3	Market Survey terrain	Enquêtes de prix réalisées avant le lancement du processus (min. 3 cotations/item)	Ponctuelle (pré-processus)	Référence conjoncturelle — prix du moment
________________________________________
§3.3 — Règles d’agrégation
Priorité en cas de conflit :
1.	Le Market Survey terrain prévaut pour les prix actuels (plus récent).
2.	L’historique des décisions prévaut pour les tendances et la fiabilité fournisseur.
3.	La mercuriale officielle sert de borne supérieure réglementaire.
Comportement quand une source manque :
Source manquante	Comportement	Indicateur UI
Mercuriale	Signal réduit à 2 sources, mention "Pas de référence officielle"	⚠️ Jaune
Historique	Signal réduit à 2 sources, mention "Aucun précédent"	⚠️ Jaune
Market Survey	Signal réduit à 2 sources, mention "Pas d’enquête terrain"	⚠️ Jaune
2 sources manquantes	Signal dégradé, mention "Contexte prix insuffisant"	🔴 Rouge
3 sources manquantes	Aucun signal, affichage "Aucune donnée marché"	⬛ Gris
Politique de fraîcheur :
Source	Fenêtre de validité	Au-delà
Mercuriale	Année en cours + année précédente	Marquée "obsolète" + coefficient d’inflation configurable
Historique	24 mois glissants	Données au-delà = archivées, non incluses dans le signal actif
Market Survey	90 jours	Marqué "à actualiser"
________________________________________
§3.4 — Flux Market Signal → Couche A
Le Market Signal alimente la Couche A en lecture seule :
Market Survey ──┐
Mercuriale ─────┼──→ MarketSignalProvider ──→ Panneau contextuel (UI)
Historique ─────┘                              │
                                               ▼
                                    Couche A (scoring)
                                    [Le signal est AFFICHÉ
                                     mais ne MODIFIE PAS
                                     les scores]
________________________________________
§4 — INVARIANTS FONDAMENTAUX
Toute évolution du DMS doit respecter les invariants suivants. Chaque invariant est défini par une règle opérationnelle et un test de conformité.
________________________________________
INV-1 — Réduction de la charge cognitive
Règle : Chaque fonctionnalité doit réduire le temps ou l’effort cognitif de l’utilisateur par rapport au processus manuel équivalent.
Test :
$T_{\text{DMS}} < T_{\text{manuel}} \times 0.2$
pour toute opération mesurable (extraction, scoring, génération CBA).
________________________________________
INV-2 — Primauté de la Couche A
Règle : La Couche A fonctionne de manière autonome. La Couche B enrichit mais n’est jamais requise pour produire un livrable complet.
Test : Couper la Couche B → le système génère toujours un CBA/PV valide.
________________________________________
INV-3 — Mémoire non prescriptive
Règle : La Couche B informe, ne prescrit pas. Aucune donnée de la Couche B ne modifie un score ou un classement.
Test : Aucun champ de supplier_scores n’est alimenté par une query Couche B.
________________________________________
INV-4 — Online-first
Règle : Le DMS est conçu pour un usage connecté en production. Aucun mode offline n’est un objectif produit. L’exécution locale (dev, tests, CI) reste pleinement supportée.
Test : Aucun composant de synchronisation offline, stockage local durable, ou file d’attente offline n’est implémenté dans le cœur applicatif.
________________________________________
INV-5 — CI verte obligatoire
Règle : Aucun merge sur la branche principale n’est autorisé si la CI est rouge.
Test : GitHub Actions bloque le merge si un test échoue ou si la coverage est sous le seuil.
________________________________________
INV-6 — Append-only & traçabilité
Règle : Toute mutation de données métier (score, élimination, décision) est journalisée de manière immutable avec horodatage et identifiant utilisateur.
Test : DELETE et UPDATE sur les tables de traçabilité sont interdits au niveau SQL. Seul INSERT est autorisé sur audit_log, score_history, elimination_log.
________________________________________
INV-7 — ERP-agnostique
Règle : Le DMS ne dépend d’aucun ERP. Il expose ses données via API REST et exports fichiers.
Test : Aucune dépendance d’import vers un ERP tiers dans le code source.
________________________________________
INV-8 — Survivabilité & lisibilité
Règle : Le code, la base de données et la documentation doivent être compréhensibles par un ingénieur senior qui n’a pas participé au développement, dans un délai de 48h.
Test : README à jour, schéma de base documenté, aucune logique métier dans des fichiers non documentés.
________________________________________
INV-9 — Fidélité au réel & neutralité
Règle : Le système reflète les données fournies sans interprétation, biais, ou modification. Les scores sont calculés, jamais ajustés.
Corrections humaines : Lorsqu’un utilisateur corrige une extraction (OCR fautif, erreur de parsing), la correction est tracée en append-only avec :
•	valeur avant correction,
•	valeur après correction,
•	identifiant utilisateur,
•	timestamp,
•	motif (champ libre).
La donnée originale n’est jamais supprimée.
Test : Score calculé = résultat de la formule appliquée aux données extraites. Aucun coefficient d’ajustement non déclaré.
Test additionnel : toute correction humaine génère une entrée dans extraction_corrections avec before/after.
________________________________________
§5 — STACK TECHNIQUE CANONIQUE
§5.1 — Backend & Data
Composant	Choix	Justification
Langage	Python 3.11+ (minimum 3.11, compatible 3.12)	Écosystème data/ML, performance suffisante
Framework API	FastAPI	Async, validation Pydantic, OpenAPI natif
Base de données	PostgreSQL 15+	Source unique de vérité, JSONB, full-text search
Migrations	Alembic	SQL brut uniquement — pas d’autogenerate
Accès DB	SQL paramétré via helpers synchrones	Contrôle total, pas de magie ORM
Cache	Redis (optionnel V3)	Fuzzy matching cache, sessions
Qualification Redis :
Redis est un cache non-autoritaire et reconstructible. PostgreSQL reste l’unique source de vérité.
Il est interdit de stocker dans Redis :
•	des entités métier (scores, décisions, éliminations),
•	des données d’audit ou de traçabilité,
•	toute donnée dont la perte nécessiterait une reconstruction impossible sans Redis.
En cas de perte totale du cache Redis, le système doit continuer à fonctionner (performances dégradées acceptables).
Interdictions techniques :
•	❌ Aucun ORM (SQLAlchemy Core autorisé, SQLAlchemy ORM interdit)
•	❌ Aucune base secondaire (pas de MongoDB, SQLite, etc.)
•	❌ Aucune migration autogénérée
________________________________________
§5.2 — Extraction & Génération
Composant	Choix	Rôle
OCR primaire	Azure Document Intelligence	Extraction texte scans/PDF
OCR fallback	Tesseract	Fallback si Azure indisponible
Génération Excel	openpyxl	CBA avec formules, onglets, styles
Génération Word	python-docx	PV avec placeholders remplis
Parsing PDF	pdfplumber / PyMuPDF	Extraction texte PDF natifs
________________________________________
§5.3 — DevOps & Déploiement
Composant	Choix
Repository	GitHub (mono-repo)
CI	GitHub Actions — tests, coverage gate, linting
CD	Railway (Nixpacks)
Conteneurisation	Docker + docker-compose (dev & staging)
Healthcheck	GET /api/health — vérifie DB, migrations, disk
________________________________________
§5.4 — Sécurité
Composant	Choix
Authentification	JWT (access + refresh tokens)
Autorisation	RBAC — 5 rôles (admin, manager, buyer, viewer, auditor)
Audit	Table audit_log — append-only, log_action()
Rate limiting	Par user et par endpoint
Upload	Validation MIME réelle (magic bytes), taille max 50MB, extensions whitelist
Secrets	Variables d’environnement, jamais en dur
CORS	Domaine production uniquement
________________________________________
§6 — MODÈLE DE DONNÉES CANONIQUE
§6.1 — Entité d’entrée : Documents
La brique d’entrée du DMS est l’entité documents, qui formalise le passage entre “fichier uploadé” et “données exploitables”.
┌──────────────────┐
│    documents     │
│                  │
│ id               │
│ case_id (FK)     │
│ kind (enum)      │  ← dao | offer | annex | market_survey | other
│ filename         │
│ storage_uri      │
│ sha256           │  ← intégrité vérifiable
│ mime_type        │  ← validé par magic bytes
│ size_bytes       │
│ page_count       │
│ extraction_status│  ← pending | processing | done | failed
│ created_at       │
│ created_by (FK)  │
└──────────────────┘
         │
         ▼
┌──────────────────────┐
│     extractions      │
│                      │
│ id                   │
│ document_id (FK)     │
│ page_number          │
│ raw_text             │
│ structured_data      │  ← JSONB
│ extraction_method    │  ← azure | tesseract | native_pdf | manual
│ confidence_score     │
│ extracted_at         │
└──────────────────────┘
         │
         ▼
┌──────────────────────────┐
│  extraction_corrections  │
│                          │
│ id                       │
│ extraction_id (FK)       │
│ field_path               │
│ value_before             │
│ value_after              │
│ reason                   │
│ corrected_by (FK)        │
│ corrected_at             │
└──────────────────────────┘
________________________________________
§6.2 — Entités fondamentales
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│    cases     │────→│   suppliers  │────→│    offers     │
│             │     │              │     │              │
│ id          │     │ id           │     │ id           │
│ reference   │     │ name_canon   │     │ case_id (FK) │
│ type (enum) │     │ aliases[]    │     │ supplier_id  │
│ status      │     │ tin          │     │ items[]      │
│ created_at  │     │ history{}    │     │ total_price  │
│ created_by  │     └──────────────┘     │ currency     │
└─────────────┘                          │ submitted_at │
       │                                 └──────────────┘
       │                                        │
       ▼                                        ▼
┌──────────────┐                    ┌──────────────────┐
│   criteria   │                    │  supplier_scores │
│              │                    │                  │
│ id           │                    │ id               │
│ case_id (FK) │                    │ case_id (FK)     │
│ name         │                    │ supplier_id (FK) │
│ type (enum)  │                    │ commercial_score │
│ weight       │                    │ capacity_score   │
│ formula      │                    │ sustain_score    │
└──────────────┘                    │ essential_score  │
                                    │ total_score      │
                                    │ rank             │
                                    │ calculated_at    │
                                    └──────────────────┘
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │supplier_eliminations│
                                │                     │
                                │ id                  │
                                │ case_id (FK)        │
                                │ supplier_id (FK)    │
                                │ reason              │
                                │ rule_ref            │
                                │ eliminated_at       │
                                └─────────────────────┘
________________________________________
§6.3 — Entités Market Signal (Couche B)
┌──────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│   mercurials     │   │ decision_history  │   │ market_surveys   │
│                  │   │                   │   │                  │
│ id               │   │ id                │   │ id               │
│ item_code        │   │ case_id (FK)      │   │ case_id (FK)     │
│ item_name        │   │ item_id (FK)      │   │ item_id (FK)     │
│ unit             │   │ supplier_id (FK)  │   │ supplier_name    │
│ zone             │   │ price_paid        │   │ price_quoted     │
│ year             │   │ quantity          │   │ date_surveyed    │
│ price_min        │   │ decision_date     │   │ location         │
│ price_avg        │   │ zone              │   │ surveyor         │
│ price_max        │   └───────────────────┘   └──────────────────┘
│ group_code       │
│ source           │
└──────────────────┘

┌──────────────────────┐
│procurement_dictionary│
│                      │
│ id                   │
│ item_name_canonical  │
│ aliases[]            │
│ unit_canonical       │
│ unit_aliases[]       │
│ category_code        │
│ mercuriale_ref{}     │
│ procurement_type     │
│ tags[]               │
└──────────────────────┘
________________________________________
§6.4 — Tables de traçabilité (append-only)
audit_log                → user_id, action, entity, entity_id, payload, timestamp
score_history            → case_id, supplier_id, scores{}, calculated_at, version
elimination_log          → case_id, supplier_id, reason, rule_ref, timestamp, by_user
extraction_corrections   → extraction_id, field_path, value_before, value_after,
                           reason, corrected_by, corrected_at
Contraintes SQL obligatoires :
•	REVOKE DELETE, UPDATE ON audit_log, score_history, elimination_log, extraction_corrections FROM app_user;
•	Seul INSERT est autorisé pour ces tables.
________________________________________
§7 — CONTRAINTES DE PERFORMANCE
Toutes les contraintes ci-dessous sont des SLA internes.
Toute régression au-delà des seuils définis bloque le merge en CI.
§7.1 — Classe A — Documents natifs (PDF texte, Excel, Word)
Métrique	Cible	Mesure
Pipeline DAO → CBA complet	< 60 secondes	Timer end-to-end en CI
Upload + extraction 1 document	< 15 secondes	Timer en CI
Génération Excel CBA	< 10 secondes	Timer en CI
Génération Word PV	< 5 secondes	Timer en CI
§7.2 — Classe B — Scans OCR
Métrique	Cible	Mesure
Upload + mise en queue	< 5 secondes	Timer en CI
Extraction OCR (asynchrone)	Budget séparé, progress bar, statut	Monitoring
L’OCR ne bloque pas l’application	Queue + callback	Test d’intégration
§7.3 — Commun aux deux classes
Métrique	Cible	Mesure
Query Market Signal (1 item)	< 200 ms	Benchmark en CI
Fuzzy match dictionnaire	< 100 ms	Benchmark en CI
Charge simultanée	10 DAO concurrents sans dégradation > 2×	Test de charge
Disponibilité	99.5% (hors maintenance planifiée)	Monitoring
Cold start Railway	< 30 secondes	Healthcheck
________________________________________
§8 — POSITIONNEMENT ERP & INTÉGRATION
§8.1 — Principe d’indépendance
Le DMS est ERP-agnostique par design :
•	Il ne dépend d’aucun ERP pour fonctionner.
•	Il ne remplace pas un ERP.
•	Il occupe un espace fonctionnel que les ERP ne couvrent pas : la structuration de la décision d’achat.
§8.2 — Formats d’intégration
Type	Format	Usage
Export CBA	Excel (.xlsx) avec formules et mise en forme	Comité d’évaluation, archivage
Export PV	Word (.docx) pré-rempli	Procès-verbal officiel
API REST	JSON via FastAPI	Intégration avec ERP, BI, systèmes tiers
Export données	CSV, JSON	Migration, reporting, audit externe
§8.3 — Positionnement
$$\text{DMS structure la décision} \quad | \quad \text{ERP enregistre l’exécution}$$
________________________________________
§9 — GOUVERNANCE & CLAUSES JURIDIQUES
§9.1 — Propriété intellectuelle
Le DMS, son code source, son architecture, sa Constitution et sa documentation sont la propriété exclusive d’Abdoulaye Ousmane et de toute entité légale qu’il désignera.
§9.2 — Confidentialité des données
Les données ingérées dans le DMS (documents, offres, prix, fournisseurs) sont la propriété de l’organisation utilisatrice. Le DMS :
•	Ne partage pas les données entre organisations.
•	Ne les utilise pas à des fins d’entraînement ou de profilage.
•	Garantit leur suppression sur demande de l’organisation propriétaire.
§9.3 — Réversibilité
Toute organisation utilisatrice peut à tout moment :
•	Exporter l’intégralité de ses données (cas, offres, scores, historique, Market Surveys) en format ouvert (CSV/JSON).
•	Résilier son usage sans perte de données.
§9.4 — Autorité interprétative
En cas de litige d’interprétation de cette Constitution, l’auteur et fondateur (Abdoulaye Ousmane) est l’autorité finale.
Toute interprétation divergente par un tiers (développeur, partenaire, auditeur) est soumise à validation explicite du fondateur.
§9.5 — Clause de freeze
Cette Constitution V3.3.1 est gelée par décision du fondateur.
Toute évolution future :
1.	Doit démontrer son alignement avec les invariants (§4).
2.	Doit être documentée comme amendement versionné.
3.	Nécessite l’approbation explicite du fondateur.
4.	N’invalide pas rétroactivement les décisions prises sous la version précédente.
________________________________________
§10 — FORMULE FONDATRICE
Le Decision Memory System est un système à deux couches —
un moteur d’exécution (Couche A) et une mémoire intelligente (Couche B) —
articulé autour d’un dictionnaire procurement et d’un Market Signal à trois sources de vérité,
conçu pour automatiser, accélérer et structurer tous les processus d’achat,
au service des États, des organisations et des entreprises,
sans jamais décider à leur place.
________________________________________
ANNEXE A — Table de concordance Invariants ↔ Tests CI
Invariant	Test CI correspondant	Type
INV-1	test_pipeline_under_60s	Performance
INV-2	test_couche_a_standalone (Couche B désactivée → CBA valide)	Intégration
INV-3	test_scores_independent_of_couche_b	Unitaire
INV-4	test_no_offline_components (scan statique : pas de sync offline, pas de stockage local durable, pas de queue offline)	Statique
INV-5	GitHub Actions gate — merge bloqué si rouge	CI
INV-6	test_audit_log_append_only (tentative DELETE → erreur SQL)	Sécurité
INV-7	test_no_erp_dependency (scan imports)	Statique
INV-8	test_readme_exists, test_schema_documented	Documentation
INV-9	test_score_equals_formula_output (pas de coefficient caché) + test_extraction_corrections_append_only (before/after exigé)	Unitaire / Sécurité
________________________________________
ANNEXE B — Changelog
Version	Date	Changements
V1.0	2024-Q3	Vision initiale, Couche A uniquement
V2.0	2024-Q4	Ajout Couche B, Market Survey
V3.0	2025-01	Stack technique, invariants
V3.2	2025-02	Portée universelle (DAO/RFQ/RFP), ERP-agnostique
V3.3	2025-02-15	Dictionnaire procurement, Market Signal 3 sources, modèle de données, contraintes performance, clauses juridiques, tests de conformité invariants — VERSION BLINDÉE
V3.3.1	2026-02-15	Patch freeze : SLA dual-class, INV-4/INV-9 corrigés, Redis qualifié non-autoritaire, entité documents/extractions/extraction_corrections ajoutées, date corrigée, mode “zéro saisie manuelle répétitive”, Python 3.11+ précisé — VERSION FREEZE CANONIQUE
________________________________________
🔐 STATUT FINAL
Ce document CONSTITUTION DMS V3.3.1 est désormais :
✅ OFFICIEL
✅ FROZEN
✅ RÉFÉRENCE CANONIQUE UNIQUE
✅ OPPOSABLE aux agents IA, au code, aux PR, aux choix techniques, et aux futures extensions

