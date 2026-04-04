# ADR-V420-002 — LangGraph pour l'orchestration stateful Pass -1

**Statut** : ACCEPTÉ  
**Date** : 2026-04-04  
**Auteur** : Abdoulaye Ousmane — CTO  
**Référence** : DMS V4.2.0 ADDENDUM §VIII — RÈGLE-13

---

## Contexte

Le Pass -1 est un pipeline stateful avec interruption humaine possible (HITL) :

```
extract → classify → link_vendor → completeness_check → [HITL interrupt?] → finalize
```

L'état doit être :
1. Persisté en PostgreSQL (checkpoint rejouable — idempotence ARQ)
2. Interruptible (bundle incomplet → HITL → reprise sans réexécuter l'OCR)
3. Observable (Langfuse tracing à chaque nœud)

## Décision

Adopter **LangGraph** avec `AsyncPostgresSaver` pour l'orchestration stateful du Pass -1.

```python
# Pattern LangGraph Pass -1 — squelette
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

class PassMinusOneState(TypedDict):
    workspace_id: str
    zip_path: str
    raw_documents: list[dict]
    bundles: list[dict]
    hitl_required: bool
    finalized: bool

graph = StateGraph(PassMinusOneState)
graph.add_node("extract", extract_node)
graph.add_node("classify", classify_node)
graph.add_node("bundle", bundle_node)
graph.add_node("hitl_check", hitl_check_node)
graph.add_node("finalize", finalize_node)

graph.add_edge("extract", "classify")
graph.add_edge("classify", "bundle")
graph.add_conditional_edges("bundle", route_hitl, {
    "hitl": "hitl_check",
    "ok": "finalize",
})
graph.add_edge("finalize", END)
```

## Checkpoint PostgreSQL

```python
# AsyncPostgresSaver utilise DATABASE_URL existant
# Pas de nouvelle table : LangGraph crée ses propres tables de checkpoint
async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as saver:
    compiled = graph.compile(checkpointer=saver)
    config = {"configurable": {"thread_id": workspace_id}}
    await compiled.ainvoke(initial_state, config=config)
```

## Interruption HITL

```python
# Nœud HITL — interrompt le graph et attend résolution humaine
from langgraph.types import interrupt

async def hitl_check_node(state: PassMinusOneState):
    if state["hitl_required"]:
        resolved = await interrupt({
            "workspace_id": state["workspace_id"],
            "message": "Bundle incomplet — intervention requise",
        })
        return {"hitl_required": False, **resolved}
    return state
```

## Raison du choix vs ARQ seul

| Critère | LangGraph + ARQ | ARQ seul |
|---|---|---|
| Persistance état inter-étapes | Oui (PostgreSQL checkpoint) | Non (ARQ = job atomique) |
| HITL natif | Oui (interrupt()) | Non (workaround complexe) |
| Rejouabilité partielle | Oui (reprend au nœud après checkpoint) | Non (recommence tout) |
| Observabilité nœud par nœud | Oui (Langfuse per-node) | Partiel |

ARQ reste utilisé pour enqueue les jobs Pass -1 (`run_pass_minus_1`) et les projectors Couche B.

## Contraintes

- `AsyncPostgresSaver` requiert PostgreSQL 14+ (disponible — Railway PG 15+)
- Connexions LangGraph : 3 dans le pool (plan allocation §VIII)
- Aucun nœud ne produit winner/rank/recommendation (INV-W06)
- Chaque nœud est idempotent (rejouable sans effet de bord)

## Version

```
langgraph>=0.2.0  # à confirmer avant pip install — tester compatibility avec arq==0.26.1
```

## Conséquences

- Ajout dans `requirements.txt` lors de Phase 4
- Tables LangGraph checkpoint créées automatiquement (pas via Alembic — pas de migration dédiée)
- Taille image Docker : +~40MB estimé (dépendance langchain-core transitive)

---

*RÈGLE-13 : ce fichier ADR doit exister avant tout `import langgraph` dans le code source.*
