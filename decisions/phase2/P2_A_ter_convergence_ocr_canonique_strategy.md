# P2-A-ter — Convergence OCR canonique DMS

**Mandat** : DMS-MANDAT-CONVERGENCE-OCR-CANONIQUE-V2  
**Autorité** : CTO principal DMS  
**Date** : 2026-04-24  
**Statut** : ✅ COMPLÉTÉ

---

## 1. Cartographie brute des 2 chemins OCR

### Chemin 1 — Pass -1 Assembler (LangGraph)

**Fichier** : `src/assembler/graph.py` (ligne 50-98)  
**Fonction** : `extract_node()` → `ocr_with_mistral(file_path)`  
**Input** : Fichier PDF/image sur disque (Path)  
**Output** : `{"raw_text": str, "confidence": float, "ocr_engine": str}`  
**Persistance** : `bundle_documents.raw_text` + `structured_json` via `finalize_node()` → `write_bundle()`  
**Clé** : `MISTRAL_API_KEY` (env var, lu ligne 44 `ocr_mistral.py`)  
**Endpoint Mistral** : `POST https://api.mistral.ai/v1/ocr` (ligne 95 `ocr_mistral.py`)  
**Usage** : Import ZIP → extraction documents → bundles fournisseurs

### Chemin 2 — Backend annotation `/predict`

**Fichier** : `services/annotation-backend/backend.py` (ligne 1303-1543)  
**Fonction** : `predict()` → `_call_mistral(text)`  
**Input** : Texte déjà extrait (str) via `{"tasks": [{"data": {"text": "..."}}]}`  
**Output** : JSON annotation structurée Label Studio  
**Persistance** : Aucune directe (retour HTTP JSON)  
**Clé** : `MISTRAL_API_KEY` (backend.py ligne 99-110)  
**Endpoint Mistral** : `POST https://api.mistral.ai/chat/completions` (client.chat.complete ligne 1183-1189)  
**Usage** : Annotation extraction métadonnées (pas OCR PDF → texte)

---

## 2. Analyse de divergence

**Pourquoi 2 chemins = 2 vérités** :
- Chemin 1 : OCR multimodal (PDF scan → texte brut)
- Chemin 2 : Extraction structurée (texte → JSON annotation)
- **Confusion architecturale** : `/predict` appelé avec `document_id` sans texte → mesures P2-A invalides (2-4s = overhead, pas OCR)

**Risques concrets** :
1. Mesures baseline Phase 2 faussées si flux mal identifié
2. Import documents sans OCR → backend annotation reçoit texte vide
3. Double consommation tokens Mistral (OCR + extraction) si pas de cache
4. Diagnostic I-DEBT-1 (timeout 120s) impossible sans baseline OCR réelle

**Pourquoi fermer maintenant** :
- P2-B PADEM suspendu jusqu'à baseline OCR cold validée
- Phase 2 I-DEBT-1 bloquée sans distinction OCR (Pass -1) vs extraction (backend)
- Import GCF P2-A n'a pas déclenché OCR automatique → documents vides en base

---

## 3. Recommandation canonique unique

### Chemin canonique : **Pass -1 Assembler (`src/assembler/ocr_mistral.py`)**

**Justification** :
- Fonction dédiée OCR PDF/image → texte (`ocr_with_mistral()`)
- Endpoint Mistral OCR correct (`/v1/ocr`, pas `/chat/completions`)
- Persistance `bundle_documents.raw_text` tracée
- Intégration pipeline ingestion ZIP complète

### Sort de l'autre chemin : **Backend `/predict` = Extraction post-OCR**

**Reclassification** :
- `/predict` n'est PAS un endpoint OCR
- `/predict` = extraction structurée métadonnées (texte → JSON)
- **Prérequis** : texte OCR déjà disponible (fourni par Pass -1 ou Label Studio)

**Action** : Aucune suppression. Clarifier documentation que backend annotation consomme texte OCR, ne le produit pas.

### Raccord backend extraction

**Flux complet** :
1. Import ZIP → Pass -1 `extract_node()` → `ocr_with_mistral(PDF)` → `raw_text` persisté `bundle_documents`
2. Label Studio récupère `raw_text` depuis DB → envoie à `/predict` via `{"data": {"text": raw_text}}`
3. Backend `/predict` → `_call_mistral(text)` → extraction JSON annotation

**Point de jonction** : `bundle_documents.raw_text` (table DB commune)

**Validation P2-A-ter** : Documents GCF importés P2-A ont `raw_text = ""` → **Pass -1 non exécuté** → mesures P2-A invalides.

---

## 4. Intégration minimale au chantier

**Faut-il intégrer dans chantier P3.4 ?** : **OUI**

**Forme minimale** : **Addendum ADR Phase 2** (pas de mandat séparé, pas de fragment supplémentaire)

**Contenu addendum** :
- Chemin canonique OCR = Pass -1 Assembler (`ocr_with_mistral()`)
- Backend `/predict` reclassifié extraction post-OCR
- Import documents Phase 2 doit déclencher Pass -1 ou fournir `raw_text` pré-extrait
- P2-A mesures `/predict` invalidées (texte vide, 2-4s = overhead HTTP)
- P2-A-ter conclut : **baseline OCR cold non établie**, P2-B reste suspendu

**Intégration sans dérive** :
- Addendum 1 page max
- Référence P2-A-ter comme diagnostic
- Pas de modification code
- Pas de nouveau fragment Phase 2
- Conclusion : P2-B nécessite ré-exécution Pass -1 sur GCF pour baseline OCR réelle

**Prochaine étape recommandée** : Mandat P2-A-quater (exécution Pass -1 sur 3 PDFs GCF → baseline OCR cold 9 mesures) ou suspension Phase 2 jusqu'à convergence outillage import.

---

## Verdict

**Convergence établie** :
- 1 chemin OCR canonique : Pass -1 `ocr_with_mistral()`
- 1 chemin extraction : Backend `/predict`
- Jonction claire : `bundle_documents.raw_text`

**Blocage Phase 2 confirmé** : Import GCF P2-A sans Pass -1 → documents vides → mesures invalides → baseline manquante.

**Recommandation CTO** : Addendum ADR Phase 2 + arbitrage sur déblocage (Pass -1 GCF ou suspension Phase 2).
