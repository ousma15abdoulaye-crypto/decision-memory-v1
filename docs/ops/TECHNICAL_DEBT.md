# Dette technique — registre opérationnel

Liste courte des écarts volontaires par rapport au canon documenté, avec critères de résolution.

| ID | Sujet | État | Critère de levée |
|----|--------|------|-------------------|
| TD-AGENT-01 | **Guardrail pré-LLM INV-W06** (`check_recommendation_guardrail`) : blocage HTTP 422 quand l’intent sémantique est RECOMMENDATION avec similarité ≥ 0,85 | **Désactivé par défaut** (`AGENT_INV_W06_PRE_LLM_BLOCK=false`) | Routeur sémantique + embeddings Mistral stables en prod ; taux acceptable de faux positifs ; validation produit / juridique. Réactivation : `AGENT_INV_W06_PRE_LLM_BLOCK=true`. |

**Non régressé par cette dette :** filtrage de sortie (`src/agent/output_filter.py`), interdiction winner/rank dans les payloads API / PV / M16, contraintes DB — invariant INV-W06 hors ce garde-fou pré-LLM.

**Références :** `src/agent/guardrail.py`, `src/core/config.py`, `docs/ops/INV_W06_ASSISTANT_BLOCKED_INVESTIGATION.md`.
