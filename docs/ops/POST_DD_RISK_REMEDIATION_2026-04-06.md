# Remédiation risques post due diligence — 2026-04-06

**Référence :** [`docs/audits/DUE_DILIGENCE_DMS_LOCAL_RAILWAY_2026-04-06.md`](../audits/DUE_DILIGENCE_DMS_LOCAL_RAILWAY_2026-04-06.md)  
**Plan :** correction risques post-DD (dry-run + migration 080 + livrables associés).

---

## DD-001 (S1) — Alembic Railway aligné sur head 080

**Statut :** résolu (migration appliquée).

| Étape | Commande / preuve |
|-------|-------------------|
| Pré-vol RO | `python scripts/with_railway_env.py python scripts/preflight_cto_railway_readonly.py` |
| Diagnostic | `python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py` |
| Dry-run | `python scripts/with_railway_env.py python scripts/apply_railway_migrations_safe.py` (sans `--apply`) |
| Apply | `python scripts/with_railway_env.py python scripts/apply_railway_migrations_safe.py --apply` |
| Post-sync | `diagnose_railway_migrations.py` → `[OK] La DB est synchronisee avec le head local.` |
| `alembic_version` | `080_market_signals_v2_zone_id_index` |
| Index | `SELECT indexname FROM pg_indexes WHERE indexname='idx_msv2_zone_id'` → `idx_msv2_zone_id` |

**Rollback d’urgence (si besoin) :** `alembic downgrade 079_bloc5_confidence_qualification_signal_log` ou `DROP INDEX IF EXISTS public.idx_msv2_zone_id` (équivalent migration 080).

---

## DD-004 (S3) — Décision `DMS_ALLOW_RAILWAY_MIGRATE` vs migrations manuelles

**Décision enregistrée (2026-04-06) :**

- **Par défaut (recommandé pour prod DMS) :** ne **pas** activer `DMS_ALLOW_RAILWAY_MIGRATE` sur le service API tant que le processus reste « migration manuelle validée » — aligné [`start.sh`](../../start.sh) et gouvernance Alembic.
- **Application des montées de version :** utiliser [`scripts/apply_railway_migrations_safe.py`](../../scripts/apply_railway_migrations_safe.py) (dry-run puis `--apply`) avec [`scripts/with_railway_env.py`](../../scripts/with_railway_env.py), puis vérifier avec `diagnose_railway_migrations.py` — voir [RAILWAY_MIGRATION_RUNBOOK.md](RAILWAY_MIGRATION_RUNBOOK.md).
- **Si `DMS_ALLOW_RAILWAY_MIGRATE=1` est activé un jour :** documenter le risque — chaque redéploiement exécute `alembic upgrade head` ([`start.sh`](../../start.sh)) ; utile pour environnements éphémères ou équipe très mature ; exiger CI verte et une seule tête Alembic (STOP-1).

---

## DD-003 (S2) — CI Postgres 15 vs Railway Postgres 17

**Court terme :** matrice de risque — [`CI_VS_RAILWAY_POSTGRES.md`](CI_VS_RAILWAY_POSTGRES.md).

**Moyen terme :** évaluer alignement CI sur Postgres 17 (image service GitHub Actions) quand le coût de migration de la CI est acceptable.

---

## DD-002 (S2) — Parité smoke `main:app`

**Statut :** smoke étendu — [`tests/test_main_app_parity_smoke.py`](../../tests/test_main_app_parity_smoke.py) vérifie les préfixes W1/W3 PV (`/api/workspaces`, `committee/seal`, `committee/pv`).

---

## DD-005 (S3) — Routes sensibles / heuristique SEC-MT

**Statut :** gabarit de revue — [`docs/audits/SEC_MT_SENSITIVE_ROUTES_REVIEW_TEMPLATE.md`](../audits/SEC_MT_SENSITIVE_ROUTES_REVIEW_TEMPLATE.md). Les gates CI (`audit_fastapi_auth_coverage.py --fail-prefix`) restent la barrière automatique ; la revue humaine tranche RLS vs guard manquant.

---

## DD-006 (S4) — Worker ARQ et `REDIS_URL`

**Statut :** checklist ops — [`RAILWAY_REDIS_WORKER_CHECKLIST.md`](RAILWAY_REDIS_WORKER_CHECKLIST.md). Validation manuelle des variables Railway (API + worker) et des logs au démarrage.

---

*Document vivant — ajouter date et preuve à chaque remédiation majeure.*
