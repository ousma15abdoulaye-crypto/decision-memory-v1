# ADR-CONFIDENCE-SCOPE-001 — Périmètre de la règle confidence {0.6, 0.8, 1.0}

**Status:** Accepted  
**Date:** 2026-04-03  
**Horizon:** DMS VIVANT V2 — C-5 (Governance)  
**Author:** CTO DMS

---

## Contexte

DMS V4.1.0 RÈGLE-19 et `CONTEXT_ANCHOR.md` (E-65) stipulent que la confidence
est restreinte à `{0.6, 0.8, 1.0}`. Cette règle, décrite dans le contexte de
l'extraction de documents (M12), a généré des ambiguïtés lors de l'implémentation
des composants VIVANT V2 (H2/H3) qui utilisent des scores internes continus :

- `PatternDetector._cluster_confidence()` → float continu `[0, 1]`
- `RAGResult.confidence` → float `[0.0, 0.70]` (plafonné)
- `CaseMemoryEntry.framework_confidence` → float continu
- `M13CorrectionEntry.confidence_was` → float continu (valeur historique capturée)

## Décision

La règle `confidence ∈ {0.6, 0.8, 1.0}` s'applique **exclusivement** aux champs
d'extraction documentaire du pipeline M12/M13 :

### Périmètre OBLIGATOIRE (discrete {0.6, 0.8, 1.0})

- `TracedField.confidence` — champs extraits par le pipeline LLM (M12)
- `ExtractionField.confidence` — champs normalisés (M12/M13)
- Tout champ `confidence` dans `DMSExtractionResult` (schema-freeze-v1.0)
- `NOT_APPLICABLE → confidence = 1.0` par convention (E-65 LOI 4)

### Périmètre HORS règle (floats continus documentés)

- `PatternDetector._cluster_confidence()` → score heuristique interne `[0, 1]`
- `RAGResult.confidence` → score RAG plafonné à 0.70 (invariant RAG, pas extraction)
- `CaseMemoryEntry.framework_confidence` → score de similarité mémoire `[0, 1]`
- `M13CorrectionEntry.confidence_was` → valeur historique capturée (peut être 0.0→1.0)
- `EmbeddingResult` scores, `RerankedResult.score` — scores de retrieval interne

### Règle de documentation

Tout composant utilisant un float continu hors périmètre DOIT :
1. Être documenté dans sa docstring comme "score interne, pas une confidence d'extraction".
2. Ne jamais exposer ce float en tant que `confidence` dans une réponse API publique
   sans disclaimer ou transformation vers `{0.6, 0.8, 1.0}` si requis.

## Conséquences

- CONTEXT_ANCHOR.md : ajout E-83 précisant ce périmètre.
- Les composants VIVANT V2 (PatternDetector, RAGService, etc.) sont conformes.
- Toute future extraction documentaire doit utiliser `{0.6, 0.8, 1.0}` obligatoirement.
- `M13CorrectionEntry.confidence_was` capture la valeur originale telle quelle (historique).

## Références

- DMS V4.1.0 RÈGLE-19
- `CONTEXT_ANCHOR.md` E-65 (confidence LOI 1-4)
- `CONTEXT_ANCHOR.md` E-49 (`extra=forbid`)
- `src/memory/pattern_detector.py` : `_cluster_confidence()`
- `src/memory/rag_service.py` : `_MAX_RAG_CONFIDENCE = 0.70`
