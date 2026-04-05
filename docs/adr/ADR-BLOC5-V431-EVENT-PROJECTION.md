# ADR — Projection post-scellement BLOC5 V4.3.1 (événements vs tâche dédiée)

**Statut** : accepté (implémentation BLOC5)  
**Contexte** : la SPEC impose `project_sealed_workspace` / `on_workspace_sealed` après **COMMIT** du scellement, avec alimentation Couche B (signaux marché) selon **C2-V431** (tous bundles `qualified`, pas de filtre `is_retained` sur la mémoire prix).

## Décision

1. **Conserver** le projector existant [`src/workers/arq_projector_couche_b.py`](../../src/workers/arq_projector_couche_b.py) pour les événements `workspace_events` de type `EVALUATION_SEALED`, `BUNDLE_SCORED`, etc. — **sans modifier** la sémantique des scores M14.
2. **Ajouter** une tâche ARQ distincte **`project_sealed_workspace`** dans [`src/workers/arq_sealed_workspace.py`](../../src/workers/arq_sealed_workspace.py), enqueued **uniquement** depuis [`src/api/routers/committee_sessions.py`](../../src/api/routers/committee_sessions.py) **après** la sortie du `with get_connection()` (donc après `COMMIT`), lorsque le scellement **session comité** réussit.
3. **Ne pas** émettre un second `EVALUATION_SEALED` pour le même geste si le projector score existe déjà — évite doublons `vendor_market_signals` pour le même pivot « prix ».
4. **`project_sealed_workspace`** insère des `price_anchor_update` **par bundle qualifié** (`qualification_status = 'qualified'`) avec `vendor_id` résolu, **indépendamment** de `is_retained`.

## Conséquences

- Deux chemins d’écriture **append-only** vers `vendor_market_signals` restent possibles mais **orthogonalux** : scores (événement M14) vs bundles qualifiés (post-seal comité). Surveillance métier si les deux coexistent sur un même workspace.
- Redis / `REDIS_URL` requis pour l’enqueue (dégradation silencieuse si indisponible — log warning).

## Alternatives rejetées

- **Unifier tout dans `workspace_events`** : exigerait un nouveau type `WORKSPACE_SEALED` + migration émetteurs — plus lourd pour le même sprint.
- **Supprimer `_project_evaluation_sealed`** : casserait les déploiements qui s’appuient sur M14.
