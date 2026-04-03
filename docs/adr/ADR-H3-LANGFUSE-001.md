# ADR-H3-LANGFUSE-001 — LLM Observability: Langfuse

**Status:** Accepted  
**Date:** 2026-04-03  
**Horizon:** DMS VIVANT V2 — H3 (RAG Production-Grade)  
**Author:** CTO DMS

---

## Contexte

Le pipeline RAG (H3) effectue des appels LLM via OpenRouter (Mistral/Claude).
Pour maintenir la qualité et détecter les régressions en production, une
observabilité des appels LLM est nécessaire :

- Traçabilité des prompts, réponses, tokens, latence, coût.
- Détection de drift de qualité (contexte vs. réponse).
- Audit offline pour RAGAS baseline comparisons.

DMS stocke déjà une copie locale dans `llm_traces` (migration 065). Une
intégration avec un outil dédié (dashboard, alertes) est nécessaire en complément.

## Décision

**Langfuse** (`langfuse>=2.0.0`) est retenu pour l'observabilité LLM.

### Justification

| Critère | Langfuse | LangSmith | Phoenix (Arize) |
|---------|----------|-----------|----------------|
| Open-source (self-host possible) | ✅ | ❌ | ✅ |
| SDK Python officiel | ✅ | ✅ | ✅ |
| Intégration RAG native | ✅ | ✅ | ✅ |
| Coût tier gratuit | ✅ | Limité | ✅ |
| RGPD / données sensibles | ✅ (self-host) | ❌ | ✅ |
| Compatible OpenRouter | ✅ | ✅ | ✅ |

Langfuse est open-source, self-hostable (conforme RGPD pour les
données de marché Mali sensibles), et son SDK Python est léger.

### Configuration

- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` : variables Railway.
- `config/langfuse/langfuse_config.yaml` : `enabled: false` par défaut en dev.
- En production, `enabled: true` avec `log_prompts: false` (données sensibles).
- Copie locale toujours active via `llm_traces` (fallback si Langfuse down).

### Comportement en CI

- `LANGFUSE_PUBLIC_KEY` absent → `LangfuseIntegration._langfuse_client = None`.
- Traces locales dans `llm_traces` toujours écrites (pas de conditionnelle Langfuse).

## Conséquences

- `langfuse>=2.0.0` ajouté à `requirements.txt`.
- `src/memory/langfuse_integration.py` : lit `langfuse_config.yaml` en `__init__`.
- Si `enabled: false` ou SDK absent, aucune donnée envoyée à Langfuse.
- ADR-H3-BGE-M3-001 est complémentaire (embedding local, pas de traces d'embedding dans Langfuse).

## Références

- Migration 065 (`llm_traces` table)
- `src/memory/langfuse_integration.py`
- `config/langfuse/langfuse_config.yaml`
- RÈGLE-13 (toute dépendance nouvelle = ADR avant premier commit)
