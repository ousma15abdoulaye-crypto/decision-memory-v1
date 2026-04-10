# Pipeline Procurement Innovation V5 — Architecture & Coutures

**Date** : 2026-04-10  
**Branche** : `feat/pipeline-v5-complete-integration`  
**Objectif** : M13 doit "**battre un senior**" dans la gestion des procédures

---

## 🎯 Vision Stratégique

M13 = **Moteur de Conformité Réglementaire Déterministe**
- **Input** : M12 (reconnaissance procédure ITT + corpus texte)
- **Output** : Profil réglementaire complet (ComplianceChecklist + EvaluationBlueprint)
- **Niveau** : Expert senior procurement Mali (DGMP) + SCI frameworks
- **Garantie** : Zéro hallucination — configurations YAML auditées

---

## 📐 Architecture Pipeline V5 (Bout-en-Bout)

```
PASS -1 (ZIP → Bundles)
    ↓
BUNDLES ASSEMBLÉS (supplier_bundles + bundle_documents)
    ↓ OCR Mistral
BUNDLE_DOCUMENTS.raw_text
    ↓
╔════════════════════════════════════════════════════════════╗
║  PIPELINE V5 (POST /workspaces/{id}/run-pipeline)         ║
╠════════════════════════════════════════════════════════════╣
║  ÉTAPE 1: extract_offers_from_bundles()                   ║
║    • Concatène bundle_documents.raw_text par bundle        ║
║    • extract_offer_content_async() — LLM structuré         ║
║    • persist_tdr_result_to_db() → offer_extractions        ║
║                                                             ║
║  ÉTAPE 2: build_pipeline_v5_minimal_m12()                  ║
║    • M12Output minimal (ITT + corpus 500k chars)           ║
║    • H1 = regulatory_profile_skeleton (framework + conf)   ║
║                                                             ║
║  ÉTAPE 3: M13 RegulatoryComplianceEngine                   ║
║    ┌──────────────────────────────────────────────────┐   ║
║    │ RegimeResolver → procedure_type (DGMP seuils)   │   ║
║    │ RequirementsInstantiator → gates + validity     │   ║
║    │ ComplianceGateAssembler → checklist per_offer   │   ║
║    │ DerogationAssessor + PrinciplesMapper           │   ║
║    │ M13RegulatoryProfileRepository.save_payload()   │   ║
║    │   → m13_regulatory_profile_versions             │   ║
║    │   Schema: {m13: M13Output, m13b: M13BHooks}     │   ║
║    └──────────────────────────────────────────────────┘   ║
║     ↓                                                      ║
║  ComplianceChecklist (RH1) + EvaluationBlueprint (RH2)    ║
║                                                             ║
║  ÉTAPE 4: M14 EvaluationEngine                             ║
║    • Input: RH1 + RH2 + offers (offer_extractions)         ║
║    • Output: EvaluationReport (scores_matrix)              ║
║    • M14EvaluationRepository.save_evaluation()            ║
║      → evaluation_documents                                ║
║                                                             ║
║  ÉTAPE 5: Bridge M14 → M16                                 ║
║    • populate_assessments_from_m14(workspace_id)           ║
║    • Crée dao_assessments + vendor_assessments             ║
║    • Synchronise scores_matrix → grilles comparatives      ║
╚════════════════════════════════════════════════════════════╝
```

---

## 🔗 Coutures Enterprise-Grade

### COUTURE 1 : Bundle → Offer Extraction

**Fichiers** :
- `src/services/pipeline_v5_service.py:147` — `extract_offers_from_bundles()`
- `src/couche_a/extraction/persistence.py:173` — `persist_tdr_result_to_db()`

**Flux** :
1. Requête SQL : `supplier_bundles JOIN bundle_documents` par `workspace_id`
2. Concaténation `raw_text` par `bundle_id` (ordre `uploaded_at`)
3. `extract_offer_content_async(text, document_role)` — LLM Mistral
4. Persistence : `offer_extractions(workspace_id, bundle_id, supplier_name, extracted_data_json)`

**FK Critique** :
```sql
-- Migration 076
ALTER TABLE offer_extractions 
  ADD CONSTRAINT offer_extractions_bundle_id_fkey
  FOREIGN KEY (bundle_id) REFERENCES supplier_bundles(id);
```

**Tests** :
- ✅ 6 bundles extraits (workspace f1a6edfb)
- ✅ `bundle_id` UUID valide → FK integrity

---

### COUTURE 2 : M12 → M13 (Regulatory Compliance)

**Fichiers** :
- `src/services/pipeline_v5_service.py:341` — `build_pipeline_v5_minimal_m12()`
- `src/procurement/m13_engine.py:60` — `process_m12()`
- `src/procurement/m13_persistence_payload.py:28` — `build_m13_regulatory_profile_persist_payload()`

**Handoff H1** :
```python
# M12 Output
handoffs.regulatory_profile_skeleton = {
    "framework": "DGMP_MALI",
    "framework_confidence": 0.6,
    "procedure_type": "UNKNOWN",  # Résolu par M13
    "threshold_tier": None,       # Calculé par M13
}
```

**M13 Processing** :
1. **RegimeResolver** : `skeleton + recognition → Regime`
   - Lit `config/regulatory/dgmp_mali/thresholds.yaml`
   - Applique règles DGMP (seuils XOF)
   - Output : `procedure_type` déterministe

2. **RequirementsInstantiator** : `Regime → ProcedureRequirements`
   - Gates administratifs (eligibility, validity)
   - Règles expiration documents (6 mois agrément, 1 an kbis)
   - Poids évaluation (technique 60%, financier 40%)

3. **Persistence** :
```sql
INSERT INTO m13_regulatory_profile_versions (
    case_id, document_id, profile_payload
) VALUES (
    :cid, :did, :payload
);

-- payload JSONB structure:
{
  "schema_version": "m13_regulatory_profile_envelope_v1",
  "profile_index": {
    "framework": "DGMP_MALI",
    "procedure_type": "appel_offres_ouvert",
    "rules_applied": [...]
  },
  "m13": { /* M13Output complet */ },
  "m13b": { /* M13BHooksPayload — Semaine 2 */ }
}
```

**Tests** :
- ✅ Workspace f1a6edfb → `procedure_type=unknown` (corpus minimal)
- ⚠️ **BUG POTENTIEL** : M12 minimal sans vrai corpus → M13 ne peut pas résoudre procédure
- **FIX NEEDED** : Corpus complet ITT/DAO → H1 framework_confidence = 0.8+

---

### COUTURE 3 : M13 → M14 (Evaluation)

**Fichiers** :
- `src/services/pipeline_v5_service.py:392` — Construction `M14EvaluationInput`
- `src/procurement/m14_engine.py` — `EvaluationEngine.evaluate()`
- `src/procurement/m14_evaluation_repository.py` — `save_evaluation()`

**Handoffs RH1 + RH2** :
```python
inp = M14EvaluationInput(
    case_id=case_id,
    source_rules_document_id=doc_id,
    offers=[...],  # depuis offer_extractions
    h2_capability_skeleton={...},  # M12.handoffs
    h3_market_context={...},       # M12.handoffs
    rh1_compliance_checklist=m13_out.compliance_checklist.model_dump(),
    rh2_evaluation_blueprint=m13_out.evaluation_blueprint.model_dump(),
    process_linking_data=[],
)
```

**M14 Output** :
```sql
INSERT INTO evaluation_documents (
    workspace_id, case_id, source_document_id, scores_matrix
) VALUES (...);

-- scores_matrix JSONB:
{
  "criteria": [...],
  "vendors": [...],
  "scores": [[...]]  -- Matrice 2D
}
```

**Tests** :
- ✅ `evaluation_documents` créé (workspace f1a6edfb)
- ✅ `scores_matrix` présent

---

### COUTURE 4 : M14 → M16 (Bridge Assessments)

**Fichiers** :
- `src/services/m14_bridge.py:355` — `populate_assessments_from_m14()`
- `src/services/pipeline_v5_service.py:440` — Appel bridge

**Flux** :
1. Lit `evaluation_documents.scores_matrix` (dernière version)
2. Extrait critères DAO + scores vendeurs
3. Crée/update `dao_assessments` (per criterion)
4. Crée/update `vendor_assessments` (per vendor × criterion)
5. Logs `assessments_sync_log`

**Tests** :
- ✅ Bridge exécuté (workspace f1a6edfb)
- ⚠️ `created + updated = 0` → scores_matrix vide ou format incorrect

---

## 🐛 Bugs Identifiés

### BUG 1 : M13 procedure_type=UNKNOWN

**Symptôme** : Pipeline retourne `step_3_m13_procedure_type: "unknown"`

**Cause** :
- `build_pipeline_v5_minimal_m12()` crée corpus tronqué (500k chars)
- `framework_detected = ProcurementFramework.UNKNOWN` hardcodé
- M13 RegimeResolver ne peut pas résoudre procédure sans vraies données ITT

**Fix** :
1. Lire **vrais documents ITT/DAO** depuis `bundle_documents`
2. Appeler Pass 1A/1B/1C pour reconnaissance complète
3. Construire M12 complet (pas minimal) avec :
   - `framework_detected` = détecté (DGMP_MALI / SCI)
   - `procedure_type` = inféré de seuils
   - `threshold_tier` = calculé

**Fichier** : `src/services/pipeline_v5_service.py:78`

---

### BUG 2 : M16 Bridge assessments_created=0

**Symptôme** : `step_5_assessments_created: 0`

**Cause Potentielle** :
- `scores_matrix` vide ou format incompatible
- M14 n'a pas évalué (pas de vraies offres structurées)
- `offer_extractions.extracted_data_json` manque fields critiques

**Fix** :
1. Valider structure `scores_matrix` (voir spec M16)
2. Logger détails M14 evaluation result
3. Checker `extracted_data_json` contient `supplier_name`, `total_amount`, `currency`

**Fichier** : `src/services/m14_bridge.py:355`

---

### BUG 3 : Pipeline V5 Router Missing in OpenAPI

**Symptôme** : Railway 404 sur `/api/workspaces/{id}/run-pipeline`

**Cause** :
- Route enregistrée dans `app_factory.py` ligne 144/171
- Mais Railway déploie via `main.py` → `create_railway_app()`
- Router `pipeline_v5_router` importé mais peut-être pas monté

**Fix** :
✅ **DÉJÀ FAIT** — vérifié ligne 171 `app.include_router(pipeline_v5_router)`

**Investigation** : Railway logs montrent app démarré — tester avec JWT valide

---

## 🧪 Plan de Tests Complet

### TEST 1 : M13 avec Documents Réels

```python
# Workspace avec ITT + DAO complets
wid = "f1a6edfb-ac50-4301-a1a9-7a80053c632a"

# 1. Upload ITT Mali (DGMP format)
# 2. Upload DAO avec seuils
# 3. Run pipeline V5
# 4. Assert: procedure_type != "unknown"
#    Assert: threshold_tier détecté
#    Assert: m13_regulatory_profile_versions créé
```

### TEST 2 : M14 Evaluation Complète

```python
# Workspace avec 3+ offres extraites
# 1. Run pipeline force_m14=True
# 2. Assert: scores_matrix non vide
# 3. Assert: len(vendors) == len(offer_extractions)
# 4. Assert: len(criteria) == dao_criteria count
```

### TEST 3 : M16 Bridge Synchronisation

```python
# Après M14 complet
# 1. Run bridge
# 2. Assert: dao_assessments créés (1 par critère)
# 3. Assert: vendor_assessments créés (vendors × critères)
# 4. Assert: assessments_sync_log entry
```

---

## 📋 Checklist Enterprise-Grade

- [x] Migrations 075/076 appliquées (bundle_id FK)
- [x] Pipeline V5 service implémenté
- [x] Route API `/run-pipeline` enregistrée
- [x] M13 persistence envelope JSONB
- [x] M13B models créés (hooks Semaine 2)
- [x] M14 bridge implémenté
- [ ] **FIX BUG 1** : M12 complet (Pass 1A/1B/1C)
- [ ] **FIX BUG 2** : M16 assessments population
- [ ] **TEST 1** : M13 procedure_type résolution
- [ ] **TEST 2** : M14 scores_matrix complet
- [ ] **TEST 3** : M16 bridge avec données réelles
- [ ] Documentation coutures (CE FICHIER)
- [ ] PR + Code review CTO

---

## 📝 Prochaines Étapes

1. **Corriger M12 Construction** :
   - Lire ITT/DAO depuis `bundle_documents`
   - Appeler Pass 1A pour reconnaissance framework
   - Construire M12 complet (pas minimal)

2. **Tester Pipeline Bout-en-Bout** :
   - Workspace réel avec ITT Mali DGMP
   - 3+ offres fournisseurs complètes
   - Valider M13 → procedure_type correct
   - Valider M14 → scores_matrix peuplé
   - Valider M16 → assessments créés

3. **Monitoring Production** :
   - Logs M13 régime résolution
   - Logs M14 evaluation duration
   - Logs M16 bridge sync count
   - Alert si procedure_type=unknown > 10%

---

**Responsable** : Claude Sonnet 4.5 + Abdoulaye Ousmane  
**Validation** : ⏳ Tests en cours  
**Merge** : ⏳ Après validation CTO
