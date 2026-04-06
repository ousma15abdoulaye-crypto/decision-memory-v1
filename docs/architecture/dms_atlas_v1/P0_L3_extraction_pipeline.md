# P0 — Livrable 3 : Pipeline d’extraction documentaire

**Principe** : deux chemins principaux — **(A)** cas legacy `/api/cases/...` uploads + extraction moteur [`src/couche_a/routers.py`](../../../src/couche_a/routers.py) / [`src/extraction/engine.py`](../../../src/extraction/engine.py) ; **(B)** campagne **annotation** Label Studio via [`services/annotation-backend/backend.py`](../../../services/annotation-backend/backend.py) + orchestrateur M12 [`src/annotation/orchestrator.py`](../../../src/annotation/orchestrator.py). Ne pas les confondre.

---

## 1. Upload (Couche A — cas)

**Fichier** : [`src/couche_a/routers.py`](../../../src/couche_a/routers.py)

| Sujet | Valeur / comportement |
|-------|------------------------|
| Formats MIME | `application/pdf`, DOCX OOXML, XLSX OOXML (`ALLOWED_MIME_TYPES`) |
| Taille max | **50 MB** par fichier (`MAX_FILE_SIZE`) |
| Validation | [`src/upload_security.py`](../../../src/upload_security.py) `validate_upload_security` + quota `update_case_quota` |
| Stockage disque | `data/uploads` (répertoire relatif, créé au chargement) |
| Antivirus | **NON TRANCHÉ** dans ce fichier (pas d’appel explicite) |

**Workspace / ZIP** : voir routes dans [`src/api/routers/workspaces.py`](../../../src/api/routers/workspaces.py) (`source-package`, `upload-zip`) pour le flux process workspace — détails dans le même fichier (préparation Pass -1).

---

## 2. Pré-traitement & OCR

**LLM / OCR** : constantes dans [`src/couche_a/llm_router.py`](../../../src/couche_a/llm_router.py) :

- `TIER_1_MODEL` (défaut `mistral-large-latest`)
- `TIER_1_OCR_MODEL` (défaut `mistral-ocr-latest`)
- Fallback Azure Form Recognizer si variables `AZURE_FORM_RECOGNIZER_*` définies

**Qualité OCR** : règles détaillées dans le pipeline annotation et prompts — pas un seul seuil global documenté ici ; **NON TRANCHÉ** pour « qualité minimale » hors contexte annotation.

**Multi-pages** : géré côté extraction PDF et orchestrateur annotation (voir `orchestrator.py`).

---

## 3. Extraction structurée

| Composant | Rôle |
|-----------|------|
| [`src/extraction/engine.py`](../../../src/extraction/engine.py) | Moteur extraction couche extraction legacy / jobs |
| [`services/annotation-backend/backend.py`](../../../services/annotation-backend/backend.py) | API Mistral, post-traitement, validation `DMSAnnotation` via [`prompts/schema_validator.py`](../../../services/annotation-backend/prompts/schema_validator.py) (**gelé sans GO CTO**) |
| [`src/annotation/document_classifier.py`](../../../src/annotation/document_classifier.py) | Classification déterministe avant / avec LLM (`TaxonomyCore`, `DocumentRole`) |

**Prompt exact** : [`services/annotation-backend/prompts/`](../../../services/annotation-backend/prompts/) — fichier `SYSTEM_PROMPT` et validateur ; **ne pas recopier ici** (taille) ; référence de vérité dans le dépôt.

**Types documents SCI (RCCM, NIF, etc.)** : le classifieur expose des énumérations **génériques** (DAO, offre, etc.). Une **liste exhaustive alignée RCCM/NIF/Quitus** par libellé métier **n’apparaît pas** comme enums dans [`document_classifier.py`](../../../src/annotation/document_classifier.py) — **NON TRANCHÉ** pour correspondance 1:1 avec la taxonomie métier SCI sans revue métier complémentaire.

---

## 4. Scoring de confiance

**Module** : [`src/cognitive/confidence_envelope.py`](../../../src/cognitive/confidence_envelope.py)

- Seuils de **régime** : `overall >= 0.8` → vert ; `>= 0.5` → jaune ; sinon rouge (`regime_from_overall`).
- `requires_hitl(overall)` : vrai si régime rouge.
- Agrégation bundle : `compute_bundle_confidence` = **min** des confiances documents (INV-C09).
- Frame : `compute_frame_confidence` = moyenne des bundles.

**Champs SQL** : `bundle_documents.system_confidence`, etc. (migrations BLOC5 — voir **L5**).

**Calibration 0.8 / 0.5** : **NON TRANCHÉ** — constantes codées en dur dans `regime_from_overall` ; pas de corpus de calibration décrit dans ce module.

---

## 5. Boucle HITL

| Aspect | Implémentation |
|--------|----------------|
| Déclenchement | `hitl_required` sur bundles ; confiance agrégée rouge dans résumés cognitifs (`confidence_summary_for_workspace` message « validation HITL requise ») |
| Que voit l’humain | **Label Studio** + backend annotation — hors périmètre API seule |
| Corrections persistées | Tables `m12_correction_log`, `m13_correction_log`, `extraction_corrections` (migrations 015/019/054/057) — voir **L5** |
| Recalibrage modèle | **NON IMPLÉMENTÉ** comme boucle d’apprentissage automatique dans le code référencé |
| Permissions HITL | **NON TRANCHÉ** comme rôle dédié ; RBAC général **L7** |

---

## 6. Fichiers « code du pipeline » (liste de travail)

| Zone | Fichiers clés |
|------|----------------|
| Upload handler | [`src/couche_a/routers.py`](../../../src/couche_a/routers.py) |
| Extracteur | [`src/extraction/engine.py`](../../../src/extraction/engine.py), [`src/couche_a/llm_router.py`](../../../src/couche_a/llm_router.py) |
| Annotation service | [`services/annotation-backend/backend.py`](../../../services/annotation-backend/backend.py) |
| Orchestrateur | [`src/annotation/orchestrator.py`](../../../src/annotation/orchestrator.py) |
| Scoring confiance | [`src/cognitive/confidence_envelope.py`](../../../src/cognitive/confidence_envelope.py) |
| Tests | `tests/annotation/`, `tests/test_extraction_*`, `tests/cognitive/`, etc. |

---

## 7. Limitations avouées

- Pipeline **Couche A** (`run_pipeline_a_*` dans [`src/couche_a/pipeline/service.py`](../../../src/couche_a/pipeline/service.py)) est un **autre** orchestrateur (étapes `preflight`, `scoring`, …) pour les **cases** — voir INV-P* dans ce fichier.
- Constitution **online-only** : [`src/core/config.py`](../../../src/core/config.py) `INVARIANTS["online_only"]`.
