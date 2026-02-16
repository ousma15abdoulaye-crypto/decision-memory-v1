DMS — MILESTONES EXECUTION PLAN (V3.3.2)
Métadonnées du document
•	Version: V3.3.2
•	Date: 2026-02-16
•	Autorité: Abdoulaye Ousmane (Founder & CTO)
•	Statut: CANONIQUE · OPPOSABLE · FREEZABLE
•	Objet: Définir, sans ambiguïté, les milestones techniques et fonctionnels du DMS V3.3.2
•	Hash (à calculer lors du freeze): [SHA256 sera ajouté dans FREEZE_MANIFEST.md]
________________________________________
0. Préambule — Traçabilité & opposabilité
0.1. Documents de référence
Ce plan d'exécution s'appuie sur:
•	Constitution DMS V3.3.2 (docs/CONSTITUTION_DMS_V3.3.2.md)
•	ADR-0001 — Fusion M10-UX-V2 + M-SECURITY-CORE + Discipline Agents (docs/adrs/ADR-0001.md)
•	Invariants (docs/INVARIANTS.md)
•	Contrats techniques: SECURITY.md, PERFORMANCE_SLA.md, ARCHITECTURE.md, DATABASE_SCHEMA.md, API_REFERENCE.md
0.2. Principes d'exécution (opposables)
1.	Exécution séquentielle stricte: un milestone suivant ne démarre que si le précédent est DONE.
2.	Binaire: un milestone est DONE ou ABSENT, jamais "80% fait".
3.	Gates CI obligatoires:
o	CI verte (tous tests passent).
o	Coverage ≥ seuil défini par phase.
o	Invariants respectés.
o	SLA validés pour milestones critiques.
4.	Aucun contournement: tout agent (humain ou IA) doit lire Constitution + Plan + ADR-0001 avant de coder.
5.	Discipline ADR: toute modification de la structure des milestones = nouvel ADR + validation CTO.
0.3. Règles anti-improvisation (discipline agents)
•	Source de vérité unique: Constitution V3.3.2 + ce plan + ADR-0001.
•	Interdiction d'inventer des milestones en dehors de ce plan sans ADR validé.
•	Definition of Done commune (§7) s'applique à tous les milestones.
•	CI comme arbitre: aucune PR mergée avec CI rouge.
•	Agents IA: doivent respecter INV-3 (Couche B non prescriptive), INV-7 (ERP-agnostique), et ne jamais introduire de dépendance ERP ou logique Couche B dans Couche A.
________________________________________
1. Définitions — Terminologie stable
1.1. Case (cas)
Un "case" représente un processus d'achat unique: DAO/RFQ/RFP/achat simple/marché négocié/hybride.
Un case possède:
•	Référence
•	Type de procédure
•	Zone géographique
•	Documents (DAO/RFQ/ToR, offres, annexes)
•	Extractions (texte + données structurées JSONB)
•	Critères typés
•	Offres normalisées
•	Scores
•	Comité (composition + état de verrouillage)
•	Exports (CBA Excel, PV Word)
1.2. Documents / Extractions / Corrections
•	Document: fichier uploadé (PDF/Excel/Word/image) + métadonnées + statut.
•	Extraction: résultat de parsing/OCR (raw_text + structured_data JSONB) + confidence score + provenance.
•	Correction: action humaine append-only, champ par champ, avec value_before/value_after + auteur + timestamp + raison.
1.3. Normalisation (dictionnaire procurement)
Processus obligatoire transformant lignes d'offres "brutes" en lignes "canoniques" comparables:
•	Item canonique
•	Unité canonique
•	Quantités converties
•	Alias résolus
•	Validation humaine si confiance insuffisante
Règle opposable: aucune offre brute ne peut entrer dans le scoring (test CI test_no_raw_offer_in_scoring).
1.4. Scoring (non prescriptif)
Le scoring produit des valeurs calculées et traçables:
•	Conformité essentiels (pass/fail)
•	Score capacité
•	Score durabilité
•	Score commercial (prix)
•	Total pondéré
Le scoring n'émet pas de recommandation décisionnelle (INV-3).
1.5. Comité (brique conformité)
Entité structurée avec règles strictes:
•	Composition proposée automatiquement selon catégorie + seuil
•	Saisie minimale des identités (nom, prénom, fonction, email)
•	Verrouillage ("LOCK") irréversible
•	Après LOCK: la composition ne change jamais
•	Délégation autorisée sans modifier la composition (proxy), tracée append-only
________________________________________
2. Milestone Registry — IDs canoniques & dépendances
ID Milestone	Titre	Phase	Dépendances
M-DOCS-CORE	Pipeline documents & extractions	0	Aucune
M-EXTRACTION-ENGINE	Moteur extraction 3 niveaux	0	M-DOCS-CORE
M-EXTRACTION-CORRECTIONS	Corrections append-only	0	M-EXTRACTION-ENGINE
M-CRITERIA-TYPING	Critères typés universels	1	M-EXTRACTION-ENGINE
M-NORMALISATION-ITEMS	Dictionnaire procurement	1	M-EXTRACTION-ENGINE
M-SCORING-ENGINE	Scoring multi-critères	2	M-CRITERIA-TYPING, M-NORMALISATION-ITEMS
M-SCORING-TESTS-CRITIQUES	Tests critiques scoring	2	M-SCORING-ENGINE
M-COMMITTEE-CORE	Module comité + LOCK	2	M-DOCS-CORE
M-CBA-TEMPLATES	Templates CBA Excel	3	M-SCORING-ENGINE
M-PV-TEMPLATES	Templates PV Word	3	M-COMMITTEE-CORE
M-CBA-GEN	Génération CBA	3	M-CBA-TEMPLATES
M-PV-GEN	Génération PV	3	M-PV-TEMPLATES
M-PIPELINE-A-E2E	Pipeline Couche A complet	3	M-CBA-GEN, M-PV-GEN
M-SECURITY-CORE	Auth/RBAC/audit/rate limit	4	M-DOCS-CORE
M-TRACE-HISTORY	Historisation scores/éliminations	4	M-SCORING-ENGINE
M-CI-INVARIANTS	Tests CI invariants	4	M-PIPELINE-A-E2E, M-SECURITY-CORE
M-MARKET-DATA-TABLES	Tables mercuriale/history/surveys	5	Aucune (Couche B)
M-MARKET-INGEST	Ingestion mercuriale + auto-feed	5	M-MARKET-DATA-TABLES
M-MARKET-SURVEY-WORKFLOW	Workflow Market Survey terrain	5	M-MARKET-DATA-TABLES
M-MARKET-SIGNAL-ENGINE	Agrégation 3 sources	5	M-MARKET-INGEST, M-MARKET-SURVEY-WORKFLOW
M-CONTEXT-UI-PANEL	Panneau UI Market Signal	5	M-MARKET-SIGNAL-ENGINE
M-DICT-FUZZY-MATCH	Fuzzy matching dictionnaire	5	M-NORMALISATION-ITEMS
M-MONITORING-OPS	Logs JSON + métriques Prometheus	6	M-PIPELINE-A-E2E
M-DEVOPS-DEPLOY	Docker/CI/CD/Railway	6	M-MONITORING-OPS
M10-UX-V2	Interface Couche A complète	7	M-PIPELINE-A-E2E, M-SECURITY-CORE
M-UX-TEST-TERRAIN	Tests utilisateurs & T_DMS	7	M10-UX-V2
M-ERP-AGNOSTIC-CHECK	Vérification indépendance ERP	7	M-PIPELINE-A-E2E
M-PILOT-EARLY-ADOPTERS	Déploiement pilote & NPS	7	M-UX-TEST-TERRAIN, M-DEVOPS-DEPLOY

________________________________________
3. Milestones Couche A — Documents → Extraction → Normalisation → Scoring → Génération
3.1. M-DOCS-CORE — Pipeline documents & extractions
Fonction
Implémenter le socle "documents → extractions → corrections", avec intégrité, statuts, endpoints, et règles append-only.
Ce que ça résout
Passage propre "fichiers uploadés → données exploitables", avec:
•	Stockage fiable
•	Statut lisible par l'UX
•	Extraction associée au bon document
•	Corrections humaines traçables sans écraser l'original
Lien Constitution
•	Entités documents/extractions/corrections (§6.1)
•	Append-only (INV-6)
•	Fidélité au réel (INV-9)
Livrables techniques (obligatoires)
1.	Modèle de données (PostgreSQL)
•	Table documents
–	id, case_id, doc_type, original_filename, content_type, file_size_bytes
–	storage_backend, storage_path, sha256, uploaded_by, uploaded_at
–	status: uploaded, queued, extracted, failed
–	metadata (JSONB): zone, vendor, pages, etc.
•	Table extractions
–	id, document_id, case_id
–	raw_text (text)
–	structured_data (JSONB)
–	confidence_score (0..1)
–	extraction_method: pdf_text, ocr_azure, ocr_tesseract, excel_parser
–	provider_payload (JSONB, optionnel)
–	created_by, created_at
–	status: success, partial, failed
•	Table extraction_corrections (append-only)
–	id, extraction_id, document_id, case_id
–	field_path (ex: criteria[2].weight)
–	value_before (text)
–	value_after (text)
–	reason (text)
–	corrected_by, corrected_at
2.	API (FastAPI)
•	POST upload document: validation content-type, magic bytes, size limit, calcul sha256, réponse: document_id, status
•	GET document metadata
•	GET extractions by document
•	GET extraction détail (raw_text + structured_data)
•	POST correction extraction (append-only)
•	POST "rebuild structured view" (appliquer corrections sans supprimer l'original)
3.	Règles de sécurité minimales
•	Aucun fichier exécutable accepté
•	Whitelist explicite: PDF, XLSX, DOCX, images (si OCR)
•	Logs d'audit des actions: upload, extraction created, correction created
Tests obligatoires
•	tests/docs_core/test_upload_validation.py
•	tests/docs_core/test_extraction_corrections_append_only.py (vérifie interdiction UPDATE/DELETE)
•	tests/docs_core/test_document_extraction_link.py
Definition of Done (bloquante)
•	[ ] Toutes les tables existent, migrées par Alembic
•	[ ] Endpoints fonctionnels avec tests
•	[ ] Append-only garanti: interdiction UPDATE/DELETE sur extraction_corrections (trigger + test)
•	[ ] Un document uploadé doit être consultable et lié à un case
•	[ ] Une extraction doit être consultable et liée au bon document
•	[ ] Une correction doit être visible dans l'historique et ne pas modifier l'original
•	[ ] Tests passent en CI
________________________________________
3.2. M-EXTRACTION-ENGINE — Moteur d'extraction 3 niveaux
Fonction
Construire ExtractionEngine à 3 niveaux:
1.	Parsing natif (PDF text / DOCX / XLSX)
2.	Parsing structuré (tableaux, sections, entêtes)
3.	OCR providers (Azure + fallback Tesseract) avec scoring confiance
Ce que ça résout
Extraire texte et données structurées de tout type de document, avec niveau de confiance mesurable.
Lien Constitution
•	Extraction (Couche A, §2.1)
•	OCR / parsing
•	SLA Classe A/B (§7)
Livrables techniques (obligatoires)
1.	Service ExtractionEngine
•	Entrée: document_id
•	Sortie: insertion extractions (raw_text + structured_data + confidence_score)
•	Gestion erreurs: statut document failed si extraction impossible, stockage message d'erreur dans metadata document ou provider_payload
2.	Structured_data minimal standard (JSON)
•	doc_kind: dao, offer, tdr, annex
•	language
•	detected_tables (liste)
•	detected_sections (liste)
•	candidate_criteria (liste brute)
•	candidate_line_items (liste brute)
•	currency_detected
•	dates_detected
•	supplier_candidates (si document offre)
3.	Providers
•	PDF text extractor (sans OCR)
•	DOCX parser
•	XLSX parser
•	OCR Azure (si activé)
•	OCR Tesseract fallback (optionnel)
•	Stratégie: essayer parsing natif d'abord, basculer OCR si texte vide ou trop faible
4.	Mesure confiance
•	confidence_score calculé et stocké
•	Règles: taux de caractères non reconnus, cohérence tables détectées, présence champs attendus
Tests obligatoires
•	tests/extraction/test_extraction_engine_pdf.py
•	tests/extraction/test_extraction_engine_ocr_fallback.py
•	tests/extraction/test_confidence_score.py
Definition of Done (bloquante)
•	[ ] ExtractionEngine fonctionne sur PDF, DOCX, XLSX
•	[ ] Au moins 1 provider OCR branchable
•	[ ] confidence_score présent et testé
•	[ ] Tests sur fixtures réalistes
•	[ ] Cas "texte vide → OCR" et "OCR fail → failed" couverts
________________________________________
3.3. M-EXTRACTION-CORRECTIONS — Traçabilité des corrections humaines
Fonction
Implémenter correction humaine champ par champ, append-only, avec "before/after", auteur, timestamp, raison.
Ce que ça résout
Permettre de corriger l'OCR/parsing sans perdre la donnée originale.
Lien Constitution
•	Humain contrôle (§0)
•	extraction_corrections (§6.1)
•	INV-9 (fidélité au réel)
Livrables techniques (obligatoires)
1.	Mécanisme "vue corrigée"
•	L'extraction originale reste immutable
•	Corrections appliquées produisent structured_data_effective
•	Deux modes acceptables:
–	(A) calcul à la volée (apply corrections)
–	(B) materialized view / champ JSON recalculé (mais l'original reste)
2.	Endpoint correction
•	POST correction: extraction_id, field_path, value_before, value_after, reason
•	Validation: value_before doit correspondre à l'état courant effectif, sinon rejet (éviter conflits)
3.	Audit
Chaque correction produit une entrée audit (action, user, extraction_id).
Tests obligatoires
•	tests/extraction/test_corrections_append_only.py
•	tests/extraction/test_effective_structured_data.py
•	tests/extraction/test_correction_conflict_detection.py
Definition of Done (bloquante)
•	[ ] Correction append-only vérifiée (pas de DELETE/UPDATE possible)
•	[ ] Correction visible dans historique
•	[ ] structured_data_effective cohérent et testé
•	[ ] Tests passent en CI
________________________________________
3.4. M-CRITERIA-TYPING — Critères typés universels
Fonction
Extraire et typer les critères: commercial, capacity, sustainability, essentials (éliminatoires).
Ce que ça résout
Donner une base structurée au scoring, quel que soit le type de procédure.
Lien Constitution
•	Universalité procédures (§1.2)
•	Scoring (§2.1)
Livrables techniques (obligatoires)
1.	Modèle
•	Table criteria
–	id, case_id, source_extraction_id
–	label, category, weight, is_essential
–	expected_evidence (optionnel)
–	created_at, created_by
2.	Pipeline
À partir de structured_data_effective: détecter candidats critères, typage, stockage.
3.	Tests
Typage stable sur fixtures DAO/RFQ/RFP, edge cases: critères sans poids, poids total ≠ 100.
Tests obligatoires
•	tests/criteria/test_criteria_extraction.py
•	tests/criteria/test_criteria_typing.py
Definition of Done (bloquante)
•	[ ] Critères générés automatiquement
•	[ ] Corrigibles via corrections extraction (pas via UPDATE destructive)
•	[ ] Tests passants
________________________________________
3.5. M-NORMALISATION-ITEMS — Dictionnaire procurement (items + unités)
Fonction
Implémenter dictionnaire procurement et moteur de normalisation.
Ce que ça résout
Standardiser lignes d'offre pour comparaison équitable.
Lien Constitution
•	Dictionnaire procurement (§2.2)
•	INV-1 (réduction charge cognitive)
Livrables techniques (obligatoires)
1.	Modèle dictionnaire
•	Table procurement_items
–	id, canonical_name, category, default_unit, active
•	Table procurement_item_aliases
–	id, item_id, alias, lang, source
•	Table procurement_units
–	id, canonical_unit, unit_family (poids, volume, longueur, unité)
•	Table procurement_unit_conversions
–	from_unit, to_unit, factor
•	Table normalized_line_items
–	id, case_id, supplier_id, raw_label, raw_unit, raw_qty, raw_price
–	item_id, canonical_unit, canonical_qty, canonical_price
–	normalization_confidence, needs_human_validation (bool)
–	created_at
2.	Moteur de normalisation
•	Entrée: line items bruts issus des extractions
•	Sortie: normalized_line_items
•	Règles:
–	Mapping alias → item canonique
–	Conversion unités si possible
–	Calcul confidence
–	Si sous seuil: needs_human_validation = true
3.	UX / endpoints validation humaine (minimal)
•	GET items à valider
•	POST validation item (append-only événement)
Tests obligatoires
•	tests/normalisation/test_no_raw_offer_in_scoring.py (BLOQUANT CI)
•	tests/normalisation/test_item_alias_resolution.py
•	tests/normalisation/test_unit_conversion.py
Definition of Done (bloquante)
•	[ ] Aucune offre brute n'entre dans scoring (test CI bloquant)
•	[ ] Normalisation produit structure comparable
•	[ ] Validations humaines tracées
•	[ ] Tests passent
________________________________________
3.6. M-SCORING-ENGINE — Scoring multi-critères non prescriptif
Fonction
Moteur scoring universel sur critères typés + offres normalisées.
Ce que ça résout
Convertir critères + offres en scores factuels, traçables, sans prescrire.
Lien Constitution
•	Scoring (§2.1)
•	Couche B ne modifie pas (§3.1, INV-3)
•	INV-9 traçabilité
Livrables techniques (obligatoires)
1.	Modèle
•	Table supplier_scores
–	id, case_id, supplier_id
–	capacity_score, commercial_score, sustainability_score
–	weighted_total
–	essential_pass (bool)
–	computed_at, computed_by, scoring_version
•	Table supplier_eliminations
–	id, case_id, supplier_id
–	reason_codes (JSONB)
–	details (JSONB)
–	created_at
2.	Règles scoring
•	Essentials = gate: si fail → essential_pass false, score total non comparable
•	Commercial scoring basé sur prix normalisé
•	Poids basé sur criteria.weight
•	Output stable et reproductible
3.	Interdictions explicites
•	Aucun appel Couche B dans le scoring
•	Aucune règle "recommandation"
•	Aucune écriture dans tables Couche B
Tests obligatoires
•	tests/scoring/test_scoring_engine.py
•	tests/scoring/test_scores_independent_of_couche_b.py (BLOQUANT CI)
•	tests/scoring/test_elimination_reasons.py
Definition of Done (bloquante)
•	[ ] Scoring reproductible (idempotent)
•	[ ] Éliminations expliquées (reason_codes)
•	[ ] Aucune dépendance Couche B (test CI bloquant)
•	[ ] Tests passent
________________________________________
3.7. M-SCORING-TESTS-CRITIQUES — Tests critiques + performance
Fonction
Suite de tests unitaires, property-based et E2E couvrant edge cases, performance, idempotence, indépendance Couche B.
Ce que ça résout
Garantir scoring correct, stable, rapide.
Lien Constitution
•	Couche A autonome (§2.1)
•	Non prescriptif (INV-3)
•	SLA (§7)
Livrables techniques (obligatoires)
•	Tests unitaires scoring
•	Tests "100+ fournisseurs"
•	Tests "aucune dépendance Couche B"
•	Tests "no raw offer in scoring" (bloquant CI)
•	Tests performance (latence scoring < seuil défini)
Tests obligatoires
•	tests/scoring/test_scoring_performance_100_suppliers.py
•	tests/scoring/test_no_raw_offer_in_scoring.py
•	tests/scoring/test_idempotence.py
Definition of Done (bloquante)
•	[ ] CI bloque si:
o	Scoring lent au-delà seuil
o	Raw offers détectées
o	Dépendance Couche B détectée
•	[ ] Tests passent
________________________________________
3.8. M-COMMITTEE-CORE — Module Comité (règles + data model + LOCK irréversible)
Fonction
Créer module comité conforme:
•	Configuration automatique selon catégorie + seuil
•	Saisie minimale (nom, prénom, fonction, email)
•	Verrouillage irréversible
•	Composition immuable après verrouillage
•	Délégation autorisée sans changer membres
Ce que ça résout
Un comité réel, une fois verrouillé, ne bouge pas. Le système doit refléter cette réalité: toute flexibilité "post-lock" est non conforme et dangereuse.
Lien Constitution
•	Comité (§6, nouveau V3.3.2)
•	Conformité processus
•	Append-only (INV-6)
•	Fidélité au réel (INV-9)
Livrables techniques (obligatoires)
1.	Modèle de données (PostgreSQL)
•	Table committees
–	id, case_id
–	committee_type (evaluation, opening, technical, etc.)
–	composition_rule_id
–	status: draft → locked
–	locked_at, locked_by
–	created_at
•	Table committee_members
–	id, committee_id
–	role (buyer, finance, budget_holder, technical, observer, chair, etc.)
–	last_name, first_name, function, email
–	required (bool)
–	created_at, created_by
•	Table committee_events (append-only, obligatoire)
–	id, committee_id, case_id
–	event_type: created, member_added, locked, delegation_added
–	payload (JSONB)
–	created_at, created_by
2.	Verrouillage irréversible (enforcement DB)
•	Après committees.status = locked:
–	Interdiction INSERT/UPDATE/DELETE sur committee_members
–	Interdiction UPDATE statut locked → draft
•	Implémentation recommandée: trigger PostgreSQL levant exception si tentative modification
•	Tests automatisés prouvant l'interdiction
3.	Délégation (sans modifier composition)
•	Table committee_delegations (append-only)
–	id, committee_id, member_id
–	delegate_name, delegate_function, delegate_email
–	reason
–	valid_from, valid_to (optionnel)
–	created_at, created_by
•	Règle: délégation ne modifie pas roster, se trace append-only, doit apparaître dans exports PV
4.	Rules engine composition (data-driven)
•	Table committee_composition_rules
–	id, category, threshold_band, rule_json
–	justification_text
•	CommitteeBuilder:
–	Entrée: case.category, case.amount, procurement_method
–	Sortie: composition roles + required + min_level
–	Aucune logique hardcodée non traçable
5.	API (FastAPI)
•	POST create committee (draft) pour case
•	POST set members (draft uniquement)
•	POST lock committee
•	POST add delegation (locked ou draft, sans toucher membres)
•	GET committee details + events + delegations
Tests obligatoires
•	tests/committee/test_committee_lock_prevents_member_update.py (BLOQUANT CI)
•	tests/committee/test_delegation_without_roster_change.py
•	tests/committee/test_composition_rules.py
Definition of Done (bloquante)
•	[ ] LOCK irréversible prouvé par tests
•	[ ] Aucune modification membres post-lock possible (DB trigger + tests)
•	[ ] Délégation possible post-lock sans modifier roster
•	[ ] Événements append-only présents
•	[ ] PV peut afficher composition officielle + délégations
•	[ ] Tests passent en CI
________________________________________
3.9. M-CBA-TEMPLATES — Templates CBA Excel normalisés
Fonction
Créer template canonique CBA Excel.
Ce que ça résout
Standardiser livrable officiel CBA, éviter dérive manuelle.
Lien Constitution
•	Livrables requis (§2.3)
•	Exports (§6.2)
Livrables techniques (obligatoires)
•	Template CBA (.xlsx)
–	Multi-onglets
–	Formules
–	Mise en forme stable
–	Zones réservées aux données injectées
•	Versionnement strict (v1.0, v1.1...)
Tests obligatoires
•	tests/templates/test_cba_template_structure.py
Definition of Done (bloquante)
•	[ ] Template validé sur cas réels
•	[ ] Placeholders complets
•	[ ] Versionnement strict
•	[ ] Tests passent
________________________________________
3.10. M-PV-TEMPLATES — Templates PV Word normalisés
Fonction
Créer template canonique PV Word.
Ce que ça résout
Standardiser livrable officiel PV, éviter dérive manuelle.
Lien Constitution
•	Livrables requis (§2.3)
•	Exports (§6.2)
Livrables techniques (obligatoires)
•	Template PV (.docx)
•	Placeholders:
–	Identifiants case
–	Liste membres comité (officiel)
–	Délégations (si présentes)
–	Scores synthétiques
–	Décision et justification (humaine)
•	Versionnement strict
Tests obligatoires
•	tests/templates/test_pv_template_structure.py
Definition of Done (bloquante)
•	[ ] Template validé sur cas réels
•	[ ] Placeholders complets
•	[ ] Versionnement strict
•	[ ] Tests passent
________________________________________
3.11. M-CBA-GEN — Génération CBA automatisée
Fonction
Générer CBA Excel depuis données Couche A.
Ce que ça résout
Automatiser génération CBA tout en gardant décision humaine.
Lien Constitution
•	Génération (§2.3)
•	INV-1 réduction charge
•	INV-9 fidélité
Livrables techniques (obligatoires)
•	CBAGenerator (openpyxl)
•	Table exports
–	id, case_id, export_type, file_path, sha256, generated_by, generated_at
•	API:
–	POST generate CBA
–	GET list exports
Tests obligatoires
•	tests/exports/test_cba_generation.py
•	tests/exports/test_cba_sha256_integrity.py
Definition of Done (bloquante)
•	[ ] Exports produisent fichiers ouvrables
•	[ ] Hash sha256 stocké
•	[ ] Traçabilité export append-only
•	[ ] Tests passent
________________________________________
3.12. M-PV-GEN — Génération PV automatisée
Fonction
Générer PV Word depuis données Couche A.
Ce que ça résout
Automatiser génération PV tout en gardant décision humaine.
Lien Constitution
•	Génération (§2.3)
•	INV-1 réduction charge
•	INV-9 fidélité
Livrables techniques (obligatoires)
•	PVGenerator (python-docx)
•	API:
–	POST generate PV
–	GET list exports
Tests obligatoires
•	tests/exports/test_pv_generation.py
•	tests/exports/test_pv_committee_display.py (comité officiel + délégations)
Definition of Done (bloquante)
•	[ ] Exports produisent fichiers ouvrables
•	[ ] Hash sha256 stocké
•	[ ] Traçabilité export append-only
•	[ ] Tests passent
________________________________________
3.13. M-PIPELINE-A-E2E — Pipeline Couche A complet + SLA Classe A
Fonction
Tests end-to-end sur documents natifs: "PDF/Excel/Word → extraction → normalisation → scoring → exports".
Ce que ça résout
Prouver que Couche A fonctionne seule et respecte la vitesse.
Lien Constitution
•	SLA Classe A (§7)
•	INV-1 (réduction charge)
•	INV-2 (Couche A autonome)
Livrables techniques (obligatoires)
•	Fixtures réalistes (DAO, offres, annexes)
•	Timers intégrés
•	Rapport performance en CI
Tests obligatoires
•	tests/e2e/test_pipeline_a_end_to_end.py
•	tests/e2e/test_sla_classe_a_60s.py (BLOQUANT CI si > 60s)
Definition of Done (bloquante)
•	[ ] SLA vérifié en CI (seuil défini)
•	[ ] Pipeline complet reproductible
•	[ ] Tests passent
________________________________________
4. Milestones Couche B — Mémoire, Market Signal, Dictionnaire étendu
4.1. M-MARKET-DATA-TABLES — Mercuriale, historique décisions, Market Surveys
Fonction
Créer tables des 3 sources Market Signal.
Ce que ça résout
Structurer données contexte marché.
Lien Constitution
•	Couche B (§3)
•	Market Signal (§3.2)
Livrables techniques (obligatoires)
•	Table mercurials
–	id, item_id, zone, price_min, price_avg, price_max, currency, unit, valid_from, valid_to, source
•	Table decision_history
–	id, case_id, item_id, zone, awarded_price, awarded_supplier, decision_date, decision_type
•	Table market_surveys
–	id, item_id, zone, price, currency, unit, source, collector, collected_at, valid_until
Tests obligatoires
•	tests/market/test_market_data_tables_schema.py
Definition of Done (bloquante)
•	[ ] Schémas stables
•	[ ] Indexes sur item/zone/date
•	[ ] Migrations + tests
•	[ ] Tests passent
________________________________________
4.2. M-MARKET-INGEST — Ingestion mercuriale & auto-feed décisions
Fonction
Ingestion mercuriale + alimentation automatique decision_history après décision.
Ce que ça résout
Alimenter Couche B sans saisie manuelle.
Lien Constitution
•	Couche B (§3)
•	INV-1 (réduction charge)
Livrables techniques (obligatoires)
•	Import mercuriale (CSV/XLSX)
•	Hook post-decision: quand PV finalisé, écrire decision_history
Tests obligatoires
•	tests/market/test_mercurial_import_idempotent.py
•	tests/market/test_decision_auto_feed.py
Definition of Done (bloquante)
•	[ ] Ingestion idempotente
•	[ ] Auto-feed fiable
•	[ ] Audit entries
•	[ ] Tests passent
________________________________________
4.3. M-MARKET-SURVEY-WORKFLOW — Workflow Market Survey terrain
Fonction
Permettre saisie terrain contrôlée.
Ce que ça résout
Structurer cotations terrain.
Lien Constitution
•	Couche B (§3)
•	Market Survey (§3.2)
Règles
•	Minimum 3 cotations par item
•	Validité max 90 jours
•	Zone obligatoire
•	Source/collecteur obligatoire
Livrables techniques (obligatoires)
•	API CRUD market surveys
•	UI minimal: création survey + ajout cotations
Tests obligatoires
•	tests/market/test_survey_validation_min_3.py
•	tests/market/test_survey_freshness_90d.py
Règle bloquante GO production
Ce milestone fait partie du gate GO production: aucun déploiement client n'est autorisé sans Market Survey, Market Signal et Context UI Panel complets et testés.
Definition of Done (bloquante)
•	[ ] Validations strictes
•	[ ] Tests sur fraîcheur
•	[ ] Tests passent
________________________________________
4.4. M-MARKET-SIGNAL-ENGINE — Agrégation 3 sources + règles de priorité
Fonction
Agrégateur Market Signal.
Ce que ça résout
Fournir contexte marché non prescriptif.
Lien Constitution
•	Market Signal (§3.2)
•	INV-3 (non prescriptif)
Livrables techniques (obligatoires)
•	MarketSignalProvider
•	Règles:
–	Priorité mercuriale officielle si fraîche
–	Sinon history
–	Sinon surveys
–	États dégradés (informatifs) sans prescription
Tests obligatoires
•	tests/market/test_market_signal_aggregation.py
•	tests/market/test_market_signal_no_scoring_impact.py (BLOQUANT CI)
Règle bloquante GO production
Ce milestone fait partie du gate GO production: aucun déploiement client n'est autorisé sans Market Survey, Market Signal et Context UI Panel complets et testés.
Definition of Done (bloquante)
•	[ ] Explicabilité: chaque signal indique source(s)
•	[ ] Aucun impact sur scoring (test CI bloquant)
•	[ ] Tests d'agrégation passent
________________________________________
4.5. M-CONTEXT-UI-PANEL — Panneau UI Market Signal (Couche B → Couche A)
Fonction
Panneau latéral "contexte marché".
Ce que ça résout
Afficher contexte sans influencer décision.
Lien Constitution
•	Market Signal (§3.2)
•	INV-3 (non prescriptif)
Livrables techniques (obligatoires)
•	UI affichant:
–	min/avg/max
–	Sources disponibles
–	Fraîcheur
–	État dégradé
•	Garantie technique: lecture seule
Tests obligatoires
•	tests/ux/test_context_panel_read_only.py (BLOQUANT CI)
Règle bloquante GO production
Ce milestone fait partie du gate GO production: aucun déploiement client n'est autorisé sans Market Survey, Market Signal et Context UI Panel complets et testés.
Definition of Done (bloquante)
•	[ ] Panel fonctionne sans influencer scoring
•	[ ] Tests "read only" passent
•	[ ] Tests CI bloquants
________________________________________
4.6. M-DICT-FUZZY-MATCH — Fuzzy matching dictionnaire (items & fournisseurs)
Fonction
Résolution variations écriture.
Ce que ça résout
Améliorer matching automatique.
Lien Constitution
•	Dictionnaire procurement (§2.2)
•	INV-1 (réduction charge)
Livrables techniques (obligatoires)
•	Algos token + levenshtein
•	Seuil configurable
•	Si sous seuil: validation humaine obligatoire + événement append-only
Tests obligatoires
•	tests/dict/test_fuzzy_match_performance.py (< 100ms, BLOQUANT CI)
•	tests/dict/test_fuzzy_match_threshold.py
Definition of Done (bloquante)
•	[ ] Performance < seuil défini
•	[ ] Tests sur cas réels
•	[ ] Aucune "auto-normalisation silencieuse" sous seuil
•	[ ] Tests passent
________________________________________
5. Milestones Transverses — Sécurité, Traçabilité, Performance, CI
5.1. M-SECURITY-CORE — Auth, RBAC, audit_log, rate limiting
Fonction
Sécuriser et tracer.
Ce que ça résout
Posture sécurité technique.
Lien Constitution
•	Sécurité (§5)
•	Audit (§6.3)
•	INV-6 (append-only)
Livrables techniques (obligatoires)
•	JWT access/refresh
•	RBAC 5 rôles: admin, manager, buyer, viewer, auditor
•	Table audit_log append-only
•	Rate limiting (par user + endpoint)
•	Upload validation (magic bytes, taille, whitelist)
Tests obligatoires
•	tests/security/test_jwt_expiration.py
•	tests/security/test_rbac_forbidden_actions.py
•	tests/security/test_rate_limit_uploads.py
•	tests/security/test_magic_bytes_block_exe.py
•	tests/security/test_audit_log_append_only.py (BLOQUANT CI)
Definition of Done (bloquante)
•	[ ] Tests auth/rbac/rate limit passent
•	[ ] Audit log généré sur actions critiques
•	[ ] Interdiction DELETE/UPDATE sur audit_log (trigger + test)
•	[ ] Tests CI bloquants
________________________________________
5.2. M-TRACE-HISTORY — score_history & elimination_log
Fonction
Historiser résultats.
Ce que ça résout
Traçabilité décisions.
Lien Constitution
•	INV-6 (append-only)
•	INV-9 (fidélité au réel)
Livrables techniques (obligatoires)
•	Table score_history append-only
•	Table elimination_log append-only
•	Triggers anti delete/update
Tests obligatoires
•	tests/trace/test_score_history_append_only.py (BLOQUANT CI)
•	tests/trace/test_elimination_log_append_only.py (BLOQUANT CI)
Definition of Done (bloquante)
•	[ ] Prouve historique inviolable
•	[ ] Tests passent
________________________________________
5.3. M-CI-INVARIANTS — Tests CI pour chaque invariant
Fonction
Rendre chaque invariant testable.
Ce que ça résout
Garantir respect invariants Constitution.
Lien Constitution
•	Invariants (§4)
Livrables techniques (obligatoires)
Suite tests/invariants/ couvrant:
•	INV-1: Pipeline document→CBA < 60s
•	INV-2: Couche A autonome (désactiver Couche B, comparer scores)
•	INV-3: Couche B non prescriptive (Market Signal n'influence pas scoring)
•	INV-4: Online-first (pas de mode offline)
•	INV-5: CI verte (bloque merge si rouge)
•	INV-6: Append-only (committee_members post-lock, audit_log, corrections)
•	INV-7: ERP-agnostique (scan imports/endpoints)
•	INV-9: Fidélité au réel (donnée originale conservée)
Tests obligatoires
•	tests/invariants/test_inv_01_pipeline_time.py
•	tests/invariants/test_inv_02_couche_a_standalone.py
•	tests/invariants/test_inv_03_couche_b_non_prescriptive.py
•	tests/invariants/test_inv_06_append_only.py
•	tests/invariants/test_inv_07_erp_agnostic.py
Definition of Done (bloquante)
•	[ ] CI bloque toute violation
•	[ ] Tests passent
________________________________________
5.4. M-MONITORING-OPS — Logs JSON & métriques Prometheus
Fonction
Observabilité SLA et régressions.
Ce que ça résout
Détecter régressions performance.
Lien Constitution
•	SLA (§7)
•	Observabilité
Livrables techniques (obligatoires)
•	Logger JSON
•	Métriques Prometheus:
–	Latence extraction
–	Latence scoring
–	Latence export
–	Latence market signal
•	Endpoint /api/health
Tests obligatoires
•	tests/monitoring/test_health_endpoint.py
•	tests/monitoring/test_prometheus_metrics.py
Definition of Done (bloquante)
•	[ ] Métriques visibles
•	[ ] Seuils d'alerte possibles
•	[ ] Tests passent
________________________________________
5.5. M-DEVOPS-DEPLOY — Docker, CI/CD, santé
Fonction
Déploiement reproductible.
Ce que ça résout
Automatiser déploiement.
Lien Constitution
•	Déploiement (§8)
Livrables techniques (obligatoires)
•	docker compose (app + postgres)
•	GitHub Actions:
–	Tests
–	Coverage
–	Lint
•	Déploiement Railway
•	Healthcheck
Tests obligatoires
•	tests/devops/test_docker_compose_up.py
•	tests/devops/test_healthcheck.py
Definition of Done (bloquante)
•	[ ] Déploiement reproductible
•	[ ] CI bloque merge si rouge
•	[ ] Tests passent
________________________________________
6. Milestones Produit & Terrain — UX, Early adopters, ERP agnostique
6.1. M10-UX-V2 — Interface Couche A complète + Registre dépôt
Fonction
Implémenter flow canonique Couche A:
•	Écran 0: Home (Market Survey sidebar + Workspace)
•	Écran 1: Déclaration intention (document formel / simple / import)
•	Écran 2: Upload + extraction Classe A/B
•	Écran 2bis: Registre dépôt offres (fusion M9, append-only)
•	Écran 3: Configuration comité (draft → LOCK irréversible, délégation possible)
•	Écran 4: Analyse comparative + Market Signal (lecture seule)
•	Écran 5: Export CBA/PV + décision
Ce que ça résout
Workflow complet utilisable.
Lien Constitution
•	UX (§2.4)
•	Comité (§6)
•	Registre dépôt (§6.1)
•	INV-1 (réduction charge)
•	INV-6 (append-only)
Livrables techniques (obligatoires)
1.	Table submission_deposits (registre dépôt)
•	Rôle: tracer chaque dépôt (physique/électronique) append-only
•	Champs:
–	id, case_id, supplier_name, supplier_phone
–	deposit_timestamp (réel, extrait ou saisi)
–	deposit_method: physical, email, portal, courier
–	deposited_by, document_count, metadata (JSONB)
–	received_by, received_at
2.	Endpoints registre dépôt
•	GET /ux/workspace/deposit-registry/{case_id}: liste dépôts + statut délai
•	POST /ux/workspace/deposit-registry/{case_id}: enregistrer dépôt (append-only)
•	POST /ux/workspace/deposit-registry/{case_id}/auto-extract: extraction timestamps depuis documents
3.	Écrans UX complets (flow 3 écrans canoniques + registre + comité)
Tests obligatoires
•	tests/ux/test_submission_deposits_append_only.py (BLOQUANT CI)
•	tests/ux/test_committee_lock_ui.py
•	tests/ux/test_workflow_end_to_end.py
Definition of Done (bloquante)
•	[ ] Workflow complet utilisable
•	[ ] Comité LOCK irréversible appliqué
•	[ ] Registre dépôt append-only
•	[ ] Tests passent
________________________________________
6.2. M-UX-TEST-TERRAIN — Tests utilisateurs & T_DMS
Fonction
Mesurer gains réels.
Ce que ça résout
Preuve efficacité terrain.
Lien Constitution
•	Validation produit (§2.4)
Livrables techniques (obligatoires)
•	Protocole test
•	Métriques:
–	T_DMS vs T_manuel
–	Nombre corrections
–	Taux "retour Excel"
•	Rapport pilot
Tests obligatoires
•	tests/ux/test_user_acceptance.py
Definition of Done (bloquante)
•	[ ] Preuve efficacité terrain
•	[ ] Rapport pilot finalisé
________________________________________
6.3. M-ERP-AGNOSTIC-CHECK — Vérification indépendance ERP
Fonction
Garantir neutralité ERP.
Ce que ça résout
Respect INV-7.
Lien Constitution
•	INV-7 (ERP-agnostique)
Livrables techniques (obligatoires)
•	Scans dépendances
•	Tests
•	Documentation intégration par exports/API
Tests obligatoires
•	tests/invariants/test_inv_07_erp_agnostic.py (BLOQUANT CI)
Definition of Done (bloquante)
•	[ ] Aucune dépendance ERP imposée
•	[ ] Tests passent
________________________________________
6.4. M-PILOT-EARLY-ADOPTERS — Déploiement pilote & NPS
Fonction
Pilote production contrôlé.
Ce que ça résout
Validation adoption.
Lien Constitution
•	Validation produit (§2.4)
Livrables techniques (obligatoires)
•	Déploiement pilote
•	Suivi adoption
•	NPS
•	Backlog correctifs
Definition of Done (bloquante)
•	[ ] Adoption validée
•	[ ] Stabilité démontrée
•	[ ] NPS ≥ seuil défini
________________________________________
7. Definition of Done (commune à tous les milestones)
Un milestone est DONE si et seulement si:
1.	Code:
o	[ ] Code écrit, committé, pushé
o	[ ] Respect conventions (PEP8, type hints, docstrings)
o	[ ] Pas de code mort, pas de TODOs en production
2.	Tests:
o	[ ] Tests unitaires écrits et passants
o	[ ] Tests d'intégration si applicable
o	[ ] Coverage ≥ seuil défini par phase
o	[ ] Tests invariants passants (si applicable)
3.	Documentation:
o	[ ] Docstrings sur fonctions/classes publiques
o	[ ] README à jour si nouveau module
o	[ ] Exemples d'usage si API publique
4.	Sécurité:
o	[ ] Validation inputs
o	[ ] Pas de secrets hardcodés
o	[ ] Audit log si action sensible
5.	Migrations:
o	[ ] Migration Alembic créée
o	[ ] Migration testée (up + down)
o	[ ] Migration réversible si possible
6.	Rollback:
o	[ ] Stratégie rollback documentée
o	[ ] Feature flags si nécessaire
7.	CI:
o	[ ] CI verte (tous tests passent)
o	[ ] Lint/format OK
o	[ ] Coverage validée
8.	Review:
o	[ ] PR créée, reviewée, approuvée
o	[ ] Commentaires adressés
o	[ ] Mergée dans branche cible
________________________________________
8. Ordre d'exécution recommandé (séquence stricte)
Ordre	ID Milestone	Phase
1	M-DOCS-CORE	0
2	M-EXTRACTION-ENGINE	0
3	M-EXTRACTION-CORRECTIONS	0
4	M-CRITERIA-TYPING	1
5	M-NORMALISATION-ITEMS	1
6	M-SCORING-ENGINE	2
7	M-SCORING-TESTS-CRITIQUES	2
8	M-COMMITTEE-CORE	2
9	M-CBA-TEMPLATES	3
10	M-PV-TEMPLATES	3
11	M-CBA-GEN	3
12	M-PV-GEN	3
13	M-PIPELINE-A-E2E	3
14	M-SECURITY-CORE	4
15	M-TRACE-HISTORY	4
16	M-CI-INVARIANTS	4
17	M-MARKET-DATA-TABLES	5
18	M-MARKET-INGEST	5
19	M-MARKET-SURVEY-WORKFLOW	5
20	M-MARKET-SIGNAL-ENGINE	5
21	M-CONTEXT-UI-PANEL	5
22	M-DICT-FUZZY-MATCH	5
23	M-MONITORING-OPS	6
24	M-DEVOPS-DEPLOY	6
25	M10-UX-V2	7
26	M-UX-TEST-TERRAIN	7
27	M-ERP-AGNOSTIC-CHECK	7
28	M-PILOT-EARLY-ADOPTERS	7

________________________________________
9. Gates GO/NO-GO
9.1. Gate Alpha Interne
Conditions:
•	[ ] M-PIPELINE-A-E2E DONE
•	[ ] M-SECURITY-CORE DONE
•	[ ] M-CI-INVARIANTS DONE
•	[ ] Coverage ≥ 60%
•	[ ] CI verte
•	[ ] Invariants INV-1, INV-2, INV-6, INV-9 testés et passants
Décision: GO alpha interne / NO-GO
9.2. Gate Pilote Terrain
Conditions:
•	[ ] M10-UX-V2 DONE
•	[ ] M-UX-TEST-TERRAIN DONE
•	[ ] M-DEVOPS-DEPLOY DONE
•	[ ] Coverage ≥ 75%
•	[ ] Tous invariants testés et passants
•	[ ] SLA Classe A validé
Décision: GO pilote terrain / NO-GO
9.3. Gate Production Externe (BLOQUANT MARKET SIGNAL)
Conditions (toutes obligatoires):
•	[ ] M-MARKET-SURVEY-WORKFLOW DONE
•	[ ] M-MARKET-SIGNAL-ENGINE DONE
•	[ ] M-CONTEXT-UI-PANEL DONE
•	[ ] M-PILOT-EARLY-ADOPTERS DONE
•	[ ] M-ERP-AGNOSTIC-CHECK DONE
•	[ ] Coverage ≥ 85%
•	[ ] NPS pilote ≥ seuil défini
•	[ ] Tous invariants testés et passants
•	[ ] SLA Classe A et B validés
Règle opposable: Aucun déploiement client n'est autorisé sans Market Survey, Market Signal et Context UI Panel complets et testés.
Décision: GO production externe / NO-GO
________________________________________
10. Règle spéciale Comité (rappel opposable)
Cette règle est opposable et non négociable:
1.	Tant que le comité est en draft, on peut saisir les membres.
2.	Dès que le comité passe en locked:
o	La composition (liste de membres) est immuable.
o	Toute tentative de modification doit échouer au niveau base de données.
o	Enforcement: trigger PostgreSQL + tests automatisés.
3.	La délégation est autorisée:
o	Elle ne modifie pas le roster.
o	Elle se trace append-only dans committee_delegations.
o	Elle doit apparaître dans les exports PV.
Test bloquant CI: tests/committee/test_committee_lock_prevents_member_update.py
________________________________________
11. Versionnement & Gouvernance
11.1. Versionnement du plan
•	Ce plan est en version V3.3.2.
•	Toute modification = nouvelle version (V3.3.3, V3.4.0...).
•	Nouvelle version impose:
o	Nouvel ADR (ADR-000X)
o	Nouveau freeze (docs/freeze/vX.Y.Z/)
o	Validation CTO explicite
11.2. Traçabilité Git
•	Ce plan sera freezé avec:
o	Tag Git: v3.3.2-freeze
o	SHA256: calculé et inscrit dans FREEZE_MANIFEST.md
o	Copie immuable dans docs/freeze/v3.3.2/
11.3. Opposabilité
•	Ce plan est CANONIQUE et OPPOSABLE.
•	Tout agent (humain ou IA) doit le respecter.
•	Aucun contournement autorisé sans ADR + validation CTO.
________________________________________
12. Références
•	Constitution DMS V3.3.2: docs/CONSTITUTION_DMS_V3.3.2.md
•	ADR-0001: docs/adrs/ADR-0001.md
•	Invariants: docs/INVARIANTS.md
•	Sécurité: docs/SECURITY.md
•	SLA: docs/PERFORMANCE_SLA.md
•	Architecture: docs/ARCHITECTURE.md
•	Database Schema: docs/DATABASE_SCHEMA.md
•	API Reference: docs/API_REFERENCE.md
________________________________________
FIN DU PLAN D'EXÉCUTION MILESTONES V3.3.2
Ce document est CANONIQUE, OPPOSABLE, et FREEZABLE.
