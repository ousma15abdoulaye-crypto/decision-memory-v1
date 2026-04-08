# PR — Alembic 093 : `assessment_history` (Canon V5.1.0)

## Objectif

Introduire la table **`assessment_history`** après la chaîne **`091 → 092`** (PR #351), sans modifier les révisions **091** ni **092**.

## Périmètre

- **Migration** `093_v51_assessment_history` : table, index, RLS + policy tenant (`app.tenant_id` / `app.current_tenant`, bypass admin).
- **Tests** : extension de `VALID_ALEMBIC_HEADS` dans `tests/test_046b_imc_map_fix.py` (invariant ANCHOR-05 / tête Alembic attendue en CI).

## Hors périmètre

- Pas de changement frontend.
- Pas de réécriture des migrations existantes.

## Référence canon

- DMS V5.1.0 — §5.4 / objectif **O6** (journal métier des changements sur critères d’évaluation).

## Vérifications locales recommandées

```powershell
python -m alembic heads
python -m alembic upgrade head
ruff check src tests services alembic/versions/093_v51_assessment_history.py
black --check src tests services alembic/versions/093_v51_assessment_history.py
```

## Déploiement

Après merge : exécuter **`alembic upgrade head`** sur les environnements cibles (ex. Railway) dans la fenêtre de maintenance habituelle.
