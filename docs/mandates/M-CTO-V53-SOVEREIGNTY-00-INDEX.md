# M-CTO-V53-SOVEREIGNTY — Index des mandats exécutables (unification sources de vérité)

**Statut :** INDEX — à valider CTO avant exécution.  
**Autorité :** `docs/freeze/DMS_V4.1.0_FREEZE.md` → `docs/freeze/CONTEXT_ANCHOR.md` → mandats CTO → `docs/freeze/DMS_V4.2.0_ADDENDUM.md` → `docs/freeze/DMS_CANON_V5.1.0_FREEZE.md` → registres V5.2 (`docs/audit/RUPTURES_V52.md`, `V52_RECONSTRUCTION_COMPLETE.md`).  
**Règle périmètre :** chaque mandat ne modifie **que** les fichiers listés dans sa section **ALLOWLIST**. Tout fichier non listé → **STOP** (RÈGLE-ANCHOR-08 / `dms-core`).

---

## 1. Convention d’exécution (alignée dépôt)

| Élément | Valeur |
|--------|--------|
| **ID programme** | `M-CTO-V53-SOV` (alias court : V53 souveraineté) |
| **Branche par mandat** | `feat/M-CTO-V53-<PHASE>` (ex. `feat/M-CTO-V53-A`) — une PR = un mandat |
| **Commits** | `<type>(M-CTO-V53-<PHASE>): <description>` — types : `feat`, `fix`, `test`, `docs`, `ci`, `refactor`, `migration` (si Alembic dans le commit) |
| **Alembic** | Nouveau fichier sous `alembic/versions/` uniquement ; **jamais** modifier une révision déjà mergée ; **jamais** autogenerate |
| **Qualité Python** | Si `.py` sous `src/`, `tests/`, `services/` : `ruff check` + `black --check` avant commit |
| **Gel annotation** | Pas de refactor `services/annotation-backend/**` hors mandat CTO dégel explicite |

---

## 2. Ordre d’exécution (une seule ligne critique)

```
A → B → C → E → D → F → G → H → I → J
```

**Justification courte :** E (historique M16 unique) avant D (PV enrichi) évite d’intégrer dans le snapshot des données encore doubles.

---

## 3. Table des mandats

| Phase | Fichier mandat | Objet |
|-------|----------------|--------|
| A | [`M-CTO-V53-A-INVENTORY.md`](./M-CTO-V53-A-INVENTORY.md) | Inventaire écrivains/lecteurs + ADR préséance marché |
| B | [`M-CTO-V53-B-MARKET-UNIFY.md`](./M-CTO-V53-B-MARKET-UNIFY.md) | MQL + PV + deltas alignés sur `market_signals_v2` ; rôle de `vendor_market_signals` |
| C | [`M-CTO-V53-C-RBAC-UNIFY.md`](./M-CTO-V53-C-RBAC-UNIFY.md) | Un guichet accès + politique JWT fallback |
| E | [`M-CTO-V53-E-ASSESSMENT-HISTORY.md`](./M-CTO-V53-E-ASSESSMENT-HISTORY.md) | Réconciliation `criterion_assessment_history` vs `assessment_history` |
| D | [`M-CTO-V53-D-PIPELINE-PV.md`](./M-CTO-V53-D-PIPELINE-PV.md) | Assembleur M14, persistance M13 blueprint, PV (R2/R4/R6/R7) |
| F | [`M-CTO-V53-F-WORKSPACE-TIMELINE.md`](./M-CTO-V53-F-WORKSPACE-TIMELINE.md) | Timeline workspace + mémoire `workspace_id` |
| G | [`M-CTO-V53-G-ORGANS-M12-RAG.md`](./M-CTO-V53-G-ORGANS-M12-RAG.md) | Brancher `m12_correction_log` ; trancher RAG/pgvector |
| H | [`M-CTO-V53-H-LANGFUSE-OBS.md`](./M-CTO-V53-H-LANGFUSE-OBS.md) | Politique Langfuse prod + métadonnées coût/run |
| I | [`M-CTO-V53-I-COGNITIVE-MATRIX.md`](./M-CTO-V53-I-COGNITIVE-MATRIX.md) | Matrice E×permission ou alignement doc/code |
| J | [`M-CTO-V53-J-CI-CLOSEOUT.md`](./M-CTO-V53-J-CI-CLOSEOUT.md) | Gates CI, inventaire routes, clôture MRD (AO) |

---

## 4. Après merge série

- Mise à jour **`docs/freeze/MRD_CURRENT_STATE.md`** : **mandat J** ou mandat CTO AO dédié (selon gouvernance).
- Addendum **`docs/freeze/CONTEXT_ANCHOR.md`** : **AO uniquement** (RÈGLE-ANCHOR-01 : ajouts, pas résumé destructif).

---

*Index généré pour exécution séquentielle — DMS CTO Grade.*
