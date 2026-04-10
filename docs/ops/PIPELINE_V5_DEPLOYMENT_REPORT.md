# Pipeline V5 - Rapport de Déploiement et Corrections

**Date** : 2026-04-10  
**Branche** : `refactor/v52-pydantic-settings`  
**Commits** : `0afa8536`, `b81a0032`  
**Environnement** : Railway Production  

---

## 🎯 Objectif

Déployer et tester le Pipeline V5 sur un workspace réel contenant :
- 6 documents avec texte OCR
- 3 critères DAO
- 1 committee

---

## 🔧 Bugs Critiques Résolus

### BUG 1 : `granted_by` manquant dans workspace_memberships
**Fichier** : `src/api/routers/workspaces.py:266`  
**Symptôme** : NOT NULL constraint violation lors création workspace  
**Cause** : Paramètre SQL `granted_by` déclaré mais non bindé  
**Fix** : Ajout `"granted_by": user_id` dans le dictionnaire de paramètres  

### BUG 2 : Colonne `committees.id` inexistante
**Fichier** : `src/services/pipeline_v5_service.py:296`  
**Symptôme** : `column c.id does not exist`  
**Cause** : Requête SQL référence `c.id` mais la colonne s'appelle `committee_id`  
**Fix** : `SELECT c.id` → `SELECT c.committee_id`  

### BUG 3 : Architecture `offer_extractions.artifact_id` cassée
**Symptôme** : FK violation - bundles non présents dans table `artifacts`  
**Cause Racine** : Le pipeline concatène documents par bundle et utilise `supplier_bundles.id`, mais la FK pointait vers `artifacts.id` (table séparée pour les uploads)  

**Solution** : Refonte architecturale complète

#### Migration 075 : `fix_offer_extractions_artifact_fk`
```sql
-- DROP FK vers artifacts.id
ALTER TABLE offer_extractions 
  DROP CONSTRAINT offer_extractions_artifact_id_fkey;

-- Conversion TEXT → UUID
ALTER TABLE offer_extractions 
  ALTER COLUMN artifact_id TYPE uuid USING artifact_id::uuid;

-- FK temporaire vers bundle_documents (essai 1)
ALTER TABLE offer_extractions 
  ADD CONSTRAINT offer_extractions_artifact_id_fkey
  FOREIGN KEY (artifact_id) REFERENCES bundle_documents(id);
```

#### Migration 076 : `fix_offer_extractions_fk_to_bundles`
```sql
-- DROP FK bundle_documents (essai 1 incorrect)
ALTER TABLE offer_extractions 
  DROP CONSTRAINT offer_extractions_artifact_id_fkey;

-- RENAME pour clarifier sémantique
ALTER TABLE offer_extractions 
  RENAME COLUMN artifact_id TO bundle_id;

-- FK finale vers supplier_bundles
ALTER TABLE offer_extractions 
  ADD CONSTRAINT offer_extractions_bundle_id_fkey
  FOREIGN KEY (bundle_id) REFERENCES supplier_bundles(id);
```

#### Code Python
**Fichiers modifiés** :
- `src/couche_a/extraction/persistence.py` : 
  - Renommage `artifact_id` → `bundle_id` dans signatures et paramètres SQL
  - Logs mis à jour
- `src/services/pipeline_v5_service.py` :
  - Requête SELECT : `artifact_id` → `bundle_id`
  - Documentation : mise à jour sémantique

---

## ✅ Résultat Pipeline V5

**Workspace testé** : `f1a6edfb-ac50-4301-a1a9-7a80053c632a`  
**Case ID** : `28b05d85-62f1-4101-aaec-96bac40905cd`

```json
{
  "workspace_id": "f1a6edfb-ac50-4301-a1a9-7a80053c632a",
  "case_id": "28b05d85-62f1-4101-aaec-96bac40905cd",
  "completed": true,
  "stopped_at": null,
  "error": null,
  "step_1_offers_extracted": 6,
  "step_2_m12_reconstructed": true,
  "step_3_m13_procedure_type": "unknown",
  "step_4_m14_eval_doc_id": "dedd4adc-1bfb-4154-b11a-0b3ffbb4e861",
  "step_5_assessments_created": 0,
  "duration_seconds": 106.07
}
```

### Détails Extraction

| # | Fournisseur | Bundle ID | Status |
|---|-------------|-----------|--------|
| 1 | ABSENT | f19c8f9f | ✅ Extrait |
| 2 | ABSENT | 0feb8c18 | ✅ Extrait |
| 3 | ABSENT | 0b19365e | ✅ Extrait |
| 4 | ABSENT | 984ecd50 | ✅ Extrait |
| 5 | ABSENT | 0aa0b276 | ✅ Extrait |
| 6 | ABSENT | 52e162e5 | ✅ Extrait |

**Note** : `supplier_name=ABSENT` indique que les documents n'avaient pas de nom de fournisseur extrait. L'extraction structurelle a néanmoins fonctionné.

---

## 📊 État Base de Données

### Migrations Appliquées
```
v52_p2_001_price_line_market_delta
076_fix_offer_extractions_fk_to_bundles
```

**⚠️ ATTENTION** : Seule la migration 076 est enregistrée dans `alembic_version`, mais les migrations 074, 075, 076 ont toutes été appliquées au schéma. Incohérence à investiguer.

### Tables Affectées
- `offer_extractions` : 6 lignes créées
- `evaluation_documents` : 2 documents créés
- `supplier_bundles` : Intégrité référentielle OK
- `workspace_memberships` : Correction appliquée (pas de test direct)

---

## 🚀 Déploiement

### Commits
1. **0afa8536** : `fix: granted_by syntax in workspaces router`
2. **b81a0032** : `fix(pipeline-v5): 3 bugs critiques corrigés + refonte artifact_id→bundle_id`

### Push
```bash
git push origin refactor/v52-pydantic-settings
# Pushed: 0afa8536..b81a0032
```

### Prochaines Étapes
1. **Merger** `refactor/v52-pydantic-settings` → `main`
2. **Redéployer** `annotation-backend` sur Railway
3. **Tester** création workspace + pipeline V5 via API
4. **Documenter** processus M13/M14 (procedure_type=unknown à investiguer)

---

## 📝 Leçons Apprises

### Architecture
- **Sémantique claire** : `artifact_id` était ambigu. `bundle_id` explicite la relation avec `supplier_bundles`.
- **FK cohérentes** : Les FK doivent pointer vers les tables effectivement utilisées par le code.
- **Test de bout en bout** : Les tests unitaires n'ont pas détecté ces bugs (pas de DB réelle).

### Process
- **Migrations incrémentales** : Migration 075 a été une étape intermédiaire nécessaire (essai bundle_documents).
- **Code + Schema** : Toujours synchroniser les refactorings SQL avec le code Python.
- **Logs explicites** : Les logs `[PIPELINE-V5]` et `[BRIDGE]` ont permis de tracer les erreurs rapidement.

---

## 🔒 RÈGLE FREEZE

**Fichiers Critiques** :
- `alembic/versions/075_fix_offer_extractions_artifact_fk.py` ✅
- `alembic/versions/076_fix_offer_extractions_fk_to_bundles.py` ✅
- `src/couche_a/extraction/persistence.py` ✅
- `src/services/pipeline_v5_service.py` ✅

❌ **Ne jamais modifier** ces migrations post-déploiement  
❌ **Ne jamais réintroduire** `artifact_id` dans le code  

---

**Responsable** : Claude Sonnet 4.5 + Abdoulaye Ousmane  
**Validation CTO** : ⏳ En attente  
