# ADR — Gouvernance sync Railway / Alembic

**Statut** : accepté  
**Objectif** : éviter la dérive documentaire (E-82) et les migrations appliquées hors procédure sur Railway.

## A1 — Preuve live

Avant de certifier `railway_alembic_head` dans [`docs/freeze/MRD_CURRENT_STATE.md`](../freeze/MRD_CURRENT_STATE.md), exécuter :

`python scripts/diagnose_railway_migrations.py` avec `RAILWAY_DATABASE_URL` (ou `--db-url`) sur l’environnement cible.

Le script utilise l’API Alembic (`ScriptDirectory`) pour le head local et la chaîne base → head (pas un parse naïf des fichiers).

## A2 — Décision GO CTO

Tout `alembic upgrade` sur Railway reste sous **GO CTO** : fenêtre de maintenance, risque d’indisponibilité, rollback, variable `DMS_ALLOW_RAILWAY_MIGRATE` si applicable.

Références : [`docs/ops/RAILWAY_MIGRATION_RUNBOOK.md`](../ops/RAILWAY_MIGRATION_RUNBOOK.md), [`scripts/apply_railway_migrations_safe.py`](../../scripts/apply_railway_migrations_safe.py).

## A3 — Après sync réussie

Mettre à jour en cohérence :

- `MRD_CURRENT_STATE.md` (head Railway, last sync, pending vide ou à jour)
- [`docs/freeze/CONTEXT_ANCHOR.md`](../freeze/CONTEXT_ANCHOR.md) — bloc GIT/ALEMBIC
- [`scripts/validate_mrd_state.py`](../../scripts/validate_mrd_state.py) — `_KNOWN_MIGRATION_CHAIN` et `VALID_ALEMBIC_HEADS` dans les tests si nouveau head
