📘 CONSTITUTION DU DECISION MEMORY SYSTEM — V1.4
Version : 1.4
Statut : FROZEN (évolutive sous invariants uniquement)
Date : 7 février 2026
Auteur fondateur : Abdoulaye Ousmane
Tech Lead : Architecture Cognitive Procurement
Cible V1 : Organisations, États, Mines, Entreprises privées
Mode : Online – Haute performance – Utilisateurs experts

§ 0 — PRÉAMBULE (Non négociable)
Le Decision Memory System est un système de structuration cognitive d'un processus compétitif d'achat à la fois (DAO, RFQ ou RFP).

Il existe pour :
Réduire radicalement la charge cognitive des décideurs experts

Transformer un volume documentaire complexe en artefacts décisionnels prêts à l'emploi

Préserver une mémoire décisionnelle exploitable sans effort supplémentaire

Ouvrir un chemin clair vers la décision humaine, sans jamais s'y substituer

Éliminer 90% du travail cognitif répétitif (extraction, structuration, pré-classement, pré-remplissage)

Il n'existe pas pour :
Optimiser ou améliorer la "qualité intrinsèque" des décisions

Recommander, classer ou scorer des fournisseurs

Juger des individus ou des équipes

Remplacer le jugement humain

Servir d'outil de contrôle managérial ou d'audit accusatoire

Gérer les contrats ou le suivi d'exécution post-attribution

Mandat unique :
Restaurer et amplifier la capacité de décision humaine sous contrainte informationnelle, en créant une version consolidée unique par processus qui remplace les tableaux Excel artisanaux et les copier-coller manuels.

§ 1 — IDENTITÉ DU SYSTÈME
1.1 Ce que le système EST
Un assistant cognitif structuré en deux couches strictement séparées :

🔹 Couche A — L'ouvrier cognitif (cœur du système)
Fonction : Traiter un processus compétitif du début (DAO/RFQ/RFP) jusqu'à la décision d'attribution.

Responsabilités :

Ingestion : DAO/RFQ/RFP + offres associées (PDF, Excel, Word)

Extraction automatique :

Règles d'évaluation

Critères techniques, financiers, administratifs

Pondérations

Lots (si multi-lots)

Seuils d'élimination

Pré-classement :

Par soumissionnaire

Par lot

Par date/heure/mode de dépôt (horodatage strict)

Structuration : Tableau d'analyse consolidé unique (lisible, classé, énuméré)

Pré-remplissage : Intégration automatique dans les outils officiels (CBA, PV)

Export : CBA officiel onglet par onglet + PV horodaté en un clic

Validation : Champs humains restent vides (visite fournisseur, évaluation échantillon, appréciation qualitative)

Principe fondamental : La Couche A crée le dossier d'analyse unique qui remplace tous les tableaux Excel artisanaux.

Structure utilisateur : 3 écrans maximum

Écran 1 : Ingestion (upload + validation extraction)

Écran 2 : Structuration (tableau consolidé + corrections)

Écran 3 : Décision & Exports (CBA + PV)

👉 Rôle : Faire 90% du travail cognitif répétitif.

🔹 Couche B — Le collègue expérimenté (mémoire)
Fonction : Capitaliser la connaissance marché et décisionnelle sans effort humain supplémentaire.

Responsabilités :

Capitaliser automatiquement les décisions passées (prix, délais, zones, catégories)

Fournir du contexte historique factuel sur requête

Alimenter une intelligence marché multi-sources

Répondre à des questions factuelles, jamais prescriptives

Principe fondamental : La mémoire est un sous-produit automatique de l'activité réelle, jamais une obligation.

Manifestation utilisateur : Réponses factuelles uniquement (historique prix/délais/volumes/typologie fournisseurs) sur requête, jamais sous forme de recommandations ou de notes.

👉 Rôle : Se souvenir, pas décider.

Règle de séparation absolue : Aucune donnée de la Couche B n'altère les calculs ni la structure de la Couche A.

1.2 Ce que le système N'EST PAS
❌ Un moteur de décision
❌ Un outil de scoring ou ranking fournisseur
❌ Un système de conformité / audit
❌ Un ERP ou système de record
❌ Un dashboard HQ
❌ Un outil de contrôle hiérarchique
❌ Un système de contract management
❌ Un outil de suivi d'exécution post-attribution

§ 2 — INVARIANTS FONDATEURS (Intouchables)
Invariant 1 — Réduction radicale de la charge cognitive
Toute fonctionnalité doit :

Réduire l'effort mental

Être plus rapide que la méthode existante

Produire un bénéfice visible immédiatement

👉 Test : Si une fonctionnalité fait hésiter ou réfléchir à "comment l'utiliser", elle est rejetée.

Invariant 2 — Primauté absolue de la Couche A (version expert)
La Couche A est prioritaire sur toute autre couche

Conçue pour utilisateurs experts du procurement

Supérieure à Excel en vitesse et structuration

Aucune configuration requise

Structure 3 écrans stricte : Ingestion, Structuration, Décision/Exports

👉 Test : Aucune sophistication mémoire ne doit ralentir la Couche A. Aucune donnée de la Couche B ne modifie les calculs de la Couche A.

Invariant 3 — La mémoire est un sous-produit, jamais une obligation
La mémoire se nourrit :

Automatiquement des processus réels (DAO/RFQ/RFP)

Optionnellement de sources externes structurées (mercurials, enquêtes)

👉 Test : Aucune action "pour documenter" n'est imposée à l'utilisateur.

Invariant 4 — Le système n'est pas décisionnaire
Le système :

Ne recommande pas

Ne classe pas (sauf pré-classement factuel chronologique)

Ne juge pas

Ne décide pas

Il :

Structure

Rappelle des faits

Expose des précédents

👉 Test : La décision appartient toujours à l'humain. Les décisions restent discutées en comité comme avant ; le système réduit le temps de préparation, pas le temps de débat.

Invariant 5 — Traçabilité sans accusation
Données factuelles uniquement

Langage neutre

Analyse centrée sur la décision, jamais sur la personne

Horodatage de toute modification (qui, quand, quoi)

👉 Test : Peut-on utiliser les données du système contre un individu ? Si oui, la fonctionnalité est rejetée.

Invariant 6 — Conception online-first haute performance (V1)
La V1 est conçue pour :

Environnement online stable

Utilisateurs experts (organisations, États, mines, entreprises privées)

Traitement rapide et fluide

Documents structurés (PDF, Excel, Word)

Hors scope V1 :

Contraintes offline

Environnements dégradés (terrain difficile)

Photos WhatsApp

Dévis SMS

Extensions contextes difficiles (Sahel, etc.)

👉 Test : Toute contrainte offline, terrain ou dégradée est hors scope V1.

Invariant 6 bis — Supériorité cognitive sur Excel
À usage égal, le système doit être plus rapide qu'Excel, y compris pour un expert.

👉 Test : Si Excel est plus rapide, la fonctionnalité est rejetée.

Invariant 7 — ERP-agnostique
Le système :

Ne dépend d'aucun ERP

Fonctionne par documents, exports, APIs simples

Complète sans remplacer

Invariant 8 — Append-only
Aucune suppression

Aucune édition rétroactive

Correction par ajout horodaté uniquement

Invariant 9 — Technologie subordonnée à la vision
IA, OCR, LLM :

Activables

Désactivables

Jamais structurants

👉 Test : Le système doit fonctionner sans IA/LLM si nécessaire.

Invariant 10 — Survivabilité
Le système doit survivre à :

Son créateur

Toute rotation RH

Toute restructuration

👉 Test : Documentation suffisante pour transmission complète.

Invariant 11 — Fidélité au réel
Le système enregistre :

Ce qui s'est passé

Pas ce qui aurait dû se passer

§ 3 — SCOPE V1 MVP (Strict)
3.1 Périmètre MVP
Processus :

Un seul processus par cas (DAO ou RFQ ou RFP)

Trois écrans max pour l'usage courant (Ingestion, Structuration, Décision/Exports)

Aucun paramétrage utilisateur

Formats supportés :

Documents : PDF, Excel .xlsx, Word .docx

Processus compétitifs formels uniquement (DAO/RFQ/RFP structurés)

Export vers outils officiels :

CBA (Comparative Bid Analysis) Save the Children

PV (Procès-Verbal) standard humanitaire/État

Périmètre décisionnel :

MVP s'arrête à la décision d'attribution

Hors scope : contract management, suivi d'exécution, gestion des avenants

3.2 Interdictions explicites V1
❌ Recommandations automatiques
❌ Scoring global fournisseur
❌ Dashboards HQ
❌ Optimisation algorithmique
❌ Multi-workflows complexes
❌ Mode offline
❌ Photos/WhatsApp/SMS
❌ App Android (post-MVP)
❌ Chatbot LLM (post-MVP)

§ 4 — COUCHE A : L'OUVRIER COGNITIF (Cœur produit)
4.1 Fonctions centrales
1. Ingestion DAO/RFQ/RFP
Entrées :

Document principal (DAO/RFQ/RFP) : PDF ou Word

Annexes (cahier des charges, TDR) : PDF ou Word

Offres soumissionnaires : PDF ou Excel

Extraction automatique :

Critères d'évaluation (techniques, financiers, administratifs)

Pondérations par critère

Lots (si multi-lots)

Règles d'élimination (seuils, documents obligatoires)

Profil d'évaluation (détection automatique : fournitures, travaux, services, santé)

Validation humaine :

Confirmation extraction en 30 secondes max

Correction manuelle si extraction < 90% confiance

Fallback manuel rapide (< 2 minutes)

2. Pré-classement des offres
Données capturées :

Nom soumissionnaire

Date/heure dépôt (horodatage strict)

Mode de dépôt (physique, email, plateforme)

Lot(s) concerné(s)

Documents soumis (liste)

Pré-classement automatique :

Par lot

Par ordre chronologique de dépôt

Par conformité administrative préliminaire (documents manquants flaggés)

3. Tableau d'analyse consolidé
Structure :

Soumissionnaire	Lot	Date/heure dépôt	Conformité admin	Critères techniques	Critères financiers	Note finale	Classement
Champs pré-remplis automatiquement :

Identité soumissionnaire

Horodatage dépôt

Conformité administrative (documents reçus vs requis)

Extraction données techniques (specs, expérience, capacité)

Extraction données financières (prix unitaires, coût total, délais)

Calcul notes selon pondérations

Champs vides (humains uniquement) :

Visite fournisseur (oui/non, date, observations)

Évaluation échantillon (conformité, qualité, observations)

Appréciation qualitative comité

Négociation (si applicable)

4. Export CBA officiel (en un clic)
Processus :

Clic "Exporter vers CBA"

L'outil remplit automatiquement le template CBA onglet par onglet

Champs humains restent vides

Utilisateur revoit et corrige

Clic "Valider" → système enregistre "CBA terminé" (horodaté)

Possibilité de revenir corriger (horodaté aussi)

Formats export :

Excel .xlsx (CBA éditable)

PDF horodaté (CBA final)

5. Génération PV officielle horodatée (en un clic)
Contenu automatique :

Date, heure, lieu ouverture

Liste soumissionnaires + heure dépôt

Liste documents soumis par offrant

Résultat évaluation (extraction depuis CBA validé)

Classement final

Horodatage génération

Champs vides (humains) :

Membres comité (noms, qualités)

Signatures

Observations particulières

Formats export :

Word .docx (PV éditable)

PDF horodaté et signé numériquement (PV final)

4.2 Règle fondamentale Couche A
👉 Champs humains (visite, échantillon, appréciation) restent vides.
👉 Cela empêche le système de dériver vers du pseudo-scoring implicite.

§ 5 — COUCHE B : MÉMOIRE & MARKET INTELLIGENCE
5.1 Base MARKET_INTEL
Structure de données :

Champ	Type	Description
id	UUID	Identifiant unique
source_type	Enum	procurement / mercurial / meal_survey
fournisseur	String	Nom fournisseur (si applicable)
categorie	String	Catégorie produit/service
item	String	Description item spécifique
zone	String	Zone géographique
prix	Float	Prix (avec unité)
delais	Integer	Délais livraison (jours)
date	Date	Date de la donnée
source_detail	String	Détail source (numéro DAO, nom mercurial, équipe MEAL)
lien_cas	String	Lien vers processus Couche A (si applicable)
timestamp	Timestamp	Horodatage insertion
5.2 Sources de vérité autorisées
Source 1 : Procurement réel (automatique)
Alimentation : Automatique après clôture d'un processus Couche A

Données capturées :

Fournisseur retenu

Catégorie

Items + prix unitaires

Zone

Délais

Date processus

Lien vers dossier complet Couche A

Principe : Zéro action utilisateur.

Source 2 : Mercurials / Référentiels prix (manuelle)
Alimentation : Import CSV ou saisie par procurement manager

Format CSV attendu :

text
categorie,item,zone,prix,unite,date,source
Fournitures,Ciment 50kg,Bamako,6500,FCFA/sac,2026-02-01,Mercurial BTP Mali
Principe : Gestionnaire de l'outil ou procurement peut importer sans dépendre d'un processus actif.

Source 3 : Enquêtes MEAL / Programmes (utilisateurs terrain)
Alimentation : App Android ultra-légère (POST-MVP V1.1)

Interface utilisateur :

Champs : Item, Prix, Zone, Marché (optionnel)

Clic "Enregistrer" → base s'alimente

Aucun accès aux autres fonctions système

Anonymisation : L'outil ne cite jamais le nom de l'utilisateur, seulement "source MEAL" + date.

Principe : Fenêtre dédiée, utilisateurs limités aux fonctions MEAL, pas plus.

5.3 Périmètre MVP (V1.0)
Sources actives en MVP :

✅ Source 1 (automatique) : Procurement réel → alimentation automatique

✅ Source 2 (import CSV) : Mercurials → import manuel

Post-MVP (V1.1+) :
3. ❌ Source 3 (app Android) : Enquêtes MEAL/Programmes
4. ❌ Chatbot LLM : Recherche en langage naturel

Interface Couche B MVP :

Recherche structurée simple (filtres : catégorie, zone, plage de dates)

Affichage résultats avec source identifiée : "Prix ciment 50kg Bamako : 6500 FCFA (source MEAL, 3 fév 2026)"

Export CSV des résultats

5.4 Règles de séparation Couche A / Couche B
👉 Aucune donnée de la Couche B n'altère les calculs de la Couche A.
👉 Aucune fusion aveugle des sources : chaque donnée reste typée et sourcée.
👉 La Couche B se manifeste uniquement sur requête utilisateur, jamais de manière proactive.

§ 6 — ALERTES (Consultatives uniquement)
6.1 Principe général
Alertes factuelles uniquement

Jamais bloquantes

Désactivables avec justification humaine

6.2 Types d'alertes autorisées (exemples)
"Prix proposé 40% inférieur à la médiane des 6 derniers mois (source Couche B)" → flag pour vérification humaine

"Document manquant : agrément technique" → rappel conformité administrative

"Délai proposé 50% supérieur à la moyenne marché" → information contextuelle

6.3 Test de dérive obligatoire
Toute nouvelle alerte passe par le Test de dérive § 9 :

Peut-on l'utiliser contre un individu ?

Réduit-elle la liberté décisionnelle ?

Centralise-t-elle le pouvoir cognitif ?

👉 Oui à une seule → alerte rejetée.

§ 7 — ÉVOLUTION LLM (Post-validation MVP)
7.1 LLM autorisé uniquement pour
Recherche en langage naturel dans Couche B

Résumés factuels

Assistance rédactionnelle (PV, notes)

7.2 LLM interdit pour
Recommandation

Scoring

Prédiction

Décision

7.3 Chatbot LLM (V1.1 post-MVP)
Use case principal : Solution au turnover

Exemple d'interaction :

Utilisateur : "Comment on évalue un marché de fournitures scolaires ?"

Chatbot : "Voici les 3 derniers DAO fournitures scolaires traités : critères utilisés (30% technique, 50% financier, 20% admin), pondérations, prix moyens (cahiers 250 FCFA/unité, stylos 100 FCFA), délais moyens (15 jours)."

👉 Le chatbot rappelle des faits, ne recommande jamais.

§ 8 — SOUVERAINETÉ DES DONNÉES
Données locales par défaut

Aucun export HQ automatique

Agrégation uniquement sur accord formel écrit

Option self-hosted obligatoire pour États/mines/organisations sensibles

§ 9 — TEST DE DÉRIVE (Garde-fou éthique)
Avant toute évolution fonctionnelle :

Peut-on l'utiliser contre un individu ?

Réduit-elle la liberté décisionnelle ?

Centralise-t-elle le pouvoir cognitif ?

👉 Oui à une seule → rejet immédiat.

§ 10 — CRITÈRES DE SUCCÈS V1 MVP
10.1 Adoption
80%+ des utilisateurs pilotes utilisent le système sans rappel après 2 semaines

Zéro formation : utilisateur expert autonome en < 15 minutes

10.2 Performance
50%+ réduction du temps de préparation (ingestion → export CBA) vs Excel

Plus rapide qu'Excel à usage égal

10.3 Fiabilité
95%+ des champs critiques (critères, pondérations, lots) extraits correctement

Fallback manuel rapide (< 2 minutes) si extraction < 90% confiance

10.4 Charge cognitive
40%+ réduction de la charge cognitive (score NASA-TLX ou équivalent)

Fatigue mentale réduite

10.5 Conformité
Export CBA/PV acceptés sans modification par compliance

Traçabilité complète (horodatage, append-only)

10.6 ROI perçu
80%+ des early adopters disent "je ne reviendrais pas à Excel"

§ 11 — STATUT CONSTITUTIONNEL
Version : 1.4
Statut : FROZEN
Référence ultime : Ce document est la référence ultime du projet

"This system protects organizations from forgetting, not from their people."

§ 12 — MOTEUR DE RÈGLES MÉTIER (Rules Engine)
12.1 Profils d'évaluation pré-encodés
L'outil contient des profils d'évaluation qui s'activent automatiquement selon le type de marché détecté dans le DAO/RFQ/RFP.

Profils MVP (à encoder après réception des manuels) :

Profil	Critères techniques	Critères financiers	Critères administratifs	Pondération défaut
Fournitures courantes	Conformité specs + échantillon	Prix unitaire + coût total	Agrément + documents légaux	30% / 50% / 20%
Travaux/construction	Capacité technique + expérience	Prix + délais	Agrément BTP + assurance	40% / 40% / 20%
Services consulting	Expérience + CV équipe	Prix journalier + coût total	Documents légaux	50% / 30% / 20%
Médicaments/santé	Conformité réglementaire + certification	Prix + délais	Agrément sanitaire + traçabilité	40% / 40% / 20%
Note : Ces profils seront affinés selon les manuels Save the Children, UN standards, et règlementation État Mali.

12.2 Règles d'élimination automatique
L'outil applique automatiquement les critères d'élimination avant l'évaluation :

Éliminations strictes (flags rouges) :

Document obligatoire manquant (liste définie dans DAO/RFQ)

Soumission hors délai (horodatage)

Non-conformité technique majeure (spécifications techniques non respectées)

Alertes pour vérification humaine (flags orange) :

Prix anormalement bas (< 50% de la médiane, source Couche B si disponible)

Délais anormalement courts ou longs (± 50% de la médiane)

Expérience déclarée non vérifiable

12.3 Lexique canonique procurement
L'outil comprend nativement les termes métier suivants :

Terme	Définition opérationnelle
DAO	Dossier d'Appel d'Offres = processus formel marché public/humanitaire (> seuil formel)
RFQ	Request for Quotation = demande de prix simple (< seuil formel, 3 devis min)
RFP	Request for Proposal = appel à propositions techniques + financières (services intellectuels)
Lot	Subdivision d'un marché (géographique, technique, ou temporelle)
CBA	Comparative Bid Analysis = tableau comparatif officiel (Save the Children, UN)
PV	Procès-Verbal = document d'ouverture et d'évaluation horodaté
TDR	Termes de Référence = cahier des charges services/consulting
Cahier des charges	Spécifications techniques fournitures/travaux
Soumissionnaire	Fournisseur ayant déposé une offre
Attributaire	Fournisseur retenu après évaluation
Comité d'évaluation	Groupe d'experts évaluant les offres (3-5 personnes min selon procédures)
12.4 Grammaire d'évaluation
L'outil sait interpréter automatiquement les structures de pondération suivantes :

Critères binaires (Go/No-Go)
Conforme / Non conforme → éliminatoire

Exemples : agrément technique, documents légaux obligatoires, délai maximum

Critères scorés (notation)
Échelle 0-100 avec coefficients

Exemples : expérience (0-20 points), capacité technique (0-30 points)

Critères combinés (notes composites)
Note technique (ex: 70%) + note financière (ex: 30%) → note finale

Formule : Note finale = (Note technique × 0.7) + (Note financière × 0.3)

Règles de seuil (notes minimales)
Note technique minimum (ex: 70/100) pour être éligible à l'évaluation financière

Si note technique < seuil → élimination automatique, même si prix le plus bas

Évaluation financière (formules courantes)
Méthode 1 : Prix le plus bas = 100 points

text
Note financière = (Prix le plus bas / Prix offre) × 100
Méthode 2 : Moyenne pondérée

text
Note financière = 100 - ((Prix offre - Prix le plus bas) / Prix le plus bas) × 100
👉 L'outil détecte la méthode utilisée dans le DAO/RFQ et applique la formule correspondante.

12.5 Détection automatique du profil
Processus :

Extraction du titre + objet marché (DAO/RFQ/RFP)

Analyse des mots-clés (fournitures, travaux, services, médicaments, etc.)

Détection critères d'évaluation présents

Attribution profil le plus proche

Si incertain : L'outil demande confirmation humaine (1 clic pour sélectionner le profil).

Fallback : Si aucun profil ne correspond, l'outil utilise les critères extraits du DAO/RFQ sans appliquer de profil pré-encodé.

12.6 Évolutivité des règles
Principe : Les règles métier, lexique et grammaire sont configurables sans toucher au code.

Implémentation technique :

Fichiers JSON ou YAML (règles, profils, lexique)

Interface admin simple pour ajouter/modifier profils (post-MVP)

Versioning des règles (append-only)

👉 Permet l'adaptation à de nouvelles organisations (UN, Banque Mondiale, etc.) sans refonte technique.

§ 13 — MAPPING TEMPLATES OFFICIELS
13.1 Template CBA (Comparative Bid Analysis)
Note : Le mapping exact sera documenté après réception du template CBA réel Save the Children.

Structure générique attendue :

Onglet	Contenu	Source Couche A	Champs humains (vides)
1. Informations générales	Titre marché, date ouverture, comité	Extraction DAO + metadata processus	Membres comité (noms, signatures)
2. Liste soumissionnaires	Nom, date/heure dépôt, lot(s)	Pré-classement Couche A	Conformité administrative (validation)
3. Analyse technique	Critères techniques + scoring	Extraction cahier charges + offres	Visite fournisseur, évaluation échantillon
4. Analyse financière	Prix unitaires, coût total, délais	Extraction offres financières	Négociation (si applicable)
5. Synthèse & recommandation	Tableau récapitulatif notes + classement	Calcul automatique Couche A	Appréciation qualitative comité
Principe de mapping : Chaque cellule du CBA est mappée à un champ de la Couche A.

13.2 Génération PV officiel
Contenu automatique :

En-tête : Organisation, titre marché, référence DAO/RFQ/RFP

Date, heure, lieu ouverture

Liste soumissionnaires + heure dépôt (ordre chronologique)

Liste documents soumis par offrant (check-list)

Résultat évaluation (extraction depuis CBA validé)

Classement final (1er, 2ème, 3ème)

Fournisseur retenu + montant

Horodatage génération PV

Champs vides (humains) :

Membres comité (noms, qualités, signatures)

Observations particulières du comité

Réserves ou conditions d'attribution

Formats d'export :

Word .docx (éditable)

PDF horodaté et signé numériquement (final)

13.3 Formats d'export supportés
Document	Format éditable	Format final	Signature numérique
CBA	Excel .xlsx	PDF	Non
PV	Word .docx	PDF	Oui (horodatage)
§ 14 — ARCHITECTURE TECHNIQUE MVP (Minimum Viable Architecture)
14.1 Stack recommandé
Backend :

Python (FastAPI ou Django)

PostgreSQL (base append-only, séparation Couche A / Couche B)

Celery (optionnel, traitement asynchrone documents lourds)

Frontend :

React ou Vue.js (3 écrans, zéro configuration)

Design system minimal (Tailwind ou shadcn/ui)

IA/ML (activable, non structurant) :

OCR : Tesseract ou Azure Document Intelligence

LLM (optionnel post-MVP) : OpenAI API ou Anthropic

Déploiement :

Docker + Docker Compose

Option Cloud : AWS/Azure/GCP (région configurable pour souveraineté)

Option Self-hosted : VM cliente (crucial pour États/mines)

14.2 Séparation Couche A / Couche B
Base de données :

Schema couche_a : Processus actifs (DAO/RFQ/RFP en cours)

Schema couche_b : Market intelligence (historique prix/délais/fournisseurs)

APIs internes distinctes :

/api/v1/couche_a/* : Ingestion, extraction, structuration, export

/api/v1/couche_b/* : Recherche mémoire, import mercurials

👉 Zéro dépendance de A vers B.

14.3 Sécurité & souveraineté
Auth robuste (pas de Google OAuth si clients États/mines)

Données stockées localement par défaut

Option self-hosted dès V1

Logs append-only avec anonymisation données sensibles

Encryption at rest + in transit

§ 15 — ROADMAP MVP (12-16 semaines)
Phase 1 : Durcissement technique (3-4 semaines)
Architecture MVA (Minimum Viable Architecture)

Database append-only (PostgreSQL)

Document ingestion pipeline (OCR + fallback manuel)

Export engine (CBA/PV mapping)

Migration Replit → GitHub + Docker

Phase 2 : Core product UX (3-4 semaines)
3 écrans (Ingestion, Structuration, Décision/Exports)

Validation "zéro formation" + "plus rapide qu'Excel"

Prototype utilisable par procurement officers experts

Phase 3 : Couche B opérationnelle (2-3 semaines)
Base MARKET_INTEL production

Sources 1-2 actives (procurement réel + mercurials)

Recherche structurée simple

Phase 4 : Validation terrain (2-3 semaines)
5-10 early adopters (ONG, État, mine/entreprise)

Métriques succès MVP

Build-Measure-Learn (cadence hebdomadaire)

§ 16 — CHECKLIST GO / NO-GO MVP → PRODUIT
✅ 1. Adoption naturelle : 70%+ early adopters utilisent sans relance
✅ 2. Vitesse : 50%+ réduction temps préparation vs Excel
✅ 3. Fiabilité : 95%+ champs critiques extraits correctement
✅ 4. Zéro formation : expert autonome en < 15 min
✅ 5. Export conforme : CBA/PV acceptés sans modification
✅ 6. Couche B non intrusive : aucune plainte "trop de mémoire"
✅ 7. Infrastructure stable : 99%+ uptime sur 4 semaines
✅ 8. Sécurité OK : audit basique passé
✅ 9. Test de dérive : aucune feature ne viole les invariants
✅ 10. ROI perçu : 80%+ disent "je ne reviendrais pas à Excel"

👉 Si < 8/10 validés → rester en MVP et itérer
👉 Si 8-9/10 → go produit avec monitoring renforcé
👉 Si 10/10 → go produit + préparation scale

FIN CONSTITUTION V1.4
**© 2026 — Decision Memory System — Constitution V1.2**

*This system protects organizations from forgetting, not from their people.*
