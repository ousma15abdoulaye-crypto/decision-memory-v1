# M-CTO-V53-E — Réconciliation historique M16 (E18)

**ID :** `M-CTO-V53-E`  
**Dépend de :** `M-CTO-V53-A` (matrice écrivains/lecteurs à jour)  
**Bloque :** `M-CTO-V53-D` (PV / API ne doivent pas lire deux timelines contradictoires)

---

## 1. Objectif

Fermer **E18** (`V52_RECONSTRUCTION_COMPLETE.md`) : **une** timeline d’audit des changements de scores M16 côté API/PV, avec stratégie **additive** (pas de perte de données).

**Décision architecturale** : à trancher dans un ADR créé dans ce mandat :

- **Option 1 (recommandée)** : `assessment_history` = **canon** pour nouvelles lectures ; `criterion_assessment_history` = **vue** ou table **legacy read-only** alimentée par trigger existant ou backfill one-shot.  
- **Option 2** : inverse (moins probable si V52 a déjà renforcé `assessment_history`).

---

## 2. Périmètre fichiers — ALLOWLIST

### Créer

| Créer |
|-------|
| `docs/adr/ADR-V53-ASSESSMENT-HISTORY-UNIFICATION.md` |
| `alembic/versions/<new>_v53_assessment_history_unify.py` *(un seul fichier ; nom révision = slug CTO)* |

### Modifier

| Modifier |
|----------|
| `src/services/m16_evaluation_service.py` |
| `src/api/routers/m16_comparative.py` *(routes `m16_assessment_history` et apparentées)* |
| `tests/integration/test_m16_rls_isolation.py` |
| `tests/db/test_v51_assessment_history_rls.py` |
| `tests/cognitive/` ou `tests/m16/` *(fichiers existants touchant historique)* — **uniquement** fichiers déjà listés par grep ci-dessous ou ajoutés explicitement ici : |

**Fichiers tests à ajuster si présents dans la PR (liste indicative — grep avant merge) :**

- Tout test qui assert sur `criterion_assessment_history` en isolation.

### Créer tests

| Créer |
|-------|
| `tests/db/test_assessment_history_unification.py` *(ou `tests/integration/test_assessment_history_unified.py`)* |

### INTERDIT

- Modifier **révisions Alembic existantes** sous `alembic/versions/` autres que le **nouveau** fichier.
- `services/annotation-backend/**`

---

## 3. Exigences migration (si Option vue)

- `upgrade()` / `downgrade()` **obligatoires**.  
- Pas de `DROP TABLE` sur données métier sans **copie** ou **période double-read** documentée dans l’ADR.  
- RLS : si nouvelle vue, policies **héritées** ou explicites — valider avec test tenant isolation.

---

## 4. Tests obligatoires

```bash
ruff check src tests
black --check src tests
pytest tests/db/test_v51_assessment_history_rls.py tests/db/test_assessment_history_unification.py -q
pytest tests/integration/test_m16_rls_isolation.py -q
```

---

## 5. Definition of Done

- [ ] ADR Accepted + migration appliquée en **local** / CI DB job si présent.
- [ ] `m16_evaluation_service` : **une** source pour `list_assessment_history` / count (plus de double SQL contradictoire sans commentaire « deprecated »).
- [ ] PR `feat/M-CTO-V53-E` ; CI verte.

---

## 6. Commits (exemples)

```
migration(M-CTO-V53-E): v53 assessment history unify view
feat(M-CTO-V53-E): m16 evaluation service single timeline read
test(M-CTO-V53-E): RLS and unified history integration
docs(M-CTO-V53-E): ADR-V53 assessment history unification
```

---

*Mandat exécutable — périmètre fermé.*
