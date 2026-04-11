# M-CTO-V53-C — RBAC un guichet + politique JWT fallback

**ID :** `M-CTO-V53-C`  
**Dépend de :** `M-CTO-V53-A` (recommandé ; peut être parallèle à B si aucun conflit de fichiers — **éviter** merge simultané sur `guard.py`)  
**Bloque :** `M-CTO-V53-F`, `M-CTO-V53-H`

---

## 1. Objectif

- Réduire **E07** : une **matrice de permissions** canonique (`src/auth/permissions.py`) appliquée de façon **prévisible** par `guard()` et chemins workspace.  
- **Documenter et durcir** `WORKSPACE_ACCESS_JWT_FALLBACK` : défaut `false` prod ; logs ; périmètre **explicite** des permissions **non** couvertes (cf. CONTEXT_ANCHOR addendum JWT pilote).

---

## 2. Périmètre fichiers — ALLOWLIST

| Modifier |
|----------|
| `src/auth/guard.py` |
| `src/auth/permissions.py` |
| `src/couche_a/auth/workspace_access.py` |
| `src/core/config.py` |
| `docs/ops/WORKSPACE_ACCESS_JWT_FALLBACK_TERRAIN.md` |
| `docs/ops/V51_ROUTE_GUARD_INVENTORY.md` |
| `tests/unit/test_workspace_access_jwt_fallback.py` |
| `tests/unit/test_guard.py` *(créer si absent pour scénarios centralisés)* |

### Créer (si besoin binaire)

| Créer |
|-------|
| `tests/unit/test_guard_matrix.py` |

### INTERDIT

- Tous les routers sauf si **amendement CTO** (ce mandat **ne** inclut **pas** `m16_guard` / `committee_sessions` — traiter dans mandat annexe si nécessaire).
- `services/annotation-backend/**`

---

## 3. Exigences fonctionnelles

1. **Table unique** : toute nouvelle permission ou rôle passe par `ROLE_PERMISSIONS` dans `permissions.py` ; `guard()` ne duplique pas de matrice en dur.  
2. **Fallback JWT** : si `WORKSPACE_ACCESS_JWT_FALLBACK=true`, journaliser **WARN** avec `user_id`, `workspace_id`, `role` ; documenter dans le runbook que **`require_rbac_permission` / M16 écriture** ne sont pas équivalents (reprendre texte anchor).  
3. **Inventaire** : mettre à jour `V51_ROUTE_GUARD_INVENTORY.md` avec état post-changement (sections « guard unifié », « fallback »).

---

## 4. Tests obligatoires

```bash
ruff check src tests
black --check src tests
pytest tests/unit/test_workspace_access_jwt_fallback.py tests/unit/test_guard*.py -q
```

---

## 5. Definition of Done

- [ ] Aucune régression sur tests auth existants.
- [ ] Runbook à jour (procédure activation/désactivation fallback).
- [ ] Branche `feat/M-CTO-V53-C` ; PR unique.

---

## 6. Commits (exemples)

```
fix(M-CTO-V53-C): centralize permission checks in guard
docs(M-CTO-V53-C): JWT fallback scope and inventory update
test(M-CTO-V53-C): guard matrix regression
```

---

*Mandat exécutable — périmètre fermé.*
