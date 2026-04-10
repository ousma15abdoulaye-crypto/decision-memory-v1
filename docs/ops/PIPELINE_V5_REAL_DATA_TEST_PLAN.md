# Pipeline V5 — Plan Tests Dossiers Réels

**Date** : 2026-04-10  
**Status** : Prêt après merge PR #364  
**Dossiers disponibles** : 3 (320 documents)

---

## 🎯 Objectif

Tester Pipeline V5 bout-en-bout sur **3 dossiers réels de procurement** avec **metrics mesurables** pour valider :
1. M13 framework detection (DGMP/SCI)
2. M13 procedure_type resolution
3. M14 evaluation scores_matrix
4. M16 assessments population
5. Performance (durée, throughput)

---

## 📦 Dossiers Test

### DOSSIER 1 : GCF (Solution & One)
**Path** : `data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/GCF`  
**Type** : Offre technique SCI (2024)  
**Documents** : 100 (attestations, contrats, RCCM, NIF, RIB, etc.)  
**Framework attendu** : SCI  
**Procédure** : RFP Consultance  

**Fournisseurs** :
- Solution & One SARL (documents administratifs complets)

### DOSSIER 2 : PADEM (Enquête de base)
**Path** : `data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/PADEM`  
**Type** : Appel d'offres études (SCI Mali)  
**Documents** : 93  
**Framework attendu** : SCI  
**Procédure** : Consultance études (PADEM)

**Fournisseurs** :
1. IEF SARL (7 documents rapports)
2. ABESSAME (3 documents offre)
3. CRDDD SARL (20+ documents attestations)

### DOSSIER 3 : TEST Mercuriale Mali
**Path** : `data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/TEST/Mercurial`  
**Type** : Prix de référence DGMP Mali 2023  
**Documents** : 127 (16 bulletins régionaux + mercuriales)  
**Framework attendu** : DGMP_MALI  
**Procédure** : Prix de référence (non-procurement)

**Régions** :
Bamako, Sikasso, Tombouctou, Taoudeni, Kita, Bougouni, Ségou, Gao, Ménaka, Dioïla, Koulikoro, Mopti, Kidal, Nioro, Nara, San

---

## 🧪 Protocole Test

### Étape 1 : Préparation Workspaces

```bash
# Créer 3 workspaces via API Railway
curl -X POST https://annotation-backend-production.up.railway.app/api/workspaces \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "GCF - Solution & One (Test Pipeline V5)",
    "reference_code": "TEST-GCF-V5-2024",
    "process_type": "rfp_consultance",
    "estimated_value": 50000000,
    "currency": "XOF"
  }'

# Répéter pour PADEM et TEST_MERCURIALE
# Sauvegarder workspace_ids
```

### Étape 2 : Upload Documents

```bash
# Créer ZIP pour chaque dossier
cd "data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE"
zip -r GCF.zip GCF/
zip -r PADEM.zip PADEM/
zip -r TEST_MERCURIALE.zip TEST/Mercurial/

# Upload via API
curl -X POST https://.../api/workspaces/{workspace_id}/upload-zip \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "file=@GCF.zip"
```

### Étape 3 : Run Pipeline V5

```bash
# Pour chaque workspace
curl -X POST https://.../api/workspaces/{workspace_id}/run-pipeline \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"

# Capturer résultat JSON
```

### Étape 4 : Collecter Metrics

```python
# test_pipeline_real_folders.py --workspace-gcf=UUID --workspace-padem=UUID --workspace-test=UUID

METRICS = {
    "duration_s": result.duration_seconds,
    "offers_extracted": result.step_1_offers_extracted,
    "framework_detected": "extracted from M13",
    "procedure_type": result.step_3_m13_procedure_type,
    "eval_doc_created": result.step_4_m14_eval_doc_id is not None,
    "assessments_created": result.step_5_assessments_created,
    "completed": result.completed,
    "error": result.error,
}
```

---

## 📊 Metrics Attendues

### DOSSIER 1 : GCF
| Metric | Target | Acceptance |
|--------|--------|------------|
| Duration | <180s | <300s |
| Documents OCR | 100 | ≥80 |
| Offers extracted | 1 | ≥1 |
| Framework detected | SCI | SCI |
| Procedure type | rfp_consultance | != unknown |
| Eval doc created | true | true |
| Assessments created | ≥3 | ≥1 |

### DOSSIER 2 : PADEM
| Metric | Target | Acceptance |
|--------|--------|------------|
| Duration | <200s | <350s |
| Documents OCR | 93 | ≥70 |
| Offers extracted | 3 | ≥2 |
| Framework detected | SCI | SCI |
| Procedure type | rfp_consultance | != unknown |
| Eval doc created | true | true |
| Assessments created | ≥6 | ≥3 |

### DOSSIER 3 : TEST Mercuriale
| Metric | Target | Acceptance |
|--------|--------|------------|
| Duration | <250s | <400s |
| Documents OCR | 127 | ≥100 |
| Offers extracted | 0-16 | ≥0 (non-offres) |
| Framework detected | DGMP_MALI | DGMP_MALI |
| Procedure type | unknown / reference | acceptable |
| Eval doc created | false/true | true |
| Assessments created | N/A | ≥0 |

---

## ✅ Critères Succès

### Critères Techniques
- [x] Upload ZIP → bundles assemblés
- [ ] OCR Mistral → raw_text peuplé (≥80% docs)
- [ ] Extraction offres → offer_extractions (≥70% bundles)
- [ ] M13 framework detection correct (DGMP/SCI)
- [ ] M13 procedure_type != unknown (dossiers 1+2)
- [ ] M14 evaluation_documents créés
- [ ] M16 assessments populated (≥50% criteria)

### Critères Performance
- [ ] Duration moyenne <250s pour 100 docs
- [ ] Throughput ≥0.4 docs/s
- [ ] Zero errors fatals (completed=true)
- [ ] Memory stable (<2GB peak)

### Critères Business
- [ ] Framework detection accuracy ≥90% (2/3 correct minimum)
- [ ] Procedure type resolution rate ≥67% (dossiers SCI)
- [ ] Assessments coverage ≥50% (criteria × vendors)

---

## 🔥 Scenarios Edge Cases

### EDGE 1 : Documents administratifs sans offre financière
**Cas** : GCF — uniquement attestations/contrats  
**Attendu** : Extraction technique mais pas de montant  
**Validation** : `offer.extracted_data_json.total_amount = "ABSENT"`

### EDGE 2 : Multiple offres même fournisseur
**Cas** : PADEM — IEF SARL (7 rapports)  
**Attendu** : 1 bundle = 1 offre (concaténation)  
**Validation** : `supplier_bundles.vendor_name_raw = "IEF SARL"`, `offer_extractions.count() = 1`

### EDGE 3 : Documents non-procurement
**Cas** : TEST Mercuriale — bulletins prix  
**Attendu** : Framework DGMP détecté, procedure_type flexible  
**Validation** : `procedure_type in ("unknown", "reference_prices")`

---

## 📝 Rapport Final

### Template Rapport

```markdown
# Pipeline V5 — Test Dossiers Réels

**Date** : 2026-04-10  
**Workspaces** : 3  
**Documents** : 320  

## Résultats

### DOSSIER 1 : GCF
- Duration: XXs
- Offers: X/1
- Framework: SCI ✅
- Procedure: rfp_consultance ✅
- Assessments: X/Y

### DOSSIER 2 : PADEM
- Duration: XXs
- Offers: X/3
- Framework: SCI ✅
- Procedure: rfp_consultance ✅
- Assessments: X/Y

### DOSSIER 3 : TEST Mercuriale
- Duration: XXs
- Offers: X/16
- Framework: DGMP_MALI ✅
- Procedure: unknown ⚠️ (acceptable)
- Assessments: X/Y

## Metrics Globales
- Success rate: X/3 (XX%)
- Avg duration: XXs
- Total offers: X/320
- Framework accuracy: XX%
- Procedure resolution: XX%
- Assessments coverage: XX%

## Issues Identifiés
1. [Si applicable]
2. [Si applicable]

## Recommandations
1. [Si applicable]
2. [Si applicable]
```

---

## 🚀 Exécution Post-Merge

**Prérequis** :
- ✅ PR #364 merged
- ✅ Railway déployé (main branch)
- ✅ JWT token valide (role: supply_chain)
- ✅ 3 dossiers ZIP préparés

**Timeline** :
1. **H+0** : Merge PR #364
2. **H+5min** : Railway redeploy complet
3. **H+10min** : Créer 3 workspaces
4. **H+15min** : Upload 3 ZIP
5. **H+20min** : Run 3 pipelines (parallel)
6. **H+30min** : Collecter metrics
7. **H+45min** : Rapport final

---

**Responsable** : Claude Sonnet 4.5 + Abdoulaye Ousmane  
**Validation** : ⏳ Après merge PR #364  
**Documentation** : Ce fichier + test_pipeline_real_folders.py
