# P2 — Livrable 6 : Moteur MQL

## 1. Constat — dénomination « MQL »

Une recherche sur le dépôt (**nom « MQL » / templates T1–T6**) ne retourne **pas** de module, route ou dossier ainsi nommé dans `src/` ou `docs/` au moment de la rédaction.

**Conclusion** : **NON IMPLÉMENTÉ sous le label « MQL V7 »** dans ce repository — ou le canon utilise une appellation externe non reflétée dans le code.

---

## 2. Équivalents fonctionnels probables (à valider métier)

| Besoin mandat | Implémentation rapprochée dans le dépôt |
|---------------|----------------------------------------|
| Requêtes marché / enquêtes | [`src/api/routers/market.py`](../../src/api/routers/market.py), tables `market_surveys`, `survey_campaigns`, `market_signals_v2` (migrations `042`, `043`) |
| Règles candidates / promotions | Tables `candidate_rules`, `rule_promotions` — [`063_candidate_rules.py`](../../alembic/versions/063_candidate_rules.py) |
| Recherche sémantique / embeddings | [`src/memory/rag_service.py`](../../src/memory/rag_service.py), table `dms_embeddings` — [`064_dms_embeddings.py`](../../alembic/versions/064_dms_embeddings.py) |
| Traces LLM | Table `llm_traces` — [`065_llm_traces.py`](../../alembic/versions/065_llm_traces.py) |

---

## 3. Templates SQL T1–T6

**NON IMPLÉMENTÉ** comme jeu nommé T1–T6 dans le dépôt — aucun fichier référencé dans les migrations grep initiales sous cette convention.

---

## 4. « Semantic Router » (mandat)

- **Embeddings** : [`src/memory/embedding_service.py`](../../src/memory/embedding_service.py) — backend BGE-M3 ou stub selon config.
- **Centroïdes d’intent / seuil 0.85 / matrice de confusion** : **NON TRANCHÉ** — pas de fichier unique décrivant ces paramètres ; recherche par `embedding` dans `src/memory/`.

---

## 5. Orchestrateur streaming / SSE / Redis context

- **WebSocket workspace** : [`src/api/ws/workspace_events.py`](../../src/api/ws/workspace_events.py) — diffusion `workspace_events` (pas SSE générique MQL).
- **Redis** : cache rate limit + middleware — [`src/couche_a/auth/middleware.py`](../../src/couche_a/auth/middleware.py), [`src/ratelimit.py`](../../src/ratelimit.py).
- **Langfuse** : **NON** trouvé comme chaîne obligatoire ; traces DB `llm_traces` à la place.

---

## 6. Limitations

Si le canon V4.4 décrit un **service MQL hors monorepo**, ce livrable **ne peut pas** documenter son code — indiquer **« hors dépôt »**.
