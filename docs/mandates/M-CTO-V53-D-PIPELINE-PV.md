# M-CTO-V53-D — Pipeline M12→M14→M16→PV (assembleur, M13 persisté, snapshot enrichi)

**ID :** `M-CTO-V53-D`  
**Dépend de :** `M-CTO-V53-B` (marché PV cohérent), `M-CTO-V53-E` (historique unique)  
**Bloque :** `M-CTO-V53-J`

---

## 1. Objectif

1. **Assembleur canonique** `offers[]` / entrées M14 depuis `supplier_bundles` + documents workspace (ferme la faille addendum V4.2 §1.1).  
2. **Persistance M13** blueprint / rapport réglementaire (R7) — schéma + service + lien workspace.  
3. **PV / snapshot** : intégrer **decision_snapshots**, **score_history** (ou équivalent post-E), **decision_history** (R2/R4/R6) selon faisabilité **dans le périmètre fichier**.

---

## 2. Périmètre fichiers — ALLOWLIST

### Créer (selon besoin — tous optionnels jusqu’à décision CTO dans PR ; **au moins un** des blocs A/B/C doit être livré)

| Créer (bloc A — assembleur) |
|-----------------------------|
| `src/procurement/m14_workspace_assembler.py` |
| `tests/procurement/test_m14_workspace_assembler.py` |

| Créer (bloc B — M13 persistence) |
|----------------------------------|
| `alembic/versions/<new>_v53_m13_blueprint_persist.py` |
| `src/procurement/m13_persistence_service.py` |
| `tests/procurement/test_m13_persistence.py` |

| Créer (bloc C — PV enrichi) |
|------------------------------|
| `tests/services/test_pv_builder_v53_snapshot.py` |

### Modifier

| Chemin |
|--------|
| `src/procurement/m14_engine.py` *(si nécessaire pour interface assembleur)* |
| `src/procurement/m14_evaluation_repository.py` |
| `src/procurement/handoff_builder.py` *(si la construction d’entrée M14 est centralisée ici)* |
| `src/services/m14_bridge.py` |
| `src/services/pipeline_v5_service.py` *(enchaînement bundles → M13 → M14 — point critique assembleur)* |
| `src/services/pv_builder.py` |
| `src/api/routes/evaluation.py` *(routes `/api/m14`)* |
| `src/api/routers/pipeline_v5.py` |
| `src/api/routers/workspaces.py` *(endpoint workspace lié à M14 si touché)* |
| `src/api/routers/m16_comparative.py` *(sync-from-m14 / bridge — si impacté par assembleur)* |

**Fichier M14 router :** il n’existe pas `src/api/routers/m14_*.py` ; l’API M14 est **`src/api/routes/evaluation.py`**.

**Tout autre fichier** (ex. `src/api/app_factory.py`) : **hors mandat** sauf **amendement CTO** explicite.

### INTERDIT

- `services/annotation-backend/backend.py` (gel)
- `src/annotation/orchestrator.py` hors **mandat dégel** séparé

---

## 3. Jalons internes (sous-PR interdits — un seul mandat = une PR ; utiliser commits logiques)

| Sous-jalon | Preuve |
|------------|--------|
| D-a | Test unitaire : workspace fixture → structure `offers[]` stable |
| D-b | Migration + INSERT/SELECT M13 blueprint par `workspace_id` |
| D-c | Test `pv_builder` : snapshot contient clés `decision_snapshots` / `score_history` **si** colonnes/tables présentes |

---

## 4. Tests obligatoires

```bash
ruff check src tests
black --check src tests
pytest tests/procurement/ tests/services/test_pv_builder.py tests/services/test_pv_builder_v53_snapshot.py -q
```

---

## 5. Definition of Done

- [ ] Au moins **un** des trois blocs (A/B/C) **terminé** avec tests ; les blocs non faits = **reportés** avec ticket CTO référencé en tête du mandat J.
- [ ] Aucun fichier hors ALLOWLIST.
- [ ] Branche `feat/M-CTO-V53-D`.

---

## 6. Commits (exemples)

```
feat(M-CTO-V53-D): m14 workspace offers assembler
migration(M-CTO-V53-D): m13 blueprint persistence
feat(M-CTO-V53-D): pv snapshot includes M14 decision artifacts
```

---

*Mandat exécutable — périmètre fermé. Si trop large, le CTO scinde en D1/D2 avec ALLOWLIST distinctes.*
