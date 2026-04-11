# M-CTO-V53-I — Matrice cognitive E×permission (implémentation ou alignement doc)

**ID :** `M-CTO-V53-I`  
**Dépend de :** `M-CTO-V53-C`  
**Bloque :** `M-CTO-V53-J`

---

## 1. Objectif

Résoudre l’écart documenté dans `docs/architecture/dms_atlas_v1/P0_L2_cognitive_engine.md` : *pas de matrice 17×6 dans le dépôt* vs affirmations partielles du canon V5.1.

**Deux modes exclusifs** (choisir **un** dans la PR, validé CTO) :

| Mode | Action |
|------|--------|
| **I-impl** | Implémenter une matrice **réduite mais exécutable** : au minimum **toutes les routes d’écriture M16 / comité / documents** refusées si `cognitive_state` < seuil défini (réutiliser `m16_guard` dans `src/api/guards/m16_guards.py`). |
| **I-doc** | Amendement **canon / atlas** via processus ADR : « la matrice canonique large est reportée ; le comportement opposable est guards de transition + `m16_guard` uniquement » — **sans** toucher `DMS_V4.1.0_FREEZE.md`. |

---

## 2. Périmètre fichiers — ALLOWLIST

### Mode I-impl

| Modifier |
|----------|
| `src/api/guards/m16_guards.py` |
| `src/cognitive/cognitive_state.py` *(si extraction helpers)* |
| `src/api/cognitive_helpers.py` |
| `src/api/routers/workspaces.py` *(si centralisation helper)* |
| Fichiers routers **uniquement** si listés explicitement dans un tableau annexe PR (max 8 fichiers) : |

**Annexe PR (obligatoire)** : liste exhaustive des routers modifiés (ex. `src/api/routers/workspaces_comments.py`, `src/api/routers/committee_sessions.py`, …). Cette liste = **extension temporaire** du mandat ; copier la liste finale dans ce fichier mandat **avant merge** (amendement).

### Mode I-doc

| Créer |
|-------|
| `docs/adr/ADR-V53-COGNITIVE-MATRIX-SCOPE.md` |

| Modifier |
|----------|
| `docs/architecture/dms_atlas_v1/P0_L2_cognitive_engine.md` |
| `docs/freeze/DMS_CANON_V5.1.0_FREEZE.md` **uniquement** si processus amendement canon approuvé CTO ; sinon **interdit** |

> **Par défaut** : ne **pas** modifier `DMS_CANON_V5.1.0_FREEZE.md` ; préférer ADR + atlas.

### INTERDIT

- `services/annotation-backend/**`

---

## 3. Tests obligatoires (mode I-impl)

```bash
ruff check src tests
black --check src tests
pytest tests/cognitive/ tests/api/ -k "m16_guard or cognitive" -q
```

---

## 4. Definition of Done

- [ ] Mode choisi ; **aucun** flou « partiel ».  
- [ ] Si I-doc : pas de contradiction avec Kill List / CONTEXT_ANCHOR.  
- [ ] Branche `feat/M-CTO-V53-I`.

---

## 5. Commits (exemples)

```
feat(M-CTO-V53-I): enforce cognitive min state on committee write routes
docs(M-CTO-V53-I): ADR cognitive matrix deferred scope
```

---

*Mandat exécutable — périmètre fermé.*
