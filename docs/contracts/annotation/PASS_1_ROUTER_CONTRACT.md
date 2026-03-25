# PASS_1_ROUTER_CONTRACT

**Passe** : `pass_1_router`  
**Version** : `1.0.0`  
**Enveloppe** : [PASS_OUTPUT_STANDARD.md](./PASS_OUTPUT_STANDARD.md)

---

## Rôle

- Absorber le **classifieur déterministe** existant : [`src/annotation/document_classifier.py`](../../../src/annotation/document_classifier.py).
- Produire pour le pipeline aval :
  - `document_role`
  - `taxonomy_core`
  - `routing_confidence`
  - `routing_source` : `deterministic_classifier` \| `llm_proposal_validated` \| `llm_proposal_unresolved` \| `human`

**Ordre** : déterministe d’abord ; LLM ensuite **uniquement** si mandat + Pass 0.5 n’a pas posé `block_llm`.

---

## `output_data`

```json
{
  "document_role": "<str>",
  "taxonomy_core": "<str>",
  "routing_confidence": 0.0,
  "routing_source": "<str>",
  "matched_rule": "<str>",
  "deterministic": true
}
```

Les valeurs `document_role` / `taxonomy_core` **doivent** rester alignées sur les enums du classifieur et du schéma DMSAnnotation (liste fermée — INV-06).

---

## `metadata` recommandé

- `model_used` : si appel LLM ; sinon omis ou `null`.
- `prompt_version` : si LLM.

---

## `status`

- `success` : routing résolu (déterministe ou LLM validé).
- `degraded` : `UNKNOWN` avec `review_required` implicite pour l’étape humaine.
- `failed` : erreur technique ; pas de routing fiable.
