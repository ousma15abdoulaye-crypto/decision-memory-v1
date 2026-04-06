# Matrice CI vs Railway — PostgreSQL

**Objectif :** documenter l’écart de version entre les tests CI et la base Railway (finding DD-003), sans prétendre à l’exhaustivité des différences de moteur.

| Environnement | Version observée | Usage |
|---------------|------------------|--------|
| CI GitHub Actions (`ci-main.yml`) | **Postgres 15** (`pgvector/pgvector:pg15`) | Migrations, tests, RLS `dm_app` avec superuser `postgres` pour setup |
| Railway (sonde 2026-04-06) | **Postgres 17.9** | Production / staging |

## Risques (honest)

- **Comportements divergents** : optimiseur, statistiques, certains détails d’index ou de verrous peuvent différer entre 15 et 17.
- **Extensions** : `pgvector` est présent en CI via l’image dédiée ; vérifier que l’extension et les versions sont cohérentes avec Railway pour les fonctionnalités qui en dépendent.
- **« Vert en CI »** ne prouve pas ligne à ligne le comportement en prod ; les tests d’intégration réduisent mais n’éliminent pas l’écart.

## Mitigations

1. Garder **une seule tête Alembic** et des migrations testées en CI avant apply prod (runbook).
2. **Moyen terme :** monter la CI sur **Postgres 17** (service container) pour rapprocher la vérité de test de la prod — mandat d’équipe (temps, flakiness, image disponible).
3. Sondes **read-only** sur Railway (`preflight_cto_railway_readonly.py`, `diagnose_railway_migrations.py`) après changements sensibles.

## Références

- [`.github/workflows/ci-main.yml`](../../.github/workflows/ci-main.yml)
- [`docs/audits/DUE_DILIGENCE_DMS_LOCAL_RAILWAY_2026-04-06.md`](../audits/DUE_DILIGENCE_DMS_LOCAL_RAILWAY_2026-04-06.md)
