# Rapport DoD — M0B DB Hardening

**Date :** 2026-02-27
**Branch source :** `feat/m0b-db-hardening`
**Merge target :** `main`
**Tag :** `v4.1.0-m0b-done`
**CI :** 491 passed · 35 skipped · 0 failed · 0 errors

---

## 1. Alembic — head unique

```
036_db_hardening (head)
```

Résultat : **1 seule tête** — conforme.

---

## 2. Colonnes `documents` — sha256 présent

| column_name       | data_type |
|-------------------|-----------|
| id                | text      |
| case_id           | text      |
| offer_id          | text      |
| filename          | text      |
| path              | text      |
| uploaded_at       | text      |
| mime_type         | text      |
| storage_uri       | text      |
| extraction_status | text      |
| extraction_method | text      |
| **sha256**        | **text**  |

Résultat : `sha256` présent, nullable (backfill requis — voir `TECHNICAL_DEBT.md`). **Conforme.**

---

## 3. FK `fk_pipeline_runs_case_id` — NOT VALID

| conname                    | convalidated |
|----------------------------|--------------|
| fk_pipeline_runs_case_id   | **False**    |

`convalidated = False` = contrainte créée `NOT VALID` — lignes orphelines préexistantes non bloquées.
Résultat : **Conforme** (décision STOP-2 actée).

---

## 4. Tables créées par migration 036

| table_name             | statut   |
|------------------------|----------|
| annotation_registry    | PRESENTE |
| committee_delegations  | PRESENTE |
| dict_collision_log     | PRESENTE |

Résultat : **3/3 tables présentes** — conforme.

---

## 5. Colonnes `extraction_jobs` — async

| column_name    | statut   |
|----------------|----------|
| fallback_used  | PRESENTE |
| max_retries    | PRESENTE |
| next_retry_at  | PRESENTE |
| queued_at      | PRESENTE |
| retry_count    | PRESENTE |

Résultat : **5/5 colonnes présentes** — conforme.

---

## 6. Contrainte UNIQUE et index `documents`

| élément                    | statut   |
|----------------------------|----------|
| `uq_documents_case_sha256` | PRESENTE |
| `idx_documents_case_id`    | PRESENT  |

Résultat : **Conforme.**

---

## 7. TECHNICAL_DEBT.md — sections ajoutées

Lignes de référence dans `TECHNICAL_DEBT.md` :

| Section | Ligne |
|---------|-------|
| FK NOT VALID (`pipeline_runs`) | 65 |
| Types PK non conformes (text vs uuid) | 161 |
| Colonnes ajoutées nullable — backfill requis | 171 |
| Risque flakiness CI multi-worker `_restore_schema` | (ajouté DoD) |

Résultat : **Conforme.**

---

## 8. Fichiers modifiés (périmètre)

```
TECHNICAL_DEBT.md
alembic/versions/036_db_hardening.py
tests/couche_a/test_migration.py
tests/db_integrity/test_pipeline_append_only_triggers.py
tests/pipeline/test_pipeline_a_e2e_mode.py
tests/pipeline/test_pipeline_a_partial_statuses.py
tests/test_m0b_db_hardening.py
```

Aucun fichier hors périmètre (`src/`, `alembic/env.py`, etc.) modifié.
Résultat : **Conforme.**

---

## 9. Checklist DoD complète

### Migration 036

| Item | Statut |
|------|--------|
| FK `pipeline_runs → cases` créée NOT VALID | ✅ |
| `committee_delegations` créée (member_id corrigé) | ✅ |
| `dict_collision_log` créée (canonical_id TEXT) | ✅ |
| `annotation_registry` créée (document_id TEXT) | ✅ |
| `extraction_jobs` : `next_retry_at` + `fallback_used` ajoutées | ✅ |
| `documents.sha256` ajouté nullable | ✅ |
| UNIQUE `(case_id, sha256)` créé | ✅ |
| `fn_reject_mutation()` créée | ✅ |
| Triggers append-only créés (IF EXISTS) | ✅ |
| `fn_sre_*` créées (3 fonctions) | ✅ |
| 8 index critiques créés | ✅ |

### Tests

| Item | Statut |
|------|--------|
| `tests/test_m0b_db_hardening.py` → tous VERT | ✅ |
| 11 tests FK corrigés → `case_factory()` | ✅ |
| `test_fk_rejects_ghost_case_id` → `pytest.raises` | ✅ |
| `test_upgrade_downgrade` → `_restore_schema` corrigé | ✅ |

### Schéma

| Item | Statut |
|------|--------|
| `alembic heads` → exactement 1 ligne | ✅ |
| Aucun fichier hors périmètre modifié | ✅ |

### Dette documentée

| Item | Statut |
|------|--------|
| FK NOT VALID (`pipeline_runs`) dans TECHNICAL_DEBT | ✅ |
| Types PK non conformes (text vs uuid) | ✅ |
| `documents.sha256` nullable (backfill requis) | ✅ |
| Risque flakiness `_restore_schema` multi-worker | ✅ |

### CI

| Item | Statut |
|------|--------|
| 491 passed · 0 failed · 0 errors | ✅ |

---

## 10. Décisions techniques actées

| Décision | Détail |
|----------|--------|
| STOP-2 : FK NOT VALID | Données orphelines `pipeline_runs` → FK créée sans validation. Validation différée (M1+). |
| STOP-5 : 11 tests FK | Tests modifiés pour utiliser `case_factory()` — FK réelle validée côté test. |
| `_restore_schema` flakiness | Risque low en CI séquentielle. Refactorisation recommandée si `pytest-xdist` activé. |

---

## Conclusion

**DoD M0B : VERT**

Merge `feat/m0b-db-hardening → main` effectué.
Tag `v4.1.0-m0b-done` posé et pushé sur `origin`.
