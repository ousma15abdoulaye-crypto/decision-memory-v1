# DMS — Document B : Pipeline annotation multipasses — Architecture post-M12

**Référence** : DMS-ANNOTATION-MULTIPASS-POST-M12-B  
**Statut** : opposable — **périmètre actif** : clôture Document A constatée (**22** `annotated_validated`, corpus **Cloudflare R2**). Voir [DMS_M12_CORPUS_GATE_EXECUTION.md](./DMS_M12_CORPUS_GATE_EXECUTION.md).  
**Date** : 2026-03-24  
**Subordonné à** : [DMS_V4.1.0_FREEZE.md](../freeze/DMS_V4.1.0_FREEZE.md), [DMS_ORCHESTRATION_FRAMEWORK_V1.md](../freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md)

---

## Objet

Industrialiser l’annotation selon la doctrine :

`Pass 0 ingestion → Pass 0.5 quality gate → Pass 1 router → … → review humaine → annotated_validated`

le gate corpus minimal (**15**) est **franchi** (22 documents) ; cette trajectoire est la suite canonique post-gate.

---

## Artefacts normatifs (repo)

| Artefact | Chemin | Rôle |
| --- | --- | --- |
| Contrat sortie passe | [PASS_OUTPUT_STANDARD.md](../contracts/annotation/PASS_OUTPUT_STANDARD.md) | Enveloppe commune + schéma Pydantic |
| Pass 0 | [PASS_0_INGESTION_CONTRACT.md](../contracts/annotation/PASS_0_INGESTION_CONTRACT.md) | Normalisation, page_map, pas de décision métier |
| Pass 0.5 | [PASS_0_5_QUALITY_GATE_CONTRACT.md](../contracts/annotation/PASS_0_5_QUALITY_GATE_CONTRACT.md) | `good \| degraded \| poor \| ocr_failed` + seuils |
| Pass 1 | [PASS_1_ROUTER_CONTRACT.md](../contracts/annotation/PASS_1_ROUTER_CONTRACT.md) | Router déterministe + LLM si besoin |
| Context pack amont | [UPSTREAM_CONTEXT_PACK_STANDARD.md](../contracts/annotation/UPSTREAM_CONTEXT_PACK_STANDARD.md) | Couche B + métadonnées document |
| FSM orchestrateur | [ANNOTATION_ORCHESTRATOR_FSM.md](../contracts/annotation/ANNOTATION_ORCHESTRATOR_FSM.md) | États, transitions, timeouts |
| Migration monolithe | [ANNOTATION_BACKEND_MIGRATION_STRATEGY.md](../contracts/annotation/ANNOTATION_BACKEND_MIGRATION_STRATEGY.md) | Strangler 4 phases |
| Seuils empiriques 0.5 | [PASS_0_5_EMPIRICAL_THRESHOLDS.md](../contracts/annotation/PASS_0_5_EMPIRICAL_THRESHOLDS.md) | Méthode + valeurs provisoires |
| Coût LLM | [LLM_COST_MODEL_ANNOTATION.md](../contracts/annotation/LLM_COST_MODEL_ANNOTATION.md) | Budget document / tokens |
| Intégration Couche B | `src/annotation/context_pack.py` | Assemblage `UpstreamContextPack` |

---

## Ordre d’exécution (post-M12 gate)

1. **Contrats** : lire PASS_OUTPUT_STANDARD + contrats Pass 0 / 0.5 / 1 + UPSTREAM_CONTEXT_PACK.
2. **FSM** : implémenter orchestrateur conforme [ANNOTATION_ORCHESTRATOR_FSM.md](../contracts/annotation/ANNOTATION_ORCHESTRATOR_FSM.md) (état persistable recommandé : DB ou fichier d’audit selon mandat).
3. **Passes** : bibliothèques pures sous `src/annotation/passes/` (sans dépendance LS dans la logique métier).
4. **Adapter LS** : `backend.py` reste le point d’entrée Label Studio jusqu’à phase 4 de la stratégie migration.
5. **Baseline** : métriques Gate Policy (extraction, temps, `review_required`, `unresolved`, qualité structurelle) après corpus ≥ seuils.
6. **OpenRouter / Claude** : **uniquement** après ADR + baseline si la preuve l’exige (pas sur le chemin critique M12).

---

## Interdits (alignement V4.1)

- Big bang `backend.py` sans phase strangler documentée.
- API LLM externe / nouvelle dépendance **sans** ADR ([docs/adr/](../adr/)).
- Appels API réels en CI (mocks obligatoires).
- `winner` / `rank` / `recommendation` / `best_offer` (RÈGLE-09).

---

## Index M12

- Gate immédiat : [DMS_M12_CORPUS_GATE_EXECUTION.md](./DMS_M12_CORPUS_GATE_EXECUTION.md)
- Workflow AO : [M12_AO_WORKFLOW.md](./M12_AO_WORKFLOW.md)
- Export : [M12_EXPORT.md](./M12_EXPORT.md)
