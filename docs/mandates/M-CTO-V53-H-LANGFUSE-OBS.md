# M-CTO-V53-H — Langfuse : politique prod + métadonnées (coût, run, couverture)

**ID :** `M-CTO-V53-H`  
**Dépend de :** `M-CTO-V53-C`  
**Bloque :** `M-CTO-V53-J`

---

## 1. Objectif

- Tracer **de façon homogène** : extraction (`src/extraction/engine.py`), agent (`src/api/routers/agent.py`, `src/agent/handlers.py`), MQL param extraction (`src/mql/param_extractor.py` si LLM).  
- Définir en **configuration** le comportement si clés Langfuse absentes : **strict** (fail startup en prod) vs **degraded** (no-op) — **décision CTO** alignée canon V5.1 INV-A01 vs contraintes ops.

---

## 2. Périmètre fichiers — ALLOWLIST

| Modifier |
|----------|
| `src/core/config.py` |
| `src/agent/langfuse_client.py` |
| `src/extraction/engine.py` |
| `src/api/routers/agent.py` |
| `src/mql/param_extractor.py` |
| `src/agent/semantic_router.py` *(si spans manquants)* |
| `docs/ENVIRONMENT_STATUS_REPORT.md` **ou** un fichier unique sous `docs/ops/` décrivant les secrets Langfuse — **un seul** fichier doc |
| `tests/unit/test_langfuse_policy.py` *(créer)* |

### Créer

| Créer |
|-------|
| `tests/unit/test_langfuse_policy.py` |

### INTERDIT

- `services/annotation-backend/**`

---

## 3. Exigences métadonnées (minimum)

Sur chaque trace ou span critique : `workspace_id` si applicable, `tenant_id` (hash ou id selon politique privacy), `model`, **tokens** si API Mistral les expose, **USD** si calculé ou renvoyé par provider.

---

## 4. Tests obligatoires

```bash
ruff check src tests
black --check src tests
pytest tests/unit/test_langfuse_policy.py -q
```

---

## 5. Definition of Done

- [ ] Document ops : variable(s) env pour politique **strict/degraded**.  
- [ ] Test : avec clés vides + `TESTING=true` → comportement attendu ; avec flag strict mock → startup fail (si implémenté).  
- [ ] Branche `feat/M-CTO-V53-H`.

---

## 6. Commits (exemples)

```
feat(M-CTO-V53-H): langfuse strict mode for production env
test(M-CTO-V53-H): langfuse policy unit tests
docs(M-CTO-V53-H): document LANGFUSE_REQUIRED and metadata
```

---

*Mandat exécutable — périmètre fermé.*
