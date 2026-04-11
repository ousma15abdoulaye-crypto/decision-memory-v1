# Langfuse — mode strict (M-CTO-V53-H)

Variable : **`LANGFUSE_REQUIRED_FOR_LLM`** (bool, défaut `false`).

- Si **`true`** et **`TESTING` ≠ true** : absence de `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` → **échec au démarrage** du premier `get_langfuse()` (RuntimeError).
- Si **`false`** (défaut) : comportement historique — no-op si clés absentes.

Voir `src/core/config.py` et `src/agent/langfuse_client.py`.
