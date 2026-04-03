# ADR-H3-BGE-M3-001 — Local Embeddings: BGE-M3 + BGE-Reranker-v2-m3

**Status:** Accepted  
**Date:** 2026-04-03  
**Horizon:** DMS VIVANT V2 — H3 (RAG Production-Grade)  
**Author:** CTO DMS

---

## Contexte

Le pipeline RAG (H3) nécessite :

1. **Embeddings denses** (1024 dim) pour la recherche par similarité cosinus.
2. **Embeddings sparses** (BM25-like) pour la fusion hybride.
3. **Reranking** cross-encoder pour améliorer la précision des top-K résultats.

Contraintes DMS :

- **Zéro appel API externe** pour les embeddings (données de marchés publics Mali,
  potentiellement sensibles — RÈGLE-09, INV-R3 souveraineté).
- **Railway tier** : 8 GB RAM disponibles en production.
- **Mali contexte** : connectivité intermittente → modèles doivent fonctionner offline.

## Décision

**FlagEmbedding** (`FlagEmbedding>=1.2.5`) avec les modèles BAAI/bge-m3 et
BAAI/bge-reranker-v2-m3 est retenu.

### Justification

| Critère | BGE-M3 (FlagEmbedding) | OpenAI Embeddings | Cohere Embed |
|---------|----------------------|-------------------|--------------|
| Fonctionnement offline | ✅ | ❌ | ❌ |
| Dense + Sparse (hybride) | ✅ | Dense seulement | Dense seulement |
| Multilingue (FR/EN/AR) | ✅ | ✅ | ✅ |
| Dimension 1024 | ✅ | 1536 | 1024 |
| Coût par token | 0€ | $0.0001/1K | $0.0001/1K |
| RAM requise | ~4 GB (fp16) | 0 (API) | 0 (API) |
| Souveraineté données | ✅ | ❌ | ❌ |

BGE-M3 est le seul modèle combinant dense+sparse natif, multilingue,
et fonctionnement 100% local. La contrainte Railway 8 GB RAM est satisfaite
avec `use_fp16=True`.

### Configuration

- `BGE_MODEL_PATH` : chemin local du modèle (vide → télécharge depuis HuggingFace au 1er démarrage).
- En CI/tests : `FlagEmbedding` absent → `_StubBackend` utilisé automatiquement.
- En production : `_BGEBackend` chargé si `FlagEmbedding` importable.

### Modèles

| Rôle | Modèle | RAM (fp16) |
|------|--------|------------|
| Embedding | `BAAI/bge-m3` | ~4 GB |
| Reranking | `BAAI/bge-reranker-v2-m3` | ~2 GB |

### Ingestion

Script `scripts/ingest_embeddings.py` : chunker → embed → INSERT `dms_embeddings`.
Index IVFFlat créé après le premier batch (voir `scripts/create_ivfflat_index.py`).

## Conséquences

- `FlagEmbedding>=1.2.5` ajouté à `requirements.txt`.
- `src/memory/embedding_service.py` : `_BGEBackend` chargé conditionnellement.
- `src/memory/reranker.py` : `_BGERerankerBackend` chargé conditionnellement.
- Premier déploiement prod : `BGE_MODEL_PATH` doit pointer vers modèles pré-téléchargés.
- CI : pas de `FlagEmbedding` dans l'image CI → stubs utilisés (tests passent).

## Références

- Migration 064 (`dms_embeddings` table, `vector(1024)`)
- `src/memory/embedding_service.py`, `src/memory/reranker.py`
- `scripts/ingest_embeddings.py`, `scripts/create_ivfflat_index.py`
- RÈGLE-13 (toute dépendance nouvelle = ADR avant premier commit)
- INV-R3 (souveraineté données — zéro exfiltration vers API tiers)
