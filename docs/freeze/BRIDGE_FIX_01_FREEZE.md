# BRIDGE FIX-01 — Freeze environnement OCR

**Date :** 2026-03-21  
**Statut :** FREEZE — ne pas modifier sans GO CTO

**Empreinte SHA256 (gel formel ADR-META-001) :** `docs/freeze/FREEZE_HASHES.md` — entrée `BRIDGE_FIX_01_FREEZE.md`.

## Prérequis OCR cloud — obligatoires avant run corpus scanné

Variables d’environnement requises (noms **exactement** comme dans `src/core/api_keys.py`) :

- **MISTRAL_API_KEY** — non vide (OCR Mistral ; résolu par `get_mistral_api_key()`).
- **LLAMADMS** — clé LlamaParse / LlamaCloud (prioritaire à la résolution).
- **LLAMA_CLOUD_API_KEY** — alias local de la même clé ; utilisé si `LLAMADMS` est absent ou vide.

Résolution Llama : `get_llama_cloud_api_key()` lit **LLAMADMS** en premier, puis **LLAMA_CLOUD_API_KEY**. **Au moins une** des deux doit être non vide pour que le second test ci-dessous réussisse.

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

**STORAGE_BASE_PATH** : mutation globale confinée à **un seul point** dans `run_ingest` (FIX-01). La base est dérivée des **répertoires sources existants** (résolus) et des **parents des PDF découverts**, puis `commonpath` (avec repli si lecteurs différents).  
Découplage réel = mandat ultérieur dédié.

## Gate opérationnel post-fix — séparé du merge script

Ce gate valide l’environnement OCR — pas la correction du script.

- `tasks_emitted` ≥ 190  
- `skip_by_classification.scanned_pdf` < 30  
- `skip_by_reason.no_text_all_extractors` < 30  

---

## Réserve CTO — non bloquante merge, bloquante gate OCR prod

Avant le **gate opérationnel** sur l’environnement **Railway production**, l’AO doit confirmer **quelle variable Llama est réellement renseignée** (souvent une seule en prod).

**Action après merge sur `main`, avant gate OCR :** mettre à jour ce freeze avec le **nom unique** de variable actif en prod Railway (retirer toute mention redondante), puis commit :

`docs(freeze): clarify llama key name post-merge`
