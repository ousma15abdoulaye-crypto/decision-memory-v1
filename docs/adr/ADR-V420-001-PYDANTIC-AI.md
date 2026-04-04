# ADR-V420-001 — PydanticAI pour les outils Pass -1

**Statut** : ACCEPTÉ  
**Date** : 2026-04-04  
**Auteur** : Abdoulaye Ousmane — CTO  
**Référence** : DMS V4.2.0 ADDENDUM §VIII — RÈGLE-13 (ADR obligatoire avant premier commit)

---

## Contexte

Le Pass -1 (assemblage ZIP → bundles fournisseurs) requiert des outils LLM typés :
- OCR de documents (Mistral OCR 3 + fallback Azure Document Intelligence)
- Classification de type de document (M12)
- Liaison fournisseur (link_vendor)
- Calcul de complétude (completeness_check)

Ces outils doivent être :
1. Déclarés avec des types Pydantic stricts (`extra=forbid` — invariant DMS)
2. Réutilisables dans LangGraph (toolcalling)
3. Observables via Langfuse (traçage du coût USD par workspace)

## Décision

Adopter **`pydantic-ai`** comme framework de définition des outils LLM dans le module `src/assembler/`.

```python
# Pattern d'outil PydanticAI — exemple complétude
from pydantic_ai import Agent, Tool
from pydantic import BaseModel

class CompletenessResult(BaseModel):
    model_config = {"extra": "forbid"}
    bundle_id: str
    score: float
    missing_documents: list[str]
    hitl_required: bool

completeness_tool = Tool(
    completeness_check,
    name="check_bundle_completeness",
    description="Calcule la complétude d'un bundle fournisseur"
)
```

## Raison du choix

| Critère | PydanticAI | Alternatives |
|---|---|---|
| Typage Pydantic natif | Oui (extra=forbid compatible) | LangChain : partiel |
| Intégration LangGraph | Compatible via toolcalling | — |
| Observabilité Langfuse | Via callbacks | — |
| Multimodal (OCR) | Oui (images, PDFs) | — |
| Maturité 2026 | Stable v0.x | — |

## Contraintes

- `extra=forbid` obligatoire sur tous les modèles (invariant DMS E-49)
- Aucun tool ne produit `winner / rank / recommendation / best_offer` (INV-W06, RÈGLE-09)
- Tous les tools sont rejouables (idempotence ARQ)
- Coût USD tracé dans `llm_traces` (migration 065)

## Version

```
pydantic-ai>=0.0.40  # à confirmer avant pip install — vérifier compatibility pydantic>=2.9.0
```

## Conséquences

- Ajout dans `requirements.txt` lors de Phase 4 (semaines 4-5)
- ADR-003 (LangGraph) complémentaire pour l'orchestration stateful
- Évaluation taille image Docker : +~15MB estimé

---

*RÈGLE-13 : ce fichier ADR doit exister avant tout `import pydantic_ai` dans le code source.*
