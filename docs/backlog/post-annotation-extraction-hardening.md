# Backlog CTO — durcissement extraction après gel annotation

**Contexte** : pendant la campagne d’annotation, le gel backend interdit de modifier `src/`, `main.py` et le service `services/annotation-backend/` (voir `.cursor/rules/dms-annotation-backend-freeze.mdc`).

**Objectif post-gel** : réduire les `no_text_all_extractors` sur PDFs scannés en améliorant le code d’extraction, une fois le gel levé et avec validation CTO.

## Pistes techniques

1. **`src/extraction/engine.py` — `_detect_mime_from_header` / `filetype`**  
   Quand le MIME est `application/octet-stream`, Mistral OCR refuse ; le fallback Azure n’est utilisé que si les variables Azure sont présentes. Envisager : magic bytes PDF explicites, ou forcer `application/pdf` pour les fichiers se terminant par `.pdf` après lecture `%PDF`.

2. **Ordre des fallbacks dans `ingest_to_annotation_bridge`** (si mandat produit)  
   Aujourd’hui : Mistral puis LlamaParse. Documenter ou ajuster selon coût / qualité mesurés sur l’échantillon RFQ.

3. **ADR-M11-002** (`docs/adr/ADR-M11-002_llm_tier1_upgrade.md`)  
   Réaligner la doc et le code sur le comportement réel de `mistral-ocr-latest` (PDF via Files API).

4. **Plafond 50 Mo** (`_MISTRAL_OCR_MAX_BYTES`)  
   Pour les dossiers lourds, découpe PDF côté worker ou message d’erreur plus visible dans le bridge.

5. **Tests de non-régression**  
   Étendre les tests existants sur `extract_text_any` / bridge avec PDFs fixtures scannés (binaires minimaux en `tests/fixtures/` si autorisé par la politique dépôt).

## Référence gel OCR opérationnel

- `docs/freeze/BRIDGE_FIX_01_FREEZE.md`
- `docs/ops/OCR_BRIDGE_VALIDATION.md`
