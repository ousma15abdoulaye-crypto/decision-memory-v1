# M-CTO-V53-J — CI, gates, inventaire final, clôture MRD (sous contrôle AO)

**ID :** `M-CTO-V53-J`  
**Dépend de :** `M-CTO-V53-B` through `I` (au minimum **A+B+C+E** mergés ou explicitement reportés dans registre écarts)  
**Bloque :** rien (clôture programme)

---

## 1. Objectif

- Renforcer la **CI** pour détecter régressions de souveraineté : imports morts (RAG), double SQL marché, routes non inventoriées.  
- Mettre à jour **`docs/freeze/MRD_CURRENT_STATE.md`** : **seulement si mandat AO** — sinon créer **`docs/audit/V53_CLOSEOUT_PENDING_MRD.md`** listant deltas pour AO.

---

## 2. Périmètre fichiers — ALLOWLIST

| Modifier |
|----------|
| `.github/workflows/ci-v52-gates.yml` |
| `.github/workflows/ci-main.yml` *(si gate doit vivre ici — **minimal**)* |
| `scripts/validate_mrd_state.py` *(si script existe et doit référencer nouveaux checks)* |
| `docs/ops/V51_ROUTE_GUARD_INVENTORY.md` |
| `docs/audit/V53_CI_GATES.md` *(créer — registre des nouveaux jobs)* |
| `docs/audit/V53_CLOSEOUT_PENDING_MRD.md` *(créer si AO non disponible)* |
| `docs/freeze/MRD_CURRENT_STATE.md` *(**uniquement** avec validation AO explicite dans le corps de PR)* |

### Créer

| Créer |
|-------|
| `docs/audit/V53_CI_GATES.md` |
| `docs/audit/V53_CLOSEOUT_PENDING_MRD.md` *(conditionnel)* |
| `scripts/check_v53_sovereignty_grep.py` *(optionnel — script grep CI ; nom exact flexible)* |

### INTERDIT

- `docs/freeze/CONTEXT_ANCHOR.md` *(réservé AO — RÈGLE-ANCHOR-01)* sauf **session AO** dédiée.
- `docs/freeze/DMS_V4.1.0_FREEZE.md`

---

## 3. Gates CI suggérées (à implémenter au moins **2**)

1. **Grep** : `from src.memory.rag_service import` hors `tests/` → **fail** si Option B G2 choisie.  
2. **Grep** : `FROM vendor_market_signals` dans `src/` sans commentaire `# ADR-V53` (exemple) → **warning** ou **fail** selon politique.  
3. **OpenAPI** : route timeline workspace présente si mandat F merged.

---

## 4. Tests / exécution

```bash
# Local
ruff check src tests
black --check src tests
pytest tests/ -q --maxfail=1  # ou subset défini dans workflow
```

---

## 5. Definition of Done

- [ ] Workflow CI mis à jour ; PR verte.  
- [ ] `V53_CI_GATES.md` décrit chaque job.  
- [ ] MRD ou `V53_CLOSEOUT_PENDING_MRD.md` **l’un des deux** mis à jour.  
- [ ] Branche `feat/M-CTO-V53-J`.

---

## 6. Commits (exemples)

```
ci(M-CTO-V53-J): v53 sovereignty grep gates
docs(M-CTO-V53-J): V53 CI gates registry and MRD closeout
```

---

*Mandat exécutable — périmètre fermé.*
