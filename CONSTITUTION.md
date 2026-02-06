📘 CONSTITUTION DU DECISION MEMORY SYSTEM — V1.2 FINAL
Version: 1.2 (Production-ready)
Statut: FROZEN (évolutive sous invariants uniquement)
Date: 6 février 2026
Auteur fondateur: Abdoulaye Ousmane
Tech Lead: Architecture Sahel-first

§ 0 — PRÉAMBULE (Non négociable)
Ce système est un assistant cognitif intelligent en procurement.

Il existe pour:

réduire radicalement la charge cognitive des décideurs sous pression,

faire émerger une mémoire décisionnelle vivante sans effort supplémentaire,

transformer l'expérience terrain en intelligence de marché actionnable.

Il n'existe pas pour:

améliorer la "qualité intrinsèque" des décisions,

remplacer le jugement humain,

optimiser les résultats procurement,

contrôler ou juger les personnes.

Son seul mandat: restaurer la capacité de décision humaine sous pression opérationnelle.

Ce système part d'une douleur réelle: des comités épuisés avant même d'analyser, 99 offres sur 21 lots, 3 jours d'ouverture manuelle, paperasse qui écrase la réflexion.

§ 1 — IDENTITÉ DU SYSTÈME
1.1 Ce que le système EST
Un assistant intelligent structuré en deux couches complémentaires:

Couche A — L'ouvrier cognitif:

Ingère, classe, extrait, structure les documents procurement (DAO, RFQ, offres).

Pré-remplit les CBA, PV, tableaux d'analyse.

Élimine le secrétariat manuel et la paperasse.

Métaphore: le stagiaire ultra-efficace qui fait tout le travail préparatoire.

Couche B — Le collègue expérimenté:

Mémorise passivement toutes les décisions et contextes.

Répond à des questions factuelles ("Qu'est-ce qui s'est passé dans des cas similaires ?").

Fournit du contexte historique (prix, délais, fournisseurs, incidents).

Nourrit une base de market intelligence dense et vivante.

Métaphore: le senior qui se souvient de tout et te donne le contexte, sans te dire quoi faire.

1.2 Ce que le système N'EST PAS
❌ Un outil de compliance ou d'audit

❌ Un système de détection de fraude

❌ Un moteur de scoring ou ranking fournisseur

❌ Un système d'automatisation de décision

❌ Un ERP ou système de record

❌ Un dashboard de performance HQ

❌ Un outil de contrôle managérial

C'est une couche de support cognitif complémentaire, jamais une autorité institutionnelle.

§ 2 — INVARIANTS FONDATEURS (Intouchables)
Ces invariants définissent l'identité du système. Violer un seul invariant invalide le produit.

Invariant 1 — Réduction radicale de la charge cognitive
Le système ne doit jamais augmenter la charge cognitive des utilisateurs.

Toute action doit coûter moins d'effort que la méthode existante.

Le bénéfice doit être visible dès la première utilisation.

L'usage doit rester possible en situation de fatigue, stress ou urgence.

Mesure de succès: si l'utilisateur hésite, ralentit, ou demande de l'aide → échec.

👉 Si une fonctionnalité augmente la charge cognitive, elle est supprimée.

Invariant 2 — Primauté absolue de la Couche A
La Couche A est prioritaire sur toutes les autres couches.

Utilisable sans formation formelle.

Compréhensible intuitivement.

Fonctionnelle pour: stagiaire, assistant, agent de sécurité, personnel non technique.

👉 Aucune sophistication de la Couche B ne peut dégrader la Couche A.

Invariant 3 — La mémoire est un sous-produit, jamais une obligation
Aucune donnée n'est saisie "pour alimenter la mémoire".

La mémoire émerge de l'usage réel.

Elle ne génère aucune tâche supplémentaire.

👉 Toute fonctionnalité demandant un effort explicite pour "documenter" est interdite.

Invariant 4 — Le système n'est pas décisionnaire
Le système:

n'arbitre pas,

ne juge pas,

ne sanctionne pas,

ne note pas moralement,

ne recommande jamais un fournisseur.

Il:

rappelle des faits,

contextualise,

compare des données historiques,

rend visibles des précédents.

👉 La décision finale appartient toujours aux humains.

Invariant 5 — Traçabilité sans accusation
Les données sont factuelles.

Le langage est neutre.

Aucun score individuel de suspicion.

Aucun mécanisme accusatoire.

L'unité d'analyse est la décision, jamais la personne.

👉 Le système protège l'organisation contre l'oubli, pas contre ses agents.

Invariant 6 — Conception Sahel-first (chaos résilient)
Le système fonctionne dans un environnement marqué par:

turnover élevé,

fatigue cognitive,

documents hétérogènes (Word, PDF, scans, Excel — formats prioritaires V1),

connectivité instable,

pression opérationnelle constante.

Priorité V1: Word, PDF, Excel, scans de qualité acceptable.
Évolution future: photos WhatsApp, images basse résolution.

👉 Si le système ne fonctionne pas dans ce contexte, il est invalide.

Invariant 7 — ERP-agnostique par conception
Le système:

ne dépend d'aucun ERP spécifique (ProSave, SAP, Dynamics, etc.),

se connecte par exports, fichiers, emails, scans, APIs simples,

complète les ERP existants sans les remplacer.

👉 Il doit fonctionner avec ou sans ERP.

Invariant 8 — Online-first (pragmatique), offline-capable (évolutif)
Stratégie V1 (réaliste pour adoption bureau pays):

Architecture online-first pour accélérer le déploiement et l'adoption.

Connectivité internet stable supposée (bureau pays).

Synchronisation temps réel.

Évolution future (post-adoption):

Capacités offline progressives.

Synchronisation différée.

Mode dégradé pour terrain sans connexion.

👉 V1 privilégie l'adoption rapide. Offline vient après validation terrain.

Invariant 9 — Append-only (aucune suppression)
Pas de suppression de données.

Pas d'édition rétroactive.

Uniquement des ajouts horodatés.

👉 On corrige en ajoutant, jamais en effaçant.

Invariant 10 — Évolution technologique subordonnée à la vision
IA, OCR, LLM, automatisation: optionnels.

Retour manuel toujours possible.

Toute technologie peut être désactivée si elle devient un risque.

👉 La technologie sert la vision, jamais l'inverse.

Invariant 11 — Survivabilité absolue
Le système doit survivre à:

son créateur (Abdoulaye Ousmane),

toute personne clé,

toute rotation RH,

toute restructuration organisationnelle,

tout changement de direction.

👉 Aucune dépendance critique à un individu unique.

Invariant 12 — Fidélité au réel
Le système enregistre ce qui s'est passé, pas ce qui aurait dû se passer:

dépôts hors délai enregistrés (pas effacés),

dérogations captées (pas corrigées),

incohérences visibles (pas masquées).

👉 Un PV réaliste vaut mieux qu'un PV artificiellement "propre".

§ 3 — SCOPE V1 (Non négociable)
3.1 Périmètre strict
UN seul processus procurement par instance d'exécution (DAO ou RFQ, jamais mixé).

Maximum 3 écrans utilisateur pour l'usage courant.

Un cas réel end-to-end comme référence de validation.

Conçu pour usage terrain sous pression.

Aucune configuration en V1.

Définition "un processus": Du lancement DAO/RFQ jusqu'à la génération du PV et décision finale, pour un seul DAO/RFQ à la fois.

👉 Tout ce qui sort de ce scope est explicitement hors V1.

3.2 Ce qui est explicitement INTERDIT en V1
Scoring/ranking/notation globale de fournisseurs

Recommandations ou suggestions automatiques de choix

Dashboards, KPIs, analytics pour HQ

Fonctionnalités de compliance/audit/fraude

Multi-workflow complexe

Toute saisie de données dont le seul but est reporting/documentation

Dépendance ou couplage fort à un ERP

Logique d'optimisation de quelque nature que ce soit

👉 Si une feature "semble utile" mais viole ces règles, elle est hors scope.

§ 4 — COUCHE A: L'OUVRIER COGNITIF (Assistant opérationnel)
4.1 Rôle
Remplacer le secrétariat procurement en absorbant toute la paperasse avant la décision humaine.

4.2 Fonctions autorisées (exhaustif pour V1)
Module 1 — Ingestion pragmatique (formats prioritaires)
Formats V1 (prioritaires, robustes):

DAO/RFQ: Word (.docx), PDF, Excel (.xlsx) → formats structurés standard SCI.

Offres techniques/financières: Word (.docx), PDF → formats professionnels attendus.

Scans: PDF de qualité acceptable (documents scannés en bureau, pas terrain).

Formats évolution future (post-V1, après validation adoption):

Photos WhatsApp, images basse résolution, scans terrain dégradés.

OCR avancé sur documents manuscrits ou très bruités.

Fonctions Module 1:

Accepter les formats V1 prioritaires.

Classifier automatiquement chaque fichier (DAO vs offre, technique vs financière).

Détecter le fournisseur (en-tête, signature, cachet) avec score de confiance.

Détecter le(s) lot(s) concerné(s) avec score de confiance.

Horodater tout automatiquement.

Gestion des erreurs (clé pour ne pas augmenter charge cognitive):

Chaque champ extrait a un score de confiance (élevé/moyen/faible).

Champs à faible confiance → surbrillance orange + validation rapide utilisateur (1 clic confirmation ou correction).

Si extraction échoue totalement → fallback: saisie manuelle guidée ultra-rapide (3–5 champs max).

👉 Principe: mieux vaut un champ à valider rapidement qu'un blocage ou une erreur silencieuse.

Module 2 — Extraction structurée (alignée manuel procurement SCI)
Stratégie technique V1:

Approche hybride: règles + modèles légers (pas de ML coûteux en V1).

Extraction basée sur patterns récurrents dans les templates SCI standards.

Si document non-standard → extraction partielle + champs manuels guidés.

DAO/RFQ → extraire:

Structure des lots (numéro, libellé, catégorie).

Critères d'évaluation alignés Manuel Procurement SCI (essentiels, capacité, commerciaux, durabilité) et pondérations.

Zone, catégorie, type de procédure (devis simple/formel/AO ouvert), valeur estimée.

Référence implicite: Manuel SC-PR-02 Procurement Manual 3.2 SCI (règles métier extraites et mappées en backend, jamais mentionnées frontend).

Offres techniques → extraire:

Conformité administrative (docs présents/manquants): RC, NIF/IFU, CNPS, attestation fiscale, formulaire signé, etc.

Éléments de capacité: nb contrats similaires, personnel clé, moyens matériels, références.

Sites visitables, certifications.

Score de confiance par champ.

Offres financières → extraire:

Prix (unitaires et totaux par article/lot).

Délais de livraison.

Validité d'offre.

Conditions de paiement.

Score de confiance par champ.

Règles métier implicites (backend, jamais exposées utilisateur):

Critères essentiels: conformité admin obligatoire (seuil pass/fail).

Critères capacité: notation 0–100 ou 0–10 (validée humainement).

Critères commerciaux: prix, conditions paiement.

Critères durabilité: environnement, social.

Pondérations standards par type de procédure (extraites du manuel, appliquées silencieusement).

👉 L'outil connaît les règles SCI, mais l'utilisateur n'a jamais à les chercher ou les saisir.

Module 3 — Pré-remplissage CBA et PV (templates intelligents embarqués)
Stratégie templates V1:

CBA (Comparative Bid Analysis):

Templates embarqués dans l'outil (pas de chargement manuel).

Un template par catégorie majeure (matériel bureau, NFI, vivres, cartouches, mobilier, location véhicules, services).

Structure:

Colonnes = fournisseurs (noms auto-remplis).

Lignes = critères (essentiels booléens, capacité 0–100, prix, délais, durabilité).

Formules Excel natives préservées (calculs de scores, totaux, rankings).

Pré-remplissage automatique:

Tous les champs factuels (noms, prix, délais, docs présents/manquants).

Cellules non trouvées → orange "NON TROUVÉ" + score confiance faible.

Cellules à valider → jaune + icône validation rapide.

Export Excel standard (.xlsx) 100% éditable par l'utilisateur.

PV (Procès-Verbal):

Template Word embarqué (structure standard SCI).

Sections auto-remplies:

En-tête: ID DAO, zone, date, lots, membres comité.

Contexte: rappel DAO/RFQ, critères, pondérations.

Liste offres reçues par lot (fournisseur, horodatage, mode dépôt).

Résumé conformité (nb offres conformes/non conformes par critère essentiel, avec détails factuels).

Tableau résumé CBA (collé ou référencé).

Bloc "DÉCISION DU COMITÉ" vide ou pré-formaté (à remplir manuellement).

Export Word standard (.docx) 100% éditable.

Mention obligatoire footer: "Document préparé avec assistance — Décision finale humaine."

Mapping automatique templates:

Détection automatique catégorie DAO → sélection template CBA correspondant.

Si catégorie ambiguë ou nouvelle → template CBA générique + alerte validation catégorie.

Templates stockés en base (versioning possible, pas de re-upload à chaque cas).

👉 L'utilisateur n'a jamais à charger un template vide. L'outil sait lequel utiliser.

Module 4 — Génération d'artefacts
Export Excel, PDF, Word standards.

Aucun format propriétaire.

Tous les exports sont autonomes (pas de lien vers l'outil pour être lus).

4.3 Ce que la Couche A ne fait JAMAIS
Ne recommande pas de fournisseur.

Ne calcule pas de "score global meilleur fournisseur" (Excel peut le faire, pas l'outil).

Ne décide rien.

Ne juge pas la qualité des offres moralement.

👉 Elle transforme "un tas de docs" en CBA/PV prêts, sans décider.

§ 5 — COUCHE B: LE COLLÈGUE EXPÉRIMENTÉ (Intelligence de mémoire)
5.1 Rôle
Transformer la mémoire décisionnelle en référentiel de marché actionnable, sans devenir un outil de contrôle ou de scoring.

5.2 Architecture Market Intelligence (produit stratégique)
Base de données centrale: MARKET_INTEL

Contient:

supplier_name, zone, category, item_description, lot_id

prix_unitaire, prix_total, devise, delai_livraison

date_observation, source (DAO/RFQ/SURVEY)

case_id (lien vers cas, NULL si survey)

awarded (fournisseur retenu? NULL si survey)

contract_type (FWA, LTA, PO, NULL)

incident_flag, incident_details, remarks

created_at, created_by

Objectif: base dense et immense pour market assessment intelligent.

5.3 Alimentation de la mémoire (deux sources)
Source 1 — Alimentation passive (prioritaire, automatique)
Après chaque décision finalisée (via Couche A):

Pour chaque SOUMISSION évaluée (fournisseur + lot):

Extraction automatique: supplier_name, zone, category, lot_id, prix_total, delai_livraison, source (DAO/RFQ).

awarded = TRUE si fournisseur retenu, FALSE sinon.

incident_flag (si signalé plus tard: retard, qualité, docs manquants).

Insertion dans MARKET_INTEL.

Structuration sortie Couche A pour alimenter mémoire:

PV Word contient balises structurées (non visibles utilisateur, XML/JSON embedded ou DB directe):

<decision>Fournisseur X retenu sur Lot 01</decision>

<justification>Prix compétitif + délai respecté + expérience prouvée</justification>

Ces balises permettent extraction automatique décision/justification → mémoire.

👉 Mémoire se nourrit des sorties Couche A sans effort supplémentaire.

Source 2 — Alimentation active (surveys terrain, évolution future)
Application mobile/web ultra-légère séparée (future):

Standards Save the Children (design system, sécurité, accessibilité).

Interface < 6 champs obligatoires:

Fournisseur (dropdown alimenté par base ou texte libre).

Zone (dropdown).

Catégorie (dropdown).

Item (texte libre).

Prix (numérique + devise auto FCFA).

Date (auto-remplie, ajustable).

Champs optionnels: délai livraison, remarques.

Temps de saisie cible: < 45 secondes.

Données insérées dans MARKET_INTEL avec source = "SURVEY", case_id = NULL, awarded = NULL.

Alignement SCI (implicite, jamais mentionné dans Constitution):

Catégories dropdown = catégories standards Manuel Procurement SCI.

Zones = zones opérationnelles SCI Mali (Centre, Nord, Mopti, Bandiagara, etc.).

Mapping backend garantit cohérence données.

👉 Application survey = outil compagnon, pas intégré V1 core. Évolution post-adoption.

5.4 Fonctions autorisées (exhaustif pour V1)
Recherche factuelle simple:

"Afficher tous les marchés de cartouches dans le Centre en 2024–2025."

"Quels fournisseurs ont déjà livré sur des FWA IT au Mali ?"

"Liste des décisions où un seul fournisseur était conforme (eWaiver)."

Rappels contextuels non intrusifs:

Lors de la création d'un nouveau cas, si DAO similaire existe (même catégorie/zone/procédure):

Panneau latéral "Contexte marché" (non bloquant, fermable):

"X cas similaires dans les 12 derniers mois."

"Fourchette de prix observée: Y–Z FCFA (moyenne: W FCFA)."

"Fournisseurs ayant déjà livré: A (3 contrats, 0 incidents), B (5 contrats, 1 retard), C (2 contrats, 0 incidents)."

"Incidents récurrents: docs manquants (30% cas), retards livraison (20% cas)."

👉 Affichage factuel, jamais prescriptif ("A est meilleur" interdit).

Paquet audit/onboarding:

Endpoint /api/case/{case_id}/full-package:

ZIP contenant:

DAO/RFQ original.

Toutes offres (techniques + financières).

CBA généré.

PV généré.

Décision + justification.

Éventuels eWaiver, contrats, avenants.

Résumé texte simple (1 page): "Marché cartouches, Centre, 8 offres, 2 conformes, FWA 3 ans non fixe avec X et Y."

👉 Usage: onboarding nouveau logisticien, audit terrain, Head of Supply Chain review.

Market Intelligence queries:

Prix moyen par catégorie/zone/période.

Fournisseurs fiables par catégorie/zone (nb contrats, nb incidents).

Cas similaires (recherche par critères multiples).

Alertes prix anormaux (écart > seuil vs moyenne, ex: ±30%).

5.5 Ce que la Couche B ne fait JAMAIS
❌ Notation globale de fournisseurs (ex: "score 85/100").

❌ Classement automatique ("Top 10 fournisseurs").

❌ Recommandations automatiques ("choisissez X").

❌ Dashboards de performance HQ pour juger personnes ou équipes.

❌ Prédictions ou conseils sur "que faire".

👉 Si une feature de Couche B "suggère" une décision ou "juge" un fournisseur globalement, elle viole la Constitution.

👉 Si elle "rappelle des faits" ou "montre ce qui s'est passé avant", elle est conforme.

§ 6 — GOUVERNANCE DES ALERTES (Clé politique)
6.1 Nature des alertes
Les alertes sont des rappels, jamais des accusations.

Exemples autorisés:

"Prix +65% vs moyenne historique zone/catégorie (basé sur X observations) — à vérifier."

"Fournisseur non observé historiquement sur cette catégorie dans cette zone."

"Dépôt effectué hors délai standard (tolérance possible selon contexte)."

"Document manquant: Attestation CNSS (requis par critère essentiel)."

Exemples INTERDITS:

❌ "Anomalie suspecte"

❌ "Risque de fraude"

❌ "Non-conformité grave"

❌ "Fournisseur peu fiable"

6.2 Statut des alertes
Chaque alerte est:

consultative (pas bloquante),

désactivable par justification humaine (texte libre court ou dropdown raisons).

👉 Ignorer une alerte est un droit. Justifier l'ignorance est la seule obligation.

6.3 Seuils dynamiques
Seuils alertes (ex: ±30% prix) sont ajustables backend (pas par utilisateur V1).
Basés sur:

densité données historiques (si < 5 observations, pas d'alerte prix),

variabilité observée (si écart-type élevé, seuil plus large).

👉 Alertes intelligentes, pas mécaniques.

§ 7 — ÉVOLUTION VERS UN ASSISTANT INTELLIGENT (LLM léger)
7.1 Vision future
Le système peut évoluer vers un assistant conversationnel intelligent (LLM léger intégré):

Répondre à des questions en langage naturel ("Quels fournisseurs ont livré des kits NFI dans le Centre l'an dernier ?").

Générer des résumés narratifs de cas similaires.

Assister à la rédaction de justifications (brouillons modifiables).

Détecter des patterns récurrents (ex: "3 retards consécutifs sur cette catégorie dans cette zone").

Critères déclenchement LLM:

Couche A/B validée en production (adoption > 80% bureau pays).

Base MARKET_INTEL dense (> 500 entrées).

Budget infrastructure LLM validé.

7.2 Règles d'intégration LLM
Autorisé:

Réponses factuelles basées sur base de données interne uniquement (pas d'hallucination externe).

Génération de texte descriptif/narratif (brouillons PV, résumés, justifications).

Extraction améliorée de documents complexes (DAO/RFQ/offres non-standards).

Interaction en langage naturel pour recherche mémoire.

INTERDIT (même avec LLM):

Recommandations de fournisseur ("je vous conseille X").

Jugements de valeur ("cette offre est meilleure").

Prédictions probabilistes ("X a 85% de chances de gagner").

Génération de scores/rankings automatiques.

Stratégie technique:

LLM léger type Mistral 7B, Llama 3 8B, ou GPT-3.5 fine-tuné.

Prompts gouvernés (prompt engineering strict, versioning, auditable).

RAG (Retrieval-Augmented Generation) sur base MARKET_INTEL locale.

Aucune connexion modèles externes non contrôlés.

👉 Le LLM reste un outil d'assistance cognitive, jamais un décideur.

7.3 Garde-fou LLM
Toute sortie générée par LLM doit inclure explicitement:

"Ce texte a été généré avec assistance IA. La décision finale relève exclusivement du jugement humain, compte tenu du contexte opérationnel, des contraintes terrain et des informations disponibles au moment de la décision."

§ 8 — CLAUSE DE SOUVERAINETÉ LOCALE
La mémoire appartient à l'entité opérationnelle locale.

Pas d'export automatique vers HQ.

Pas de dashboard global par défaut.

Pas d'agrégation centrale sans accord explicite (process formal governance).

Mécanisme accord explicite:

Demande écrite HQ → validation Country Director + Head of Supply Chain local.

Export anonymisé/agrégé uniquement (pas de données individuelles cas).

Tracé dans audit log.

👉 Le local n'est pas un sous-traitant du HQ.

§ 9 — TEST ULTIME DE DÉRIVE (Garde-fou systématique)
Avant toute évolution (feature, module, intégration), poser ces 3 questions:

Est-ce que cela peut être utilisé contre un individu ?

Est-ce que cela réduit la liberté de décision humaine ?

Est-ce que cela centralise le pouvoir cognitif ?

👉 Si OUI à une seule → rejet ou report Phase 3+.

Process application:

Intégré dans validation GitHub (PR template avec checklist).

Révision Tech Lead + Product Owner obligatoire.

Documentation justification si réponse "OUI" (pourquoi malgré tout acceptable, ou pourquoi rejet).

§ 10 — CRITÈRES DE SUCCÈS V1
Le succès de V1 est démontré lorsque:

L'utilisateur complète une tâche procurement plus vite (mesure: temps moyen ouverture → PV prêt < 50% temps manuel).

Avec moins de fatigue mentale (feedback qualitatif utilisateurs).

Sans formation préalable (onboarding < 15 minutes).

Sans explication pendant l'usage (taux de sollicitation support < 5%).

Sans altération de son autorité décisionnelle (aucune plainte "l'outil a décidé à ma place").

Mesures concrètes:

Temps comité: de 3 jours (cas MOPTI-2026-01) → < 1 jour.

Taux adoption: > 80% bureau pays dans 6 mois.

Satisfaction utilisateur: > 4/5 (NPS positif).

👉 Si le système nécessite une explication, il a déjà échoué.

§ 11 — ALIGNEMENT IMPLICITE MANUEL PROCUREMENT SCI
Règle stratégique:

Les règles métier du système sont extraites et mappées du Manuel SC-PR-02 Procurement Manual 3.2 FR (Save the Children International).

Éléments mappés (backend uniquement, jamais exposés utilisateur):

Types de procédures (devis simples, formels, AO ouvert/restreint, RFQ, FWA).

Seuils monétaires par type procédure.

Critères d'évaluation standards (essentiels, capacité, commerciaux, durabilité).

Pondérations par défaut par type procédure.

Documents administratifs requis (RC, NIF, CNSS, quitus, etc.).

Délais standards (publication, soumission, évaluation).

Composition comité minimum.

Principe:

L'utilisateur n'a jamais à chercher dans le manuel.

L'outil applique silencieusement les règles SCI.

Si conflit règle/contexte → alerte neutre + choix utilisateur (avec justification).

Avantage stratégique:

Outil inattaquable en audit (conforme manuel by design).

Réduction charge cognitive (pas de vérification manuelle règles).

Évolution manuel → simple mise à jour mapping backend (pas de retraining utilisateurs).

👉 L'outil connaît les règles SCI. L'utilisateur ne les voit jamais, il les applique naturellement.

§ 12 — PRINCIPE DE SURVIE (Clause de clôture)
Ce système doit survivre à:

son créateur (Abdoulaye Ousmane),

tout individu contributeur,

tout manager ou sponsor,

toute restructuration organisationnelle.

Garanties techniques:

Stack simple, documenté, standard (Python/FastAPI, SQLite→PostgreSQL, React/Vue).

Données lisibles (SQL standard, exports CSV/JSON).

Documentation complète (README, API docs, architecture docs).

Aucun savoir caché (pas de "magie" non documentée).

La vision, les invariants, et le mandat sont au-dessus de toutes les implémentations.

Les invariants ne sont:

ni des recommandations,

ni des bonnes pratiques,

ni des orientations.

👉 Ils sont des contraintes structurelles. Si une évolution viole un invariant, elle est rejetée sans débat.

§ 13 — GOUVERNANCE DE LA CONSTITUTION
Processus de modification:

Amendements mineurs (clarifications, exemples): Tech Lead + Product Owner.

Amendements majeurs (nouveaux invariants, changement scope): governance board (Country Director + Head of Supply Chain + Tech Lead + 2 utilisateurs terrain).

Invariants §2 intouchables sauf urgence absolue (justification écrite, validation unanime board).

Versioning:

Format: X.Y (X = majeur, Y = mineur).

Chaque version datée, tracée Git, changelog public.

Version actuelle toujours accessible dans CONSTITUTION.md repo racine.

§ 14 — STATUT DU DOCUMENT
Version: 1.2 (Production-ready)

Date: 6 février 2026

Statut: FROZEN (évolutive sous invariants uniquement)

Modification: uniquement via processus gouvernance §13

Rôle: Référence ultime du projet

© 2026 — Decision Memory System — Constitution V1.2

This system protects organizations from forgetting, not from their people.
