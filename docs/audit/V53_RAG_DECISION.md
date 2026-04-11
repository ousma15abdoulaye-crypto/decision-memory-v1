# V53 — Décision RAG / pgvector (M-CTO-V53-G)

**Date :** 2026-04-11  
**Option retenue :** **B** — pas de branchement production de `RAGService` dans cette livraison.

## État

- `src/memory/rag_service.py` reste dans le dépôt pour **tests** et mandat futur (corpus réglementaire, RAGAS, feature flag).
- `process_info_handler` (`src/agent/handlers.py`) continue d’utiliser le LLM **sans** retrieval pgvector — comportement inchangé mais **documenté** pour éviter le faux vert « capacité RAG livrée ».

## Prochaine étape (hors V53-G minimal)

Mandat dédié : câbler `RAGService` + corpus + métriques, **ou** retirer l’extension pgvector des déploiements sans usage.

## Preuve CI

Script `scripts/check_v53_no_rag_import_in_src.py` — échoue si un fichier sous `src/` (hors `src/memory/rag_service.py`) importe `rag_service`. Job GitHub Actions : `v53-sovereignty-gate` dans `.github/workflows/ci-v52-gates.yml`.
