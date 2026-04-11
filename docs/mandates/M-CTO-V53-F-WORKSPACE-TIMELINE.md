# M-CTO-V53-F — Timeline workspace + mémoire `workspace_id` (event index)

**ID :** `M-CTO-V53-F`  
**Dépend de :** `M-CTO-V53-C` (guards cohérents pour nouvelles routes)  
**Bloque :** `M-CTO-V53-J`

---

## 1. Objectif

- Exposer une **timeline** alignée **workspace-first** : lecture depuis `dms_event_index` (et/ou `workspace_events`) par **`workspace_id`**, sans exiger `case_id` comme seule clé.  
- Sécuriser **`GET /views/case/.../timeline`** existant **ou** le remplacer par route sous `/api/workspaces/...` — **décision dans PR** documentée dans ADR court ou section PR body.  
- Préparer **mémoire** : nouvelles écritures `memory_entries` avec **`workspace_id`** si colonne absente → migration.

---

## 2. Périmètre fichiers — ALLOWLIST

### Créer

| Créer |
|-------|
| `alembic/versions/<new>_v53_workspace_timeline_memory.py` *(optionnel — **obligatoire** si ajout `workspace_id` sur `memory_entries` ou index)* |
| `src/api/routers/workspace_timeline.py` *(ou équivalent ; si route ajoutée dans fichier existant, **ne pas** créer ce fichier)* |
| `tests/api/test_workspace_timeline.py` |

### Modifier

| Chemin |
|--------|
| `src/memory/event_index_service.py` |
| `src/memory/event_index_models.py` |
| `src/api/views/case_timeline.py` |
| `src/api/app_factory.py` *(include_router uniquement — **minimal**)* |
| `src/annotation/memory/case_memory_writer.py` *(si branchement workspace_id pour écritures)* |
| `src/core/dependencies.py` *(si `add_memory` / lecture mémoire par case)* |
| `docs/ops/V51_ROUTE_GUARD_INVENTORY.md` |
| `docs/ops/WORKSPACE_ROUTES_CHECKLIST.md` *(si présent)* |

### INTERDIT

- Modifier migrations Alembic **existantes** (sauf le **nouveau** fichier révision).
- `services/annotation-backend/**`

---

## 3. Exigences sécurité

- Toute nouvelle route **doit** utiliser le même modèle que le bundle workspace : `get_current_user` + `acquire_with_rls` **ou** `get_connection` + `TenantContextMiddleware` **et** `require_workspace_access` pour `workspace_id` cible.  
- **Interdit** : endpoint timeline lisant tout l’index sans tenant.

---

## 4. Tests obligatoires

```bash
ruff check src tests
black --check src tests
pytest tests/api/test_workspace_timeline.py tests/memory/test_event_index_service.py -q
```

---

## 5. Definition of Done

- [ ] Au moins **une** route documentée OpenAPI : timeline par `workspace_id`.
- [ ] Test d’isolation : utilisateur A ne voit pas événements tenant B (si infra test le permet ; sinon skip documenté + test unitaire avec mock RLS).
- [ ] Branche `feat/M-CTO-V53-F`.

---

## 6. Commits (exemples)

```
feat(M-CTO-V53-F): workspace-scoped event timeline API
migration(M-CTO-V53-F): memory_entries workspace_id nullable index
test(M-CTO-V53-F): timeline route auth and RLS
docs(M-CTO-V53-F): route inventory workspace timeline
```

---

*Mandat exécutable — périmètre fermé.*
