# Timeline — suivi tests & merge (PR / main)

Document opérationnel pour **piloter une PR jusqu’au merge** sans perdre les gates CI ni l’état Alembic. À dupliquer ou adapter par PR (ex. copier la section « Checklist PR #___ » en bas).

---

## Principes

| Gate | Workflow GitHub (nom affiché) | Bloquant merge ? |
|------|--------------------------------|------------------|
| Lint | `CI Main` → Ruff + Black | Oui |
| Alembic | `CI Main` → single head + `upgrade head` | Oui |
| Auth audit | `CI Main` → audit FastAPI | Oui |
| Tests + couverture | `CI Main` → `pytest tests/` + `--cov-fail-under` | Oui |
| Annotation / M12 | `CI Main` → pytest services + export + validate | Oui |
| Milestones / invariants | `CI — Milestone Gates + Invariants` (si branches couvertes) | Selon config |
| Freeze / autres | Voir onglet **Checks** de la PR | Selon |

**Seuil de couverture** : si le fichier `.milestones/M-TESTS.done` est présent sur la branche, `pytest` utilise **`--cov-fail-under=65`**. Sinon le seuil est **0** (CI ne bloque pas sur la couverture).

---

## Phase 0 — Avant push (machine locale)

Exécuter dans l’ordre (PowerShell ; adapter le chemin repo) :

```powershell
cd <repo>
$env:PYTHONPATH = (Get-Location).Path

# 1) Lint (identique CI Main)
ruff check src tests
black --check src tests

# 2) Tests sans DB (rapide)
python -m pytest tests/cognitive/ tests/test_cognitive_helpers_unit.py tests/test_046b_imc_map_fix.py -q --tb=short

# 3) Si Postgres local disponible + DATABASE_URL
#    alembic upgrade head
#    python -m pytest tests/ -q --tb=short --cov=src --cov-fail-under=65
```

**Invariant Alembic (E-85 / ANCHOR-05)** : à chaque **nouvelle migration** qui devient `head`, ajouter la révision **`revision = "..."`** dans le tuple **`VALID_ALEMBIC_HEADS`** de `tests/test_046b_imc_map_fix.py` **dans le même PR**. Sinon : `AssertionError: Head inattendu : <nouvelle_migration>` en CI.

---

## Phase 1 — Après push (GitHub)

1. Ouvrir la PR → onglet **Checks**.
2. Attendre **CI Main** (vert).
3. Si **Milestone Gates** est déclenché : second passage `pytest` + couverture — même exigence de seuil si `M-TESTS.done` présent.

### Échecs fréquents & correctif

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| `Head inattendu : 079_...` | `VALID_ALEMBIC_HEADS` non étendu | Ajouter `078_...` et `079_...` (ou le nouveau head) dans `tests/test_046b_imc_map_fix.py` |
| `COVERAGE FAILED` / sous 65 % | Nouveau code `src/` peu couvert par les tests | Ajouter tests unitaires (mocks) ou tests d’intégration ciblés |
| `black --check` / `ruff check` | Format ou imports | `black src tests` ; `ruff check --fix …` dans le périmètre |
| Auth audit `FAIL — routes missing get_current_user` | Route sensible sans dépendance JWT | Vérifier `Depends(get_current_user)` sur les routes concernées |
| `alembic heads` ≠ 1 | Deux têtes de migration | Migration de fusion Alembic |

---

## Phase 2 — Review humaine

- [ ] Revue code (Tech Lead / pair).
- [ ] Vérifier **runbook migrations** si la PR ajoute `alembic/versions/**` (Railway / prod) : `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md`.
- [ ] Aligner **`docs/freeze/MRD_CURRENT_STATE.md`** / **`CONTEXT_ANCHOR.md`** (section Alembic) **après** décision CTO — souvent **post-merge** ou PR docs dédiée.

---

## Phase 3 — Merge

- [ ] Tous les checks **required** verts sur `main`.
- [ ] Merge PR vers `main` : **agent** après CI verte et garde-fous (`CLAUDE.md` § DÉCISION CTO — PR).
- [ ] Tag / release si process produit l’exige.

---

## Phase 4 — Post-merge (déploiement)

- [ ] `alembic upgrade head` sur l’environnement cible **avant** ou selon fenêtre de déploiement.
- [ ] Vérifier `SELECT version_num FROM alembic_version;` = head attendu.
- [ ] Smoke API / Label Studio selon périmètre.

---

## Journal (à compléter par PR)

| Date | Étape | Résultat | Notes |
|------|--------|----------|--------|
| | Phase 0 locale | | |
| | CI Main vert | | |
| | Milestone Gates | | |
| | Review | | |
| | Merge | | |
| | Prod / Railway | | |

---

## Références repo

- `docs/freeze/CONTEXT_ANCHOR.md` — **E-85**, **E-71** (`VALID_ALEMBIC_HEADS`).
- `.github/workflows/ci-main.yml` — ordre réel des jobs.
- `.github/pull_request_template.md` — checklist migration + `VALID_ALEMBIC_HEADS`.
