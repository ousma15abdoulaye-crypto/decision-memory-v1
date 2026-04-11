# Investigation — Assistant DMS bloqué / message « Guardrail INV-W06 » systématique

**Date (rapport)** : 2026-04-11  
**Périmètre** : route `POST /api/agent/prompt`, guardrail INV-W06, semantic router, console Next.js `AgentConsole`.

## Mise à jour — garde pré-LLM désactivée par défaut

Le blocage HTTP 422 **avant** tout appel LLM (intent RECOMMENDATION ≥ 0,85) est **désactivé par défaut** via `AGENT_INV_W06_PRE_LLM_BLOCK` (`false`). Enregistré en dette technique **TD-AGENT-01** dans [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md). Réactivation explicite : `AGENT_INV_W06_PRE_LLM_BLOCK=true`.

## Symptôme rapporté

Toute question à l’assistant affiche un bandeau du type :

`Guardrail INV-W06 — Requête bloquée par le guardrail INV-W06.`

alors que la requête ne semble pas être une demande de recommandation.

## Chaîne technique (référence code)

1. **Backend** — `src/api/routers/agent.py` : avant le stream SSE, `check_recommendation_guardrail` peut bloquer en 422 (si le flag pré-LLM est activé).
2. **Classification** — `src/agent/guardrail.py` → `src/agent/semantic_router.py` : centroïdes d’exemples + similarité cosinus ; seuil 0,85 sur RECOMMENDATION.
3. **Embeddings** — `src/agent/embedding_client.py` : sans `MISTRAL_API_KEY` ou sans SDK, mode fallback (vecteur déterministe).
4. **Frontend** — `frontend-v51/components/agent/agent-console.tsx` : les réponses **422** doivent distinguer guardrail (`detail` objet avec `error: guardrail_inv_w06`) et **validation Pydantic** (`detail` tableau avec `msg`).

## Cause principale identifiée : confusion des HTTP 422

En FastAPI, le code **422** sert à la fois au guardrail (objet `detail`) et aux erreurs de validation (tableau `detail`). Un front qui lit seulement `detail.message` tombe sur un repli texte et affiche « INV-W06 » à tort. Le parseur structuré dans `agent-console.tsx` corrige cela.

## Vérifications recommandées

1. Onglet Réseau : corps JSON du 422.
2. `workspace_id` : UUID valide si présent.
3. `MISTRAL_API_KEY` et logs embedding en prod.
4. Langfuse : traces `guardrail_inv_w06` si blocage réel.

## Fichiers concernés

- `src/api/routers/agent.py`, `src/agent/guardrail.py`, `src/core/config.py`
- `frontend-v51/components/agent/agent-console.tsx`
