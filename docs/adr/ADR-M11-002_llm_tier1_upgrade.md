# ADR-M11-002 — LLM Tier-1 Upgrade : mistral-large + mistral-ocr

**Date**    : 2026-03-16  
**Statut**  : ACCEPTÉ  
**Auteur**  : Abdoulaye Ousmane — CTO DMS  
**Branche** : feat/m11-llm-upgrade  

---

## Contexte

Le backend d'annotation DMS traite des documents procurement longs (TDR, offres
techniques, offres financières) issus de PDF scannés multi-pages. Ces documents
peuvent atteindre 40–100 pages une fois extraits en texte.

Le modèle actuel `mistral-small-latest` (via `chat.complete()`) présente deux
limites critiques :

1. **Qualité extraction insuffisante** sur les documents complexes → taux de
   champs AMBIGUOUS ou ABSENT trop élevé pour atteindre les seuils M15.
2. **OCR limité aux images** (`image_url` base64) — les PDF scannés ne passent
   pas par `mistral-ocr-latest` qui supporte nativement les PDF.

---

## Décision

### Tier-1 LLM — annotation et extraction DAO

| Constante       | Valeur                  |
|-----------------|-------------------------|
| TIER_1_MODEL    | `mistral-large-latest`  |

Utilisation : annotation procurements (src/couche_a/llm_router.py).  
Jamais dans services/annotation-backend/ (géré séparément via MISTRAL_MODEL env).

### Tier-1 OCR — documents scannés et PDF

| Constante        | Valeur                 |
|------------------|------------------------|
| TIER_1_OCR_MODEL | `mistral-ocr-latest`  |

Utilisation : extraction texte depuis PDF scanné et images (src/extraction/engine.py).  
API : `client.ocr.process()` avec document base64 pour fichiers locaux.  
Fallback : Azure Form Recognizer si `AZURE_FORM_RECOGNIZER_ENDPOINT` défini.

---

## Estimation de coût (100 dossiers)

| Opération | Volume estimé | Coût unitaire | Total |
|-----------|--------------|---------------|-------|
| OCR PDF scanné (avg 20 pages/doc) | 100 docs | ~$0.04/doc | ~$4.00 |
| Annotation mistral-large (avg 12k tokens) | 100 docs | ~$0.022/doc | ~$2.20 |
| **Total estimé** | | | **~$6.20** |

Hypothèses : mistral-large $8/M input tokens, mistral-ocr $2/1000 pages.

---

## Alternatives rejetées

- `pixtral-12b-2409` — modèle vision, pas d'API OCR dédiée, moins précis sur
  texte long.
- `mistral-large-2512` — version datée, préférer `mistral-large-latest` pour
  bénéficier des correctifs automatiques.
- `gpt-4o` — coût 3× supérieur, dépendance OpenAI incompatible avec la politique
  fournisseur unique.

---

## Conséquences

- `src/couche_a/llm_router.py` : nouveau module — constantes + helper `get_llm_client()`
- `src/extraction/engine.py` : `_extract_mistral_ocr()` migre vers `client.ocr.process()`
  et accepte les PDF (suppression de la restriction `image/*`)
- `requirements.txt` : `mistralai>=1.5.0` (déjà présent — aucun changement de version)
- `services/annotation-backend/backend.py` : **NON MODIFIÉ** — continue d'utiliser
  `MISTRAL_MODEL` env var (géré Railway)
- Alembic : aucune migration requise

---

## Règles de gouvernance

- Toute modification de TIER_1_MODEL ou TIER_1_OCR_MODEL → GO CTO obligatoire
- Ne jamais hardcoder un model name en dehors de `llm_router.py`
- Fallback Azure conservé — actif si `AZURE_FORM_RECOGNIZER_ENDPOINT` présent
