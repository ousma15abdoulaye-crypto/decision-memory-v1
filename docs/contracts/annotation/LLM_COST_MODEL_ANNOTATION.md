# LLM_COST_MODEL_ANNOTATION — Coût par document (pré-OpenRouter)

**Version** : `1.0.0`  
**Date** : 2026-03-24  
**Implémentation** : [`src/annotation/llm_cost_model.py`](../../../src/annotation/llm_cost_model.py)

---

## 1. Objectif

Estimer **en amont** le coût token / USD d’une passe LLM pour :

- éviter les documents anomaliques qui vident le budget ;
- comparer Mistral vs autres fournisseurs **après** baseline (OpenRouter / ADR).

---

## 2. Modèle simplifié (Mistral)

Hypothèses configurables via variables d’environnement (pas d’appel API, valeurs par défaut définies dans le code Python) :

- `MISTRAL_USD_PER_1M_INPUT_TOKENS` — défaut conservateur à mettre à jour selon grille Mistral officielle.
- `MISTRAL_USD_PER_1M_OUTPUT_TOKENS` — idem.
- Estimation tokens : **approximation** `chars / 4` (documentée comme borne, pas comme facture).

**Formule** :

```
cost_usd ≈ (prompt_tokens * PIN + completion_tokens * POUT) / 1_000_000
```

---

## 3. Budget document

| Paramètre | Défaut suggéré | Action si dépassement |
| --- | ---: | --- |
| `max_prompt_tokens_per_document` | 120_000 | Troncature Pass 0 (déjà `MAX_TEXT_CHARS` côté backend) |
| `max_completion_tokens` | 32_000 | Aligné backend Mistral |
| `max_usd_per_document` | **null** (désactivé) | Si défini → `review_required` / refus LLM |

---

## 4. Traçabilité

Les estimations doivent être copiées dans `AnnotationPassOutput.metadata` :

- `token_count_prompt_est`
- `token_count_completion_est`
- `cost_estimate_usd`

Les **coûts réels** (si API retourne usage) remplacent les estimations quand disponibles.

---

## 5. OpenRouter / multi-provider

Hors scope de ce document jusqu’à ADR. Étendre `llm_cost_model.py` avec table `provider -> (pin, pout)` sans casser les tests (valeurs mockées).
