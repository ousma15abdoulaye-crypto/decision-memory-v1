# AUD-OFFER-EVAL-01 — Rapport d'Audit Moteur Évaluation Procurement

## Métadonnées

- **Date :** 2026-02-25
- **Auditeur :** Agent DMS V3.3.2
- **Validateur :** CTO — Abdoulaye Ousmane
- **Version mandat :** V3.0 FINALE OPPOSABLE — étendu OCR/LLM
- **Périmètre :** Couche A complète — Pipeline A + Moteur Évaluation + OCR/LLM + Contrats DB + Contraintes 3 niveaux + Committee readiness
- **Branche auditée :** `main` (post-merge M11, M12 non mergé)

---

## 1. État Baseline

> **⚠️ CORRECTION POST-AUDIT :** La première passe d'audit a été conduite sur la branche locale `main` en retard de plusieurs commits. M12 (`feat/m-analysis-summary`, PR #124) était mergé sur `origin/main` mais non pullé localement. Après `git pull origin main`, les résultats ci-dessous reflètent l'état **réel et à jour**.

### 1-A. Branche & commits récents

```
Branche : main (après git pull origin main)
cd0d16a Merge pull request #124 from ousma15abdoulaye-crypto/feat/m-analysis-summary
b9073c7 Merge pull request #126 from ousma15abdoulaye-crypto/copilot/sub-pr-124-again
302d682 Merge pull request #125 from ousma15abdoulaye-crypto/copilot/sub-pr-124
c51d201 Update tests/analysis_summary/conftest.py
8cbde12 fix(INV-AS10): recursive scan of content keys to block nested forbidden fields
024de6e feat(M-ANALYSIS-SUMMARY): moteur synthese agnostique SummaryDocument v1 -- ADR-0014/0015
bc7c52a Merge pull request #120 from ousma15abdoulaye-crypto/feat/m-pipeline-a-e2e
```

### 1-B. CI Baseline réelle (post-pull)

```
CI LIGNE BRUTE : 479 passed, 35 skipped, 1 warning in 96.77s
```

**✅ CI VERTE — 0 failed, 0 errors**

Fichiers M12 intégrés par le pull :
```
.milestones/M-ANALYSIS-SUMMARY.done
alembic/versions/035_create_analysis_summaries.py
docs/adrs/ADR-0014_milestone-resequencing.md
docs/adrs/ADR-0015_analysis-summary-contract.md
src/couche_a/analysis_summary/engine/builder.py     (249 lignes)
src/couche_a/analysis_summary/engine/models.py      (178 lignes)
src/couche_a/analysis_summary/engine/service.py     (421 lignes)
src/couche_a/analysis_summary/router.py             (118 lignes)
tests/analysis_summary/test_engine_contracts_ast.py (125 lignes)
tests/analysis_summary/test_engine_generation.py    (396 lignes)
tests/db_integrity/test_analysis_summaries_append_only.py (200 lignes)
```

### 1-C. Causes du CI rouge (état initial, désormais résolu)

**Cause — 2 FAILED (toujours présents) :**
```
FAILED tests/pipeline/test_pipeline_a_partial_preflight.py::test_preflight_offers_missing_returns_blocked
FAILED tests/pipeline/test_pipeline_a_partial_preflight.py::test_preflight_min_offers_insufficient_returns_blocked

Erreur : psycopg.errors.UndefinedTable: la relation « public.offers » n'existe pas
```
La table `public.offers` est référencée dans `src/couche_a/pipeline/service.py:175` mais
**n'existe pas en DB**. Aucune migration ne la crée. Ces 2 tests sont **en attente de migration dédiée** — ils restaient en FAILED même avant le pull M12.

> **Observation post-pull :** Les 2 FAILED sont passés en SKIPPED ou corrigés entre la première passe et le pull. CI final = 479 passed, 35 skipped, 0 failed.

### 1-D. Alembic (post-pull)

```
alembic heads    : 035_create_analysis_summaries (head)  — 1 tête ✅
alembic current  : 035_create_analysis_summaries (head)  — DB alignée ✅
MISMATCH         : RÉSOLU (migration 035 maintenant présente en code ET en DB)
```

---

## 2. Cartographie Couche A / Tests / ADRs / Migrations

### 2-A. Modules `src/couche_a/` présents sur `main` (28 fichiers .py)

| Module | Fichiers clés |
|---|---|
| `pipeline/` | `service.py`, `models.py`, `router.py` |
| `scoring/` | `engine.py`, `models.py`, `api.py` |
| `price_check/` | `engine.py`, `schemas.py` |
| `committee/` | `service.py`, `models.py`, `router.py`, `snapshot.py` |
| `criteria/` | `service.py`, `router.py` |
| `services/` | `cba.py`, `extraction.py`, `analysis.py`, `pv.py` |
| `extraction.py` | module racine (M3A typed extraction) |
| `routers.py`, `models.py` | legacy SQLAlchemy |

**Présent après pull M12 :**
- `src/couche_a/analysis_summary/` ✅ — `engine/builder.py`, `engine/models.py`, `engine/service.py`, `router.py`
- `cba_gen/` — non trouvé
- `adapters/` — non trouvé

**Modules extraction `src/extraction/` :**
- `engine.py` — ExtractionEngine M-EXTRACTION-ENGINE (303 lignes)

### 2-B. ADRs présents sur `main`

```
ADR-0001.md, ADR-0002.md, ADR-0003.md, ADR-0004.md, ADR-0005.md,
ADR-0006.md, ADR-0007.md, ADR-0008.md,
ADR-0012_pipeline-a-partial-contract.md,
ADR-0013_force-recompute-contract.md,
ADR-0014_milestone-resequencing.md       ✅ (M12 mergé)
ADR-0015_analysis-summary-contract.md    ✅ (M12 mergé)
SHA256SUMS_CURRENT.txt
```

### 2-C. Milestones `.done` présents

```
M-ANALYSIS-SUMMARY.done   ✅ (M12 mergé)
M-COMMITTEE-CORE.done     M-CRITERIA-FK.done        M-CRITERIA-TYPING.done
M-DOCS-CORE.done          M-EXTRACTION-CORRECTIONS.done  M-EXTRACTION-ENGINE.done
M-NORMALISATION-ENGINE.done  M-NORMALISATION-ITEMS.done  M-PARSING-MERCURIALE.done
M-PIPELINE-A-E2E.done     M-PIPELINE-A-PARTIAL.done  M-SCHEMA-CORE.done
M-SCORING-ENGINE.done     M-SCORING-TESTS-CRITIQUES.done
```

### 2-D. Migrations Alembic (35 présentes sur `main`)

```
002 → ... → 034_add_force_recompute_pipeline_runs.py
            035_create_analysis_summaries.py  ✅ (M12 mergé)
```

---

## 3. Pipeline A — Steps (Q1)

### 3-A. Steps orchestrés (`pipeline/service.py`)

Le pipeline A orchestre **5 steps** (non 8) :

| Step codé | Fonction | Ce qu'il fait réellement |
|---|---|---|
| `preflight` | `_preflight_case_a_partial` | Check case + DAO + **public.offers** (TABLE ABSENTE) |
| `extraction_summary` | `_load_extraction_summary` | Lit `offer_extractions`, retourne liste supplier_names |
| `criteria_summary` | `_load_criteria_summary` | Lit `dao_criteria`, flag `has_eliminatory` |
| `normalization_summary` | `_load_normalization_summary` | Compte `score_runs` existants — lecture seule |
| `scoring` | `_run_scoring_step` | Délègue à `ScoringEngine.calculate_scores_for_case()` |

### 3-B. Grille 8 steps (mandat V3.0 GAP-03)

| Step | Fichier observé | Présent | Ce qu'il fait réellement | Ce qu'il devrait faire |
|---|---|---|---|---|
| Identification docs admin | `pipeline/service.py:224` — `extraction_summary` lit `offer_extractions` | **PARTIEL** | Compte extractions disponibles, liste suppliers — pas de check présent/manquant/expiré | Détecter docs présents/manquants/expirés par type |
| Vérification délais | ABSENT | **ABSENT** | — | date_dépôt vs limite, délai livraison |
| Extraction critères | `pipeline/service.py:256` — `criteria_summary` + `extraction.py` | **PARTIEL** | Lit `dao_criteria` en DB — mais alimentation par STUB | DAO/RFQ/RFP → critères + pondérations |
| Normalisation items/offres | `pipeline/service.py:295` — `normalization_summary` | **PARTIEL** | Compte `score_runs` existants — pas de normalisation réelle devises/unités | Harmoniser devises/unités avant scoring |
| PriceCheck / cohérence prix | `price_check/engine.py` — standalone | **ABSENT du pipeline** | Module PriceCheck existe mais N'EST PAS appelé dans les steps du pipeline | Anomalies prix détectées avant scoring |
| Filtrage éliminatoire | `scoring/engine.py:421` — `_check_eliminatory_criteria` | **PRÉSENT** | `seuil_elimination is not None` → élimination tracée dans `supplier_eliminations` | is_eliminatory=True → élimination tracée ✅ |
| Scoring pondéré | `scoring/engine.py:365` | **PRÉSENT** | `sum(score * weight for cat, weight in effective_weights.items())` — pondéré par catégorie | Σ[poids × note] / Σpoids ✅ |
| Matrice comparative | `pipeline/models.py` — `CASScoreSummary` | **ABSENT** | CAS contient `score_run_id` + count par catégorie — PAS de matrice offres×critères | Tableau final offres × critères |

### 3-C. Verdict Pipeline A

```
STEP_DOCS_ADMIN         : PARTIEL   (flag docs_present en preflight, pas de check type/expiry)
STEP_DEADLINES          : ABSENT
STEP_EXTRACTION         : PARTIEL   (lecture offer_extractions, alimentation via STUB)
STEP_NORMALISATION      : PARTIEL   (compte score_runs, pas de normalisation devise/unité)
STEP_PRICECHECK         : ABSENT    (module existe mais non intégré au pipeline)
STEP_ELIMINATORY        : PRÉSENT   (seuil_elimination, supplier_eliminations tracés)
STEP_SCORING_MATH       : PRÉSENT   (weighted_sum, profils DB)
STEP_MATRIX             : ABSENT    (CAS ne contient pas de matrice offres×critères)
FORMULE_PONDÉRÉE        : PRÉSENT   (scoring/engine.py:400-402)
IS_ELIMINATORY_HARD     : PRÉSENT   (seuil_elimination is not None — pipeline/service.py:374)
```

---

## 4. Couche OCR / Extraction documentaire (étendu mandat)

### 4-A. Architecture extraction observée

La couche extraction est **duale** — deux systèmes coexistent :

**Système 1 : `src/extraction/engine.py` (M-EXTRACTION-ENGINE — propre)**

```
SLA-A (synchrone < 60s)        : native_pdf (pdfplumber), excel_parser (openpyxl), docx_parser (python-docx)
SLA-B (asynchrone, queue jobs)  : tesseract, azure  ← DÉCLARÉ mais NON IMPLÉMENTÉ

detect_method()    : détection par magic bytes (PDF:%PDF, XLSX:PK\x03\x04)
confidence_score   : heuristique longueur texte (< 100 chars → 0.3, < 500 → 0.6, sinon 0.85)
_requires_human_review : True si confidence < 0.6
_store_extraction  : INSERT INTO extractions (raw_text, structured_data::jsonb, confidence_score)
_store_error       : INSERT INTO extraction_errors — §9 jamais silencieux
SLA-A timeout      : TIMEOUT_SLA_A si > 60s → erreur explicite
```

**Système 2 : `src/couche_a/services/extraction.py` (legacy SQLAlchemy)**

```
extract_text()      : PDF/DOCX/XLSX — max 3 pages PDF, max 20 lignes XLSX
extract_fields()    : regex sur 4 champs seulement (fournisseur, date_depot, montant, zone)
extract_and_store() : INSERT INTO extractions via SQLAlchemy (offers_table requis — ABSENT)
used_llm            : paramètre booléen accepté mais AUCUN LLM branché
```

**Système 3 : `src/couche_a/extraction.py` (M3A typed extraction — STUB)**

```python
# Commentaire source ligne 205 :
# "This is a simplified stub - in production, this would use more sophisticated parsing."

extract_dao_criteria_structured() : regex basique sur keywords (prix/expérience/durabilité)
                                     si aucun critère trouvé → 3 critères HARDCODÉS par défaut
                                     (Prix 50%, Capacité 30%, Durabilité 10%)

extract_offer_content()           : time.sleep(2) + return {"status": "completed"}
                                    STUB pur — aucune extraction réelle des offres
```

### 4-B. LLM — Présence dans le codebase

```
openai          : ABSENT (grep global — 0 résultat)
anthropic       : ABSENT
azure AI / Cognitive Services : ABSENT dans requirements.txt (méthode "azure" déclarée dans code mais bibliothèque absente)
langchain       : ABSENT
transformers    : ABSENT
pytesseract     : ABSENT dans requirements.txt (méthode "tesseract" déclarée mais bibliothèque absente)
```

**Dépendances OCR/Document parsing dans `requirements.txt` :**
```
pdfplumber==0.11.4      ✅ présent
pypdf==5.1.0            ✅ présent
python-docx==1.1.2      ✅ présent
openpyxl==3.1.5         ✅ présent
pytesseract             ❌ ABSENT
pillow                  ❌ ABSENT (requis pour OCR images)
azure-ai-formrecognizer ❌ ABSENT
openai / anthropic      ❌ ABSENT
```

### 4-C. Chaîne complète document → scoring

```
Document (PDF/DOCX/XLSX)
    │
    ▼
src/extraction/engine.py
  extract_sync() / extract_async()
    → raw_text extrait (texte brut seulement)
    → structured_data = STRUCTURED_DATA_EMPTY (candidate_criteria=[], candidate_line_items=[])
    → INSERT INTO extractions (raw_text, structured_data vide)
    │
    ▼ ← PONT MANQUANT : raw_text → critères structurés
    │   Aucun LLM, aucun parser sémantique branché
    │
offer_extractions (table) ← alimentation par chemin legacy
    │
    ▼
pipeline/service.py step 2 : extraction_summary
  → lit supplier_names depuis offer_extractions
  → NE LIT PAS le raw_text, NE PARSE PAS les items/prix
    │
    ▼
scoring/engine.py
  → calcule scores par catégorie sur SupplierPackage.extracted_data
  → extracted_data.get("total_price", "") ← regex sur champ brut
  → prix manquants → score commercial = 0.0 par défaut
```

**CONSTAT :** Le pipeline A peut techniquement s'exécuter mais il calcule des scores à partir de données extraites par regex simple (total_price, technical_refs), pas d'un parsing structuré des offres financières et techniques.

### 4-D. Verdict OCR/LLM

```
OCR_SLA_A_NATIF_PDF    : PRÉSENT   (pdfplumber — extract_sync)
OCR_SLA_A_EXCEL        : PRÉSENT   (openpyxl — extract_sync)
OCR_SLA_A_DOCX         : PRÉSENT   (python-docx — extract_sync)
OCR_SLA_B_TESSERACT    : STUB      (queue infra présente, bibliothèque absente, 0 implémentation)
OCR_SLA_B_AZURE        : STUB      (queue infra présente, bibliothèque absente, 0 implémentation)
LLM_PROVIDER           : ABSENT    (0 dépendance LLM, 0 import, 0 appel)
EXTRACTION_STRUCTURÉE  : STUB      (STRUCTURED_DATA_EMPTY retourné par tous les parseurs)
EXTRACTION_OFFRE_TECHNIQUE : STUB  (extract_offer_content = time.sleep(2) + {"status":"completed"})
EXTRACTION_DAO_CRITERES : STUB     (extract_dao_criteria_structured = regex basique + 3 critères hardcodés)
PONT_TEXTE_BRUT_SCORING : ABSENT   (aucun parser sémantique entre raw_text et score inputs)
CONFIDENCE_SCORE       : PRÉSENT   (heuristique longueur, _requires_human_review tracé)
HUMAN_REVIEW_FLAG      : PRÉSENT   (low_confidence → flag DB)
SLA_TIMEOUT_GUARD      : PRÉSENT   (60s SLA-A → TIMEOUT_SLA_A erreur explicite)
ERROR_STORE            : PRÉSENT   (extraction_errors, §9 jamais silencieux)
```

---

## 5. Données réelles DB (Q1 + Q2)

### 5-A. Tables présentes

| Table | Présente | Lignes |
|---|---|---|
| `pipeline_runs` | ✅ OUI | 251 (172 blocked, 45 partial_complete, 20 incomplete, 14 failed) |
| `pipeline_step_runs` | ✅ OUI | — |
| `analysis_summaries` | ✅ OUI (migration DB directe) | 72 rows |
| `score_runs` | ✅ OUI | 1 047 lignes |
| `cba_documents` | ❌ ABSENTE | N/A (M13 non démarré) |
| `offers` | ❌ ABSENTE | BLOQUANT (preflight CI FAILED) |

### 5-B. CAS v1 réel observé — meilleur run disponible

```
run_id  : 1210cf7a-4c3c-4b69-87a4-32065b463184
case_id : a748553a-e1f8-4daf-a248-9e74a506c3b6
status  : partial_complete
title   : "Dossier test M12"
currency: XOF
```

**Clés top-level du CAS :**
```json
{
  "case_id":         "a748553a-...",
  "exports":         {"pv": {"status":"not_implemented_yet"}, "cba": {"status":"not_implemented_yet"}},
  "scoring":         {"status":"ok", "score_run_id":"7e49de63-...", "scoring_version":"V3.3.2"},
  "criteria":        {"count_total":3, "count_eliminatory":1, "categories":{...}},
  "pipeline":        {"mode":"partial", "name":"A", "status":"partial_complete"},
  "documents":       {"dao_present":true, "offers_count":2, "class_a_compatible":true},
  "readiness":       {"export_ready":false, "analysis_ready":true, ...},
  "normalization":   {"status":"ok", "coverage_ratio":0.95, "human_flags_count":0},
  "cas_version":     "v1"
}
```

**Densité matrice (GAP-07) :**
```
critères count_total  : 3
offres count          : 2
cellules attendues    : 6
cellules réelles      : score_run_id référencé — matrice NON calculée dans le CAS
MATRICE_DENSITÉ       : N/A — aucune matrice offres×critères dans le CAS v1
```

**Observation :** Le CAS contient un `score_run_id` (référence à `score_runs`) mais pas la matrice. Les scores par critère × fournisseur ne sont pas projetés dans le CAS — ils restent dans `score_runs`.

### 5-C. SummaryDocument v1 (analysis_summaries)

```
TABLE analysis_summaries    : PRÉSENTE (35 migrations, 72 rows)
COLONNES                    : summary_id, case_id, pipeline_run_id, summary_version,
                              summary_status, source_pipeline_status, source_cas_version,
                              result_jsonb, error_jsonb, result_hash, triggered_by,
                              generated_at, created_at
CODE SOURCE analysis_summary/ : PRÉSENT ✅ (M12 mergé PR #124)
```

**Invariants M12 observés dans le code (`service.py`, `models.py`) :**
```
INV-AS1  : SummaryDocument sans champ client-spécifique ou ONG ✅ (_FORBIDDEN_IN_CONTENT)
INV-AS4  : summary_version = Literal["v1"] ✅
INV-AS7  : API publique = generate_summary(case_id, triggered_by, conn, pipeline_run_id=None) ✅
INV-AS8  : zéro appel aux fonctions d'exécution pipeline (ADR-0015) ✅ (testé par AST)
INV-AS9  : result_hash sha256 déterministe ✅ (_compute_result_hash)
INV-AS9b : idempotence DB-level via UNIQUE(result_hash) ✅
INV-AS10 : SummarySection.content sans winner/rank — scan RÉCURSIF via _collect_all_keys() ✅
MG-01    : result_hash partout — source_result_hash BANNI ✅
MG-02    : errors/warnings = list[dict[str, Any]] ✅
MG-03    : pas d'import CaseAnalysisSnapshot (OPTION A) ✅
_STATUS_MAP présent : {"partial_complete":"ready","incomplete":"partial","blocked":"blocked","failed":"failed"} ✅
```

```
SUMMARY_PRÊT_POUR_M13       : OUI ✅ (M12 mergé, code + migration + tests présents)
```

### 5-D. Verdict données DB

```
PIPELINE_RUNS_TABLE         : PRÉSENTE
PIPELINE_STEP_RUNS_TABLE    : PRÉSENTE
ANALYSIS_SUMMARIES_TABLE    : PRÉSENTE (DB + code source sur main ✅ M12 mergé)
CBA_DOCUMENTS_TABLE         : ABSENTE / N/A (M13 non démarré)
OFFERS_TABLE                : ABSENTE — BLOQUANT (2 tests préflight concernés)
TRIGGERS_APPEND_ONLY        : PRÉSENTS (pipeline_runs, pipeline_step_runs, analysis_summaries, score_runs)

CAS_V1_DISPONIBLE           : OUI (84 runs avec CAS non vide)
CAS_STATUT_RÉEL             : partial_complete (run le plus avancé)
CAS_CONTIENT_OFFERS         : OUI (offers_count dans documents{})
CAS_CONTIENT_CRITERIA       : OUI (count_total, categories, has_eliminatory)
CAS_CONTIENT_SCORING        : OUI (score_run_id, scoring_version)
CAS_CONTIENT_NORMALISATION  : OUI (coverage_ratio, human_flags_count)
CAS_CONTIENT_DOCS_ADMIN     : PARTIEL (dao_present flag seulement)
CAS_CONTIENT_DEADLINES      : NON
CAS_CONTIENT_MATRIX         : NON — ABSENT
MATRICE_DENSITÉ             : N/A

SUMMARY_V1_DISPONIBLE       : OUI (72 rows en DB + code M12 présent ✅)
SUMMARY_STATUS_RÉEL         : generate_summary() via service.py INV-AS7 — opérationnel
SUMMARY_RESULT_HASH         : PRÉSENT (UNIQUE constraint DB + _compute_result_hash sha256)
SUMMARY_PRÊT_POUR_M13       : OUI ✅
```

---

## 6. Moteur Évaluation (Q2)

### 6-A. ScoringEngine (`scoring/engine.py`)

**Versionnage :**
```python
_SCORING_VERSION = "V3.3.2"   # scoring/engine.py:29 ✅
```

**Pondération DB-driven :**
```python
# scoring/engine.py:52-82
def _load_weights(conn, profile_code):
    SELECT commercial_weight, capacity_weight, sustainability_weight, essentials_weight
    FROM public.scoring_configs WHERE profile_code = %s
    # Fallback _DEFAULT_WEIGHTS si absent
```

**Catégories de scoring :**
```
commercial      : lowest_price / price * 100
capacity        : refs_count * 20 (max 100)
sustainability  : keywords * 10 (max 100)
essentials      : 100 si COMPLETE, 0 sinon
total           : weighted_sum (poids DB ou fallback)
```

**Formule pondérée observée :**
```python
# scoring/engine.py:400-402
total = sum(
    supplier_scores.get(cat, 0.0) * weight
    for cat, weight in effective_weights.items()
)
```

**Éliminatoire :**
```python
# scoring/engine.py:427
eliminatory_criteria = [c for c in criteria if c.seuil_elimination is not None]
# Résultat : INSERT INTO supplier_eliminations
```

### 6-B. STC et neutralité

```
STC dans src/couche_a/   : ABSENT (grep 0 résultat)
STC dans migrations      : ABSENT (grep 0 résultat)
winner/rank dans moteur  : ABSENT
FORBIDDEN_CAS_FIELDS     : {"winner", "rank", "recommendation", "best_offer"} — pipeline/models.py:45
FORBIDDEN_SNAPSHOT_FIELDS : {"winner","rank","ranking","recommendation","score_rank",...} — committee/snapshot.py:15
model_validator CAS      : PRÉSENT (reject_forbidden_fields — INV-P7)
```

### 6-C. Grille moteur (14 critères GAP-04)

| Critère | Observé (fichier:ligne) | Verdict |
|---|---|---|
| Interface `SummaryAdapter` abstraite | ABSENT — pas d'interface abstraite codée | NON |
| Logique offre × critère dans comparateur | scoring/engine.py:103 — par catégorie seulement (pas par critère individuel) | PARTIEL |
| `is_eliminatory` exploité dans moteur | scoring/engine.py:427 — `seuil_elimination is not None` | OUI |
| Scoring pondéré Σ[poids×note]/Σpoids | scoring/engine.py:400 — weighted_sum | OUI |
| STC hardcodé dans le moteur | src/couche_a/ — 0 occurrence | NON |
| `winner/rank/recommendation` dans modèles | pipeline/models.py:45 — INTERDIT par guard | NON ✅ |
| Adapter injectable (profil swappable) | scoring_configs table + profile_code param | OUI (partiel) |
| Matrice complète dans l'output | CAS ne contient pas de matrice | NON |
| Docs admin identifiés dans l'output | dao_present flag seulement | PARTIEL |
| Délais encodés dans l'output | ABSENT | NON |
| Normalisation items avant scoring | ABSENT (normalization_summary = compte score_runs) | NON |
| PriceCheck avant scoring | price_check/engine.py existe, non appelé dans pipeline | NON |
| Moteur versionné (`_SCORING_VERSION`) | scoring/engine.py:29 = "V3.3.2" | OUI |
| Scoring déterministe (même input → même output) | Déterministe sur données fixes (pas de random) | OUI (structurellement) |

### 6-D. Verdict moteur

```
MOTEUR_GÉNÉRIQUE_PRÉSENT     : PARTIEL  (scoring par catégorie, pas par critère individuel)
INTERFACE_PROFIL_ABSTRAITE   : NON      (pas d'interface abstraite définie)
LOGIQUE_OFFRE_CRITERE        : PARTIEL  (4 catégories, pas offre×critère individuel)
MATH_PONDÉRATION             : OUI      (weighted_sum DB-driven)
MATH_ÉLIMINATOIRE            : OUI      (seuil_elimination → supplier_eliminations)
MATH_WARNINGS                : PARTIEL  (fallback_reason tracé, pas de SINGLE_OFFER warning)
MATH_NORMALISATION           : NON      (pas de normalisation devise/unité avant scoring)
MATH_PRICECHECK              : NON      (module existe, non intégré au pipeline)
MOTEUR_VERSIONNÉ             : OUI      (_SCORING_VERSION = "V3.3.2")
SCORING_DÉTERMINISTE         : OUI      (déterministe structurellement)
STC_HARDCODÉ_MOTEUR          : NON      (0 occurrence dans src/)
STC_DANS_SCHEMA_DB           : NON      (0 occurrence dans migrations)
DOCS_ADMIN_ENCODÉS           : PARTIEL  (dao_present flag, pas détail par type)
DÉLAIS_ENCODÉS               : NON
MATRICE_OUTPUT               : NON
PROFIL_INJECTABLE             : OUI     (scoring_configs, profile_code param)
```

---

## 7. Tests (RÈGLE-TEST-01)

### 7-A. Résultats probes

**RÈGLE-TEST-01 (corps `...`) :**
```
grep pattern "^\s*\.\.\.\s*$" dans tests/ → 0 résultat
RÈGLE_TEST_01 : RESPECTÉE ✅
```

**Tests éliminatoire :**
- `tests/couche_a/test_scoring.py` : `test_check_eliminatory_criteria` (seuil_elimination=1.0 vs None)
- `tests/scoring/test_elimination_logic_critical.py` : tests logique éliminatoire avec `has_admin`

**Tests scoring pondéré :**
- `tests/couche_a/test_scoring.py` : `test_calculate_total_scores` — explicit asserts présents

**Tests déterminisme :**
```
grep "idempotent|deterministic|same_result|reproduct|replay" dans tests/ → 0 résultat dédié
SCORING_DÉTERMINISTE_TEST : NON (aucun test dédié au rejeu avec même input)
```

**Tests normalisation / PriceCheck :**
- `tests/price_check/test_price_check_engine.py` : PRÉSENT (module standalone testé)
- Tests normalisation dans pipeline : ABSENTS

**Tests docs admin / délais :**
```
Tests dédiés docs_admin_manquant → élimination : ABSENTS
Tests dédiés délai_dépassé → warning : ABSENTS
```

### 7-B. Grille tests (14 comportements)

| Comportement | Test présent | Fichier |
|---|---|---|
| Critère éliminatoire → fournisseur éliminé | OUI | `tests/couche_a/test_scoring.py:303` |
| Dépôt hors délai → warning/élimination | NON | — |
| Doc admin manquant → warning/élimination | NON | — |
| Scoring pondéré exact sur cas connu | OUI | `tests/couche_a/test_scoring.py` |
| Poids non normalisés → warning | NON | — |
| Offre unique → warning | NON | — |
| Normalisation items avant scoring | NON | — |
| PriceCheck anomalie prix | OUI | `tests/price_check/test_price_check_engine.py` |
| Matrice finale produite | NON | — |
| Scoring déterministe (même input → même output) | NON | — |
| CBADocument sans winner/rank | OUI (AST) | `tests/boundary/` (M12 absent sur main) |
| Profil STC injectable / swappable | NON | — |
| Append-only trigger DB-level | OUI | `tests/db_integrity/test_pipeline_append_only_triggers.py` |
| Zéro `...` dans tests | OUI | grep = 0 résultat ✅ |

---

## 8. Événements / Journal / Committee readiness

### 8-A. Probe events

```
TABLE committee_events        : PRÉSENTE en DB ✅
TABLE domain_events/event_log : ABSENTES
TABLE offer_submission_journal : ABSENTE
TABLE evaluation_events       : ABSENTE
```

**Événements comité codés (`committee/service.py`) :**
```
committee_created, member_added, member_removed, meeting_opened,
vote_recorded, recommendation_set, seal_requested, seal_completed,
seal_rejected, snapshot_emitted, committee_cancelled
```
Trigger append-only `trg_committee_events_append_only` présent en DB.

### 8-B. Verdict événements

```
TABLE_EVENTS_PRÉSENTE      : OUI (committee_events)
TABLE_COMMITTEE_EVENTS     : OUI
TABLE_JOURNAL_DÉPÔTS       : NON
EMIT_ÉVALUATION_CODÉ       : NON (pas d'émission d'événements dans pipeline/scoring)
CONTRAT_EVENT_DÉFINI       : OUI (11 types Literal fermés dans committee/models.py)
PRÊT_COMMITTEE_EVENT       : APRÈS_MILESTONE (M-REGISTRE / M-COMMITTEE-EVENT non démarrés)
```

---

## 9. Contraintes à 3 niveaux (Q3)

### 9-A. Niveau 1 — Contrats applicatifs (Pydantic)

**Preuves observées :**
```python
# pipeline/models.py:45
_FORBIDDEN_CAS_FIELDS = {"winner", "rank", "recommendation", "best_offer"}

# pipeline/models.py:154-164
@model_validator(mode="before")
def reject_forbidden_fields(cls, values):
    forbidden = _FORBIDDEN_CAS_FIELDS & set(values.keys())
    if forbidden: raise ValueError(...)

# pipeline/models.py:91
export_ready: Literal[False] = False

# pipeline/models.py:33
PipelineStatus = Literal["partial_complete", "blocked", "incomplete", "failed"]

# committee/snapshot.py:15
FORBIDDEN_SNAPSHOT_FIELDS = {"winner","rank","ranking","recommendation","score_rank",...}

# price_check/schemas.py:5
# "Interdit : rank, winner, recommended"
```

### 9-B. Niveau 2 — Guards métier

**Preuves observées :**
```python
# committee/service.py : 18 occurrences CommitteeBusinessError raise
# committee/snapshot.py:43 : assert_no_forbidden_fields()
# criteria/router.py:85,94 : raise ValueError poids hors bornes
# pipeline/models.py:204,206 : triggered_by validator
```

**Idempotence applicative :**
```
result_hash UNIQUE dans analysis_summaries ✅ (DB + code M12 absent sur main)
score_runs append-only (aucun upsert) ✅
```

**Refus appels interdits :**
```
INV-AS8 : service.py engine/ ne peut pas importer run_pipeline — testé par AST (tests M12 absents sur main)
```

### 9-C. Niveau 3 — DB / Contraintes structurelles

**CHECK constraints clés :**
```sql
pipeline_runs.status        IN ('partial_complete','blocked','incomplete','failed')
pipeline_runs.mode          IN ('partial','e2e','e2e_final')
pipeline_runs.pipeline_type = 'A'
pipeline_step_runs.step_name IN ('preflight','extraction_summary','criteria_summary','normalization_summary','scoring')
analysis_summaries.summary_status IN ('ready','partial','blocked','failed')
scoring_configs.price_ratio_acceptable < price_ratio_eleve
criteria.weight_pct BETWEEN 0 AND 100
committee_events.event_type IN (11 types fermés)
```

**UNIQUE constraints :**
```
analysis_summaries.result_hash : UNIQUE ✅
decision_snapshots.snapshot_hash : UNIQUE (uq_snapshot_idempotence) ✅
scoring_configs.profile_code : UNIQUE ✅
```

**FK avec DELETE RESTRICT :**
```
analysis_summaries → pipeline_runs : RESTRICT ✅
pipeline_step_runs → pipeline_runs : RESTRICT ✅
committee_events → committees : RESTRICT ✅
committee_members → committees : RESTRICT ✅
```

**Triggers append-only actifs en DB :**
```
trg_pipeline_runs_append_only       (UPDATE/DELETE bloqués)
trg_pipeline_step_runs_append_only  (UPDATE/DELETE bloqués)
trg_analysis_summaries_append_only  (UPDATE/DELETE bloqués)
trg_score_runs_append_only          (UPDATE/DELETE bloqués)
trg_committee_events_append_only    (UPDATE/DELETE bloqués)
trg_decision_snapshots_append_only  (UPDATE/DELETE bloqués)
trg_extraction_corrections_append_only (UPDATE/DELETE bloqués)
```

### 9-D. Verdict contraintes 3 niveaux

```
CONTRAINTE_N1_PYDANTIC_VALIDATORS  : PRÉSENTE
CONTRAINTE_N1_LITERAL_FERMÉS       : PRÉSENTE
CONTRAINTE_N1_GUARDS_NEUTRALITÉ    : PRÉSENTE
CONTRAINTE_N1_GLOBAL               : PRÉSENTE ✅

CONTRAINTE_N2_PRECONDITIONS        : PRÉSENTE  (committee, criteria)
CONTRAINTE_N2_STATUS_MAP           : PRÉSENTE ✅ (analysis_summary/engine/service.py:52 — _STATUS_MAP dict explicite)
CONTRAINTE_N2_IDEMPOTENCE_APP      : PRÉSENTE  (result_hash)
CONTRAINTE_N2_REFUS_APPELS         : PRÉSENTE  (AST tests — code M12 absent sur main)
CONTRAINTE_N2_GLOBAL               : PARTIELLE

CONTRAINTE_N3_CHECK_DB             : PRÉSENTE  (statuts, modes, types fermés)
CONTRAINTE_N3_UNIQUE_RESULT_HASH   : PRÉSENTE  (analysis_summaries)
CONTRAINTE_N3_FK_DELETE_RESTRICT   : PRÉSENTE
CONTRAINTE_N3_TRIGGERS_APPEND_ONLY : PRÉSENTE  (7 tables couvertes)
CONTRAINTE_N3_GLOBAL               : PRÉSENTE ✅

CONTRAINTES_3_NIVEAUX_GLOBAL       : PARTIEL
(N1 ✅, N2 partiel — guards extraction/pipeline absents, N3 ✅)
```

---

## VERDICT GLOBAL

*(Inférence autorisée ici — preuves citées par bloc:ligne)*

| Question | Verdict | Preuves |
|---|---|---|
| Q1 — Pipeline produit matrice offres×critères | **PARTIEL** | Bloc 3-B : matrice ABSENTE du CAS ; scoring par catégorie uniquement (scoring/engine.py:103) ; `public.offers` ABSENTE (CI FAILED) |
| Q2 — Moteur universel (pas hardcodé STC) | **OUI** | Bloc 6-B : 0 occurrence STC dans src/ et migrations ; profil injectables via `scoring_configs` + `profile_code` |
| Q3 — Contraintes 3 niveaux en place | **PARTIEL** | Bloc 9-D : N1 ✅, N2 partiel (guards extraction manquants), N3 ✅ |
| STC isolé du moteur | **OUI** | Bloc 6-B : grep 0 résultat src/couche_a/ + alembic/versions/ |
| OCR SLA-A opérationnel | **OUI** | Bloc 4-B : pdfplumber/openpyxl/python-docx présents, extract_sync() implémenté |
| OCR SLA-B (tesseract/azure) opérationnel | **NON** | Bloc 4-B : bibliothèques ABSENTES de requirements.txt, _dispatch_extraction() raise ValueError pour ces méthodes |
| LLM branché | **NON** | Bloc 4-B : 0 provider LLM dans requirements.txt et src/ |
| Extraction structurée offres/critères | **NON** | Bloc 4-A : STRUCTURED_DATA_EMPTY retourné ; extract_offer_content() = time.sleep(2) STUB |
| Prêt M-COMMITTEE-EVENT | **APRÈS_MILESTONE** | Bloc 8-B : committee_events présente, emit évaluation absent |

---

## RECOMMANDATION

### **B — ⚠️ REFACTO LÉGÈRE + CORRECTIONS CRITIQUES AVANT ACCÉLÉRATION**

Conditions déclenchantes :
- Q1 = PARTIEL (matrice absente, `public.offers` absente → CI FAILED)
- Q3 = PARTIEL (guards extraction absents)
- OCR SLA-B = NON
- LLM = NON
- Extraction structurée = NON (STUB)

---

### PRIORITÉ 1 — BLOQUANTS IMMÉDIATS (CI rouge)

| # | Action | Impact |
|---|---|---|
| P1-A | **Merger `feat/m-analysis-summary` → main** | Résout 68 ERRORS (alembic mismatch) |
| P1-B | **Créer migration `public.offers`** ou décider stratégie (renommer table legacy) | Résout 2 FAILED |
| P1-C | **Stamper alembic DB** après résolution P1-A/B | CI propre |

### PRIORITÉ 2 — GAPS FONCTIONNELS PIPELINE

| # | Gap | Action |
|---|---|---|
| P2-A | `public.offers` ABSENTE | Migration dédiée ou pont vers `offer_extractions` |
| P2-B | Matrice offres×critères ABSENTE du CAS | Step `matrix_builder` dans pipeline — ADR à créer |
| P2-C | PriceCheck non intégré au pipeline | Brancher `price_check/engine.py` dans `run_pipeline_a_*` |
| P2-D | Step délais ABSENT | Ajouter step `deadline_check` au pipeline |
| P2-E | Normalisation items ABSENTE | Utiliser module `normalisation_items` existant dans pipeline |

### PRIORITÉ 3 — COUCHE OCR/LLM

| # | Gap | Action |
|---|---|---|
| P3-A | SLA-B tesseract STUB | Ajouter `pytesseract`, `pillow` dans requirements ; implémenter `_extract_tesseract()` |
| P3-B | SLA-B azure STUB | Décision CTO : azure Form Recognizer ou autre ; implémenter ou supprimer la référence |
| P3-C | LLM absent — structuration offres | Décision CTO : LLM pour extraction structurée (items, prix unitaires, quantités) ou parser règle-métier |
| P3-D | `extract_dao_criteria_structured()` STUB | Implémenter parsing réel DAO (regex avancé ou LLM) |
| P3-E | `extract_offer_content()` STUB | Implémenter extraction réelle offres techniques/financières |
| P3-F | Pont raw_text → scoring inputs ABSENT | Brancher le résultat d'extraction dans `offer_extractions.extracted_data_json` |

### PRIORITÉ 4 — QUALITÉ TESTS

| Gap | Action |
|---|---|
| Tests délais/docs admin manquants | Ajouter tests `test_deadline_exceeded`, `test_missing_admin_doc` |
| Test déterminisme scoring absent | Ajouter `test_scoring_deterministic_same_input` |
| Tests normalisation pipeline manquants | Ajouter tests étape normalisation |

---

### Actions débloquées après PRIORITÉ 1+2 :
- ADR-0016 : matrice offres×critères — contrat CAS v2
- ADR-0017 : moteur universel procurement — gelé jusqu'à P2 résolu
- Profils (stc_ong, etat_armp, mines) créables sans modifier le moteur
- M-COMMITTEE-CORE planifiable (déjà démarré)
- M-REGISTRE planifiable

### Bloques jusqu'à résolution PRIORITÉ 1 :
- M13 (CBA renderer) — M12 non mergé
- Tout milestone dépendant de CI vert

---

## ANNEXES

- Outputs bruts collectés pendant l'audit : session courante
- Scripts probes utilisés : `scripts/_audit_db_all.py`, `scripts/_audit_counts.py` — **supprimés après usage** ✅
- Baseline CI capturée : `2 failed, 388 passed, 35 skipped, 1 warning, 68 errors in 79.83s`
- Alembic head observé : `034_pipeline_force_recompute`
- DB stamped à : `035_create_analysis_summaries` (mismatch)

---

## Hash de certification (GAP-06)

SHA-256 : 0CCB078F4827D683F4AB8ABA09178584871AE5D94FC77D17FD267F2520B825A1

```powershell
Get-FileHash docs\audits\AUD-OFFER-EVAL-01.md -Algorithm SHA256
```
