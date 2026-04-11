# M-CTO-V53-G — Brancher `m12_correction_log` + trancher RAG (`RAGService` / pgvector)

**ID :** `M-CTO-V53-G`  
**Dépend de :** `M-CTO-V53-A`  
**Bloque :** `M-CTO-V53-J`

---

## 1. Objectif (deux volets — **les deux** doivent être clos par décision binaire)

### Volet G1 — M12 corrections

- **Écriture** : au moins **un** chemin runtime (route API interne **ou** hook pipeline post-validation) appelle `M12CorrectionWriter` (`src/procurement/m12_correction_writer.py`).  
- **Lecture** : endpoint **audit** (permission `audit.read` ou `mql.internal` / `system.admin` selon canon) **ou** export documenté.

### Volet G2 — RAG

- **Option A** : brancher `process_info_handler` (`src/agent/handlers.py`) sur `RAGService` + corpus documenté + feature flag `Settings`.  
- **Option B** : retirer `RAGService` du dépôt **ou** le déplacer sous `tests/` / marquer module **deprecated** avec CI grep interdisant import production — **sans** laisser pgvector « décoratif ».

**Le CTO coche A ou B dans la PR** ; pas d’option floue.

---

## 2. Périmètre fichiers — ALLOWLIST

### Volet G1 — fichiers

| Créer |
|-------|
| `src/api/routers/m12_corrections.py` *(préfixe API à aligner sur `app_factory`)* |
| `tests/api/test_m12_corrections_router.py` |

| Modifier |
|----------|
| `src/procurement/m12_correction_writer.py` *(imports / compat async si nécessaire — minimal)* |
| `src/api/app_factory.py` *(include_router)* |
| `docs/ops/V51_ROUTE_GUARD_INVENTORY.md` |

### Volet G2 — fichiers (Option A)

| Modifier |
|----------|
| `src/agent/handlers.py` |
| `src/memory/rag_service.py` |
| `src/memory/embedding_service.py` |
| `src/core/config.py` *(flags RAG)* |
| `tests/memory/test_rag_service.py` |
| `tests/unit/test_agent_handlers.py` *(créer si absent)* |

### Volet G2 — fichiers (Option B)

| Modifier / Déplacer / Supprimer |
|--------------------------------|
| `src/memory/rag_service.py` |
| `tests/memory/test_rag_service.py` |
| `.github/workflows/ci-v52-gates.yml` ou workflow approprié *(grep dead code)* |

### Documentation décision RAG (obligatoire)

| Créer |
|-------|
| `docs/audit/V53_RAG_DECISION.md` |

### INTERDIT

- `services/annotation-backend/prompts/schema_validator.py` (gel)
- Toute modification **non listée**

---

## 3. Tests obligatoires

```bash
ruff check src tests
black --check src tests
pytest tests/procurement/test_m12_correction_writer.py tests/api/test_m12_corrections_router.py -q
# Si Option A:
pytest tests/memory/test_rag_service.py tests/unit/test_agent_handlers.py -q
```

---

## 4. Definition of Done

- [ ] G1 : au moins **un** INSERT runtime testé (API ou service appelé depuis pipeline mock).  
- [ ] G2 : **A ou B** documenté dans `docs/audit/V53_RAG_DECISION.md`.

---

## 5. Commits (exemples)

```
feat(M-CTO-V53-G): m12 correction log API write path
test(M-CTO-V53-G): m12 correction writer integration
feat(M-CTO-V53-G): wire process_info to RAGService
# ou
refactor(M-CTO-V53-G): remove unused RAGService from production path
```

---

*Mandat exécutable — périmètre fermé.*
