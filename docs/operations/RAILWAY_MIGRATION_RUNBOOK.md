# Déplacé — source canonique

Le runbook opérationnel unique pour les migrations Railway DMS est :

**[docs/ops/RAILWAY_MIGRATION_RUNBOOK.md](../ops/RAILWAY_MIGRATION_RUNBOOK.md)**

Ce fichier ne doit plus être dupliqué (E-82 — une seule source de vérité). Toute référence historique à `docs/operations/RAILWAY_MIGRATION_RUNBOOK.md` pointe ici ou vers le lien ci-dessus.

Pour historique et lots sécurisés (probes `probe_alembic_head`, `probe_railway_counts`), voir les sections du runbook canonique et `scripts/apply_railway_migrations_safe.py`.
