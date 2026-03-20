# BRIDGE FIX-01 — Freeze environnement OCR

**Date :** 2026-03-21  
**Statut :** FREEZE — ne pas modifier sans GO CTO

## Prérequis OCR cloud — obligatoires avant run corpus scanné

Variables requises :

- **MISTRAL_API_KEY** — non vide (OCR Mistral)
- **LLAMADMS** ou **LLAMA_CLOUD_API_KEY** — non vide (LlamaParse ; `LLAMADMS` prioritaire, aligné `src/core/api_keys.py`)

Tests de validation avant run :

```bash
python -c "from src.core.api_keys import get_mistral_api_key; get_mistral_api_key(); print('MISTRAL OK')"
python -c "from src.core.api_keys import get_llama_cloud_api_key; get_llama_cloud_api_key(); print('LLAMA OK')"
```

Si un test échoue → ne pas lancer le bridge sur corpus scanné.

## Seuils de classification — versionnés ici

| Paramètre | Valeur | Référence code |
|-----------|--------|----------------|
| `_MIN_NATIVE_CHARS` | 100 | `scripts/ingest_to_annotation_bridge.py` L.50 |
| `_MIN_SCAN_CHARS` | 50 | `scripts/ingest_to_annotation_bridge.py` L.51 |
| Seuil densité `/Image` (natif vs mixte) | 0.002 | `scripts/ingest_to_annotation_bridge.py` L.93 |

Toute modification = nouveau freeze + GO CTO obligatoire.

## Dette technique active

**STORAGE_BASE_PATH** : mutation globale confinée à un seul point dans le bridge (FIX-2, assignation unique dans `run_ingest`).  
Découplage réel = mandat ultérieur dédié.

## Gate opérationnel post-fix — séparé du merge script

Ce gate valide l’environnement OCR — pas la correction du script.

- `tasks_emitted` ≥ 190  
- `skip_by_classification.scanned_pdf` < 30  
- `skip_by_reason.no_text_all_extractors` < 30  
