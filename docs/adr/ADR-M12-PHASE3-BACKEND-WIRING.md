# ADR — M12 Phase 3 — Branchement orchestrateur sur annotation-backend

**Statut** : accepté  
**Date** : 2026-04-01  
**Contexte** : [`docs/contracts/annotation/ANNOTATION_BACKEND_MIGRATION_STRATEGY.md`](../contracts/annotation/ANNOTATION_BACKEND_MIGRATION_STRATEGY.md) Phase 3.

## Décision

1. La route `POST /predict` de [`services/annotation-backend/backend.py`](../../services/annotation-backend/backend.py) peut appeler [`AnnotationOrchestrator.run_passes_0_to_1`](../../src/annotation/orchestrator.py) lorsque la variable d’environnement **`ANNOTATION_USE_PASS_ORCHESTRATOR=1`** (sinon comportement inchangé : texte → Mistral comme avant).

2. **Rollback** : `ANNOTATION_USE_PASS_ORCHESTRATOR=0` (défaut) restaure le chemin monolithique sans redéploiement de code si la variable est la seule modification.

3. **RÈGLE-11 (LLM)** : aucun nouveau fournisseur LLM n’est introduit. L’appel Mistral existant (`_call_mistral`) est conservé ; le texte envoyé au modèle provient de la sortie Pass 0 (`normalized_text`) lorsque l’orchestrateur a tourné.

4. **Persistance des runs** : répertoire configurable via **`ANNOTATION_PIPELINE_RUNS_DIR`** (défaut sûr : temporaire sous conteneur si non défini).

5. **`ANNOTATION_USE_M12_SUBPASSES`** : doit être aligné avec les attentes produit (sous-passes 1A–1D). Si des runs restent dans un état résumable sans sous-passes, l’orchestrateur lève une erreur explicite — documenté dans [`ENVIRONMENT.md`](../../services/annotation-backend/ENVIRONMENT.md).

## Conséquences

- Observabilité : [`GET /health`](../../services/annotation-backend/backend.py) expose l’activation des flags (sans secrets).
- Phase 4 (thin adapter uniquement) reste hors périmètre.
