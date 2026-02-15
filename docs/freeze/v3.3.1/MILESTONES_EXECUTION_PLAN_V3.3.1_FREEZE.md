
1. Milestones Couche A – Documents → Extraction → Normalisation → Scoring → Génération
1.1. M DOCS CORE — Pipeline documents & extractions
Milestone	Fonction	Ce que ça résout	Lien Constitution
M DOCS CORE	Implémenter le modèle documents, extractions, extraction_corrections + endpoints upload/consultation.	Passage propre “fichiers uploadés → données exploitables”, avec intégrité, statut, et corrections tracées.	§6.1 entité documents/extractions/corrections, INV 6 (append only), INV 9 (fidélité au réel).
Rôle dans la séquence:
C’est l’entrée canonique du système pour tous les processus d’achat (DAO/RFQ/RFP/Achat simple/marché négocié/procédure hybride). Aucun travail d’extraction sérieux ne peut commencer sans ce socle.
________________________________________
1.2. M EXTRACTION ENGINE – Moteur d’extraction 3 niveaux
Milestone	Fonction	Ce que ça résout	Lien Constitution
M EXTRACTION ENGINE	Construire ExtractionEngine 3 niveaux (règles SCI, parsing PDF/Excel/Word, OCR providers Azure/Tesseract) avec confidence score.	Extraire du texte et des données structurées de tout type de document, avec un niveau de confiance mesurable.	§2.1 (Extraction), §5.2 (OCR, parsing), §7.1 7.2 (SLA Classe A/B).
Rôle:
Transforme les documents en extractions (raw_text + structured_data JSONB) pour alimenter critères/offres, tout en respectant la performance (Classe A/B).
________________________________________
1.3. M EXTRACTION CORRECTIONS – Traçabilité des corrections humaines
Milestone	Fonction	Ce que ça résout	Lien Constitution
M EXTRACTION CORRECTIONS	Implémenter extraction_corrections + UI/endpoint de correction champ par champ avec before/after, user, timestamp.	Permettre à l’humain de corriger l’OCR/parsing sans perdre la donnée originale, et tracer chaque correction.	§2.1 (l’humain contrôle), §6.1 (extraction_corrections), INV 9 (fidélité au réel).
Rôle:
Verrouille le principe “correction humaine tracée, jamais destructive”, base essentielle pour audit et confiance.
________________________________________
1.4. M CRITERIA TYPING (M3A déjà posé) – Critères typés universels
Milestone	Fonction	Ce que ça résout	Lien Constitution
M CRITERIA TYPING (M3A)	Extraire et typer les critères (commercial/capacity/sustainability/essentials) pour tout type de processus.	Donner une base structurée et typée au moteur de scoring, indépendamment du type de procédure.	§1.1 (universalité DAO/RFQ/RFP…), §2.1 (Scoring).
Rôle:
C’est la passerelle entre extraction brute et logique de scoring multi critères.
________________________________________
1.5. M NORMALISATION ITEMS – Dictionnaire procurement (items + unités)
Milestone	Fonction	Ce que ça résout	Lien Constitution
M NORMALISATION ITEMS	Implémenter procurement_dictionary (items canoniques, unités, alias) + moteur de normalisation (quantités, unités, catégories).	Standardiser les lignes d’offre pour comparaison équitable, éliminer les divergences d’écriture et d’unités.	§2.3 (dictionnaire procurement), §6.3 (procurement_dictionary), INV 1 (réduction charge cognitive).
Rôle:
Permet de comparer des offres sur une base homogène avant scoring commercial/capacité.
________________________________________
1.6. M SCORING ENGINE (M3B FINAL) – Scoring multi critères non prescriptif
Milestone	Fonction	Ce que ça résout	Lien Constitution
M SCORING ENGINE (M3B)	Moteur de scoring universel (commercial, capacity, sustainability, essentials, total) basé sur criteria + offers normalisées, tables supplier_scores et supplier_eliminations.	Convertir critères + offres en scores factuels, avec traçabilité des éliminations, sans décider ni classer pour l’utilisateur.	§2.1 (Scoring), §2.2 (Couche B ne modifie pas), §6.2 (supplier_scores/eliminations), INV 3 (mémoire non prescriptive), INV 9.
Rôle:
Cœur décisionnel de la Couche A, configurable par type de processus mais basé sur une base algorithmique unique.
________________________________________
1.7. M SCORING TESTS CRITIQUES (M TESTS V2 P1/P2/FULL)
Milestone	Fonction	Ce que ça résout	Lien Constitution
M SCORING TESTS CRITIQUES	Série de tests unitaires + property based + E2E couvrant scoring edge cases, performance (100+ fournisseurs), idempotence, indépendance vis à vis de la Couche B.	Garantir que le scoring est correct, stable, rapide, et qu’il ne dépend pas de la mémoire marché.	INV 2 (Couche A autonome), INV 3 (scores indépendants Couche B), §7 (SLA).
Rôle:
Verrouille la qualité, la performance et les invariants sur le moteur de scoring.
________________________________________
1.8. M CBA TEMPLATES / M PV TEMPLATES (M5) – Templates normalisés
Milestone	Fonction	Ce que ça résout	Lien Constitution
M CBA TEMPLATES	Créer templates CBA Excel (.xlsx) canoniques (multi onglets, formules, mise en forme) pour les différentes familles d’achats.	Standardiser les livrables CBA, éviter réinvention ou modification manuelle dangereuse.	§1.2 (livrables requis), §8.2 (Export CBA).
M PV TEMPLATES	Créer templates PV Word (.docx) avec placeholders alignés sur le modèle de données (décisions, scores, commentaires).	Accélérer la rédaction des PV tout en restant conforme aux formes attendues (État, ONG, mines).	§1.2 (livrables), §8.2 (Export PV).
Rôle:
Fournit les supports officiels de sortie pour comités et archivage.
________________________________________
1.9. M CBA GEN / M PV GEN (M6) – Génération CBA/PV automatisée
Milestone	Fonction	Ce que ça résout	Lien Constitution
M CBA GEN	Implémenter CBAGenerator (openpyxl) pour produire des CBA prêts à l’usage à partir des scores + offres normalisées.	Automatiser ce que l’utilisateur fait aujourd’hui dans Excel, en respectant formules et structure.	§2.1 (Génération), §5.2 (openpyxl), INV 1.
M PV GEN	Implémenter PVGenerator (python docx) pour produire des PV Word pré remplis.	Éviter la saisie manuelle répétitive des PV, tout en gardant la décision finale humaine.	§2.1 (Génération), §5.2 (python-docx), INV 1, INV 9.
Rôle:
Finalise la Couche A sortie : DAO/RFQ/RFP → CBA + PV.
________________________________________
1.10. M PIPELINE A E2E – Pipeline Couche A complet + SLA Classe A
Milestone	Fonction	Ce que ça résout	Lien Constitution
M PIPELINE A E2E	Tests end to end “documents natifs (PDF/Excel/Word) → CBA/PV” avec timers intégrés pour vérifier SLA <60s.	Vérifier que la Couche A tient la promesse de vitesse sur les documents natifs.	§7.1 (Classe A), INV 1.
Rôle:
C’est la validation que la Couche A peut fonctionner seule, sans Couche B, et plus vite que le manuel.
________________________________________
2. Milestones Couche B – Mémoire, Market Signal, Dictionnaire étendu
2.1. M MARKET DATA TABLES – Mercuriale, historique décisions, Market Surveys
Milestone	Fonction	Ce que ça résout	Lien Constitution
M MARKET DATA TABLES	Créer tables mercurials, decision_history, market_surveys + schémas alignés sur §6.3.	Structurer les 3 sources de vérité du Market Signal.	§3.2 (3 sources), §6.3.
________________________________________
2.2. M MARKET INGEST – Ingestion mercuriale & auto feed décisions
Milestone	Fonction	Ce que ça résout	Lien Constitution
M MARKET INGEST	Endpoints/import tools pour mercuriale officielle + auto feed decision_history après chaque décision validée.	Maintenir les sources de vérité marché à jour sans effort manuel excessif.	§3.2–3.3, §2.2 (Couche B).
________________________________________
2.3. M MARKET SURVEY WORKFLOW – Workflow Market Survey terrain
Milestone	Fonction	Ce que ça résout	Lien Constitution
M MARKET SURVEY WORKFLOW	UI/API pour créer et stocker les Market Surveys (min. 3 cotations/item, validité 90j).	Assurer que le Market Survey ne reste pas théorique mais intégré dans le système.	§3.1–3.3 (Market Survey obligatoire, fraîcheur 90 jours).
________________________________________
2.4. M MARKET SIGNAL ENGINE – Agrégation 3 sources + règles de priorité
Milestone	Fonction	Ce que ça résout	Lien Constitution
M MARKET SIGNAL ENGINE	Implémenter MarketSignalProvider qui agrège mercuriale, historique, Market Surveys avec règles de priorité, fraîcheur, dégradations (⚠️, 🔴, ⬛).	Fournir un signal prix cohérent, explicable, non prescriptif, même quand certaines sources manquent.	§3.3–3.4, INV 3 (non prescriptif).
________________________________________
2.5. M CONTEXT UI PANEL – Panneau UI Market Signal (Couche B → Couche A)
Milestone	Fonction	Ce que ça résout	Lien Constitution
M CONTEXT UI PANEL	Panneau latéral “Contexte marché” affichant le Market Signal par item (prix min/avg/max, tendances, état des 3 sources).	Donner à l’acheteur la mémoire marché au moment de la décision, sans changer les scores.	§3.4 (flux Market Signal → A), §2.2 (Couche B read only), INV 3.
________________________________________
2.6. M DICT FUZZY MATCH – Fuzzy matching dictionnaire (items & fournisseurs)
Milestone	Fonction	Ce que ça résout	Lien Constitution
M DICT FUZZY MATCH	Implémenter algos fuzzy (Levenshtein + token based) sur procurement_dictionary pour items/fournisseurs, avec seuil configurable.	Résoudre les variations d’écriture tout en forçant la validation humaine sous le seuil de confiance.	§2.3 (dictionnaire), INV 9 (fidélité & correction tracée), §7.3 (fuzzy <100ms).
________________________________________
3. Milestones Transverses – Sécurité, Traçabilité, Performance, CI
3.1. M SECURITY CORE – Auth, RBAC, audit_log, rate limiting
Milestone	Fonction	Ce que ça résout	Lien Constitution
M SECURITY CORE	JWT (access/refresh), RBAC 5 rôles, table audit_log append only, rate limiting par endpoint/user, validation uploads (magic bytes, taille, whitelist).	Protection accès, traçabilité actions, défense contre abus et fichiers malveillants.	§5.4 (Sécurité), §6.4 (audit_log), INV 6 (append only), §7 (SLA).
________________________________________
3.2. M TRACE HISTORY – score_history & elimination_log
Milestone	Fonction	Ce que ça résout	Lien Constitution
M TRACE HISTORY	Créer score_history et elimination_log append only (+ tests interdiction DELETE/UPDATE).	Garder l’historique des scores et éliminations, versionnés, pour audit/contrôle.	§6.4 (tables traçabilité), INV 6.
________________________________________
3.3. M CI INVARIANTS – Tests CI pour chaque invariant
Milestone	Fonction	Ce que ça résout	Lien Constitution
M CI INVARIANTS	Implémenter la table Annexe A en tests CI réels (performance, indépendance Couche A, pas de dépendance ERP, Readme présent, etc.).	Rendre chaque invariant testable et non théorique ; blocage CI si violation.	Annexe A (Invariants ↔ tests CI), INV 1 à INV 9, INV 5 (CI verte).
________________________________________
3.4. M MONITORING OPS – Logs JSON & métriques Prometheus
Milestone	Fonction	Ce que ça résout	Lien Constitution
M MONITORING OPS	Logger JSON global + métriques Prometheus (SLA Classe A/B, queries Market Signal, fuzzy, charge).	Rendre visible les SLA, détecter toute régression de performance.	§7 (SLA), §5.3 (Healthcheck, monitoring).
________________________________________
3.5. M DEVOPS DEPLOY – Docker, CI/CD, santé
Milestone	Fonction	Ce que ça résout	Lien Constitution
M DEVOPS DEPLOY	Docker + docker compose, GitHub Actions (tests, coverage, lint), déploiement Railway, health /api/health.	Assurer un déploiement reproductible, contrôlé, et bloquer tout merge si la CI échoue.	§5.3 (DevOps & déploiement), INV 5 (CI verte obligatoire).
________________________________________
4. Milestones Produit & Terrain – UX, Early adopters, ERP agnostique
4.1. M UX FLOW 3 SCREENS – 3 écrans canoniques
Milestone	Fonction	Ce que ça résout	Lien Constitution
M UX FLOW 3 SCREENS	Concevoir et implémenter le flow 3 écrans: Ingestion → Structuration → Décision, UI minimaliste mais complète.	Aligner l’UX sur le modèle “un processus d’achat = règles + critères + offres + décision humaine” sans complexité additionnelle.	§1.2 (abstraction canonique), §2.1 (Couche A), INV 1.
________________________________________
4.2. M UX TEST TERRAIN – Tests utilisateurs & T_DMS
Milestone	Fonction	Ce que ça résout	Lien Constitution
M UX TEST TERRAIN	Mesurer T_DMS vs T_manuel sur un cas complet (DAO/RFQ) + feedback qualitatif.	Vérifier concrètement que le système divise le temps par ≥5 (20%) et réduit la charge cognitive.	INV 1 (T_DMS < 0.2 T_manuel).
________________________________________
4.3. M ERP AGNOSTIC CHECK – Vérification indépendance ERP
Milestone	Fonction	Ce que ça résout	Lien Constitution
M ERP AGNOSTIC CHECK	Scan imports + endpoints, validation que le DMS n’est lié à aucun ERP spécifique (uniquement API/exports).	Garantir que le DMS reste utilisable par États, ONG, mines, entreprises sans verrou propriétaire.	§8.1–8.3 (ERP agnostique), INV 7.
________________________________________
4.4. M PILOT EARLY ADOPTERS – Déploiement pilote & NPS
Milestone	Fonction	Ce que ça résout	Lien Constitution
M PILOT EARLY ADOPTERS	Déploiement pilote SCI Mali, suivi usage, métriques adoption (temps, erreurs, NPS, “je ne reviens pas à Excel”).	Valider que le système tient sa promesse produit sur le terrain et non seulement en CI.	§0 (raison d’être), §1, §3 (standard de référence), §9.3 (réversibilité).
________________________________________

