# Rapport — Mandat DMS-MIGRATION-PROD-V51-001

**Date (UTC)** : 2026-04-08  
**Objectif mandat** : aligner Railway PostgreSQL sur révision Alembic **090** (head dépôt).

## Écart par rapport au scénario nominal du mandat

| Attendu (mandat) | Constat pré-migration |
|---|---|
| `alembic current` = **079** | `alembic current` = **080** (`080_market_signals_v2_zone_id_index`) |

**Décision** : arrêt du scénario « 079→090 » ; exécution de **`alembic upgrade head`** depuis **080**, soit **10** révisions (**081→090**), et non 11.

## Phase 0 — Preuves

- **main** : à jour (≥ PR #345 / docs #346).
- **Fichiers** : migrations `080_*` … `090_*` présents ; `alembic heads` → un seul head **090**.
- **Dry-run SQL** : `alembic upgrade 080_market_signals_v2_zone_id_index:head --sql` — pas de `DROP TABLE` / `TRUNCATE` / `DELETE FROM` métier dans le script généré (hors `alembic_version`).
- **Santé DB** : PostgreSQL 17.x ; idle in transaction > 5 min = **0** ; ~212 tables ; taille ~60 MB (mesure au moment du check).

## Phase 1 — Sauvegarde

- **Snapshot Railway (Dashboard)** : à confirmer par **AO** (l’agent ne valide pas l’UI Railway).

## Phase 2 — Application

- Commande : `python scripts/with_railway_env.py python -m alembic upgrade head`
- Révisions appliquées : **081** → **082** → **083** → **084** → **085** → **086** → **087** → **088** → **089** → **090** (succès, exit 0).

## Phase 3 — Post-check (extrait)

- `alembic current` = **090_v51_extraction_jobs_langfuse_trace** (identique à `alembic heads`).
- Tables M16 attendues + `mql_query_log`, `assessment_comments` : présentes ; RLS **enabled + forced** sur l’échantillon contrôlé par `scripts/railway_migration_postcheck_v51_001.py`.
- Triggers : append-only / immutabilité sur `deliberation_messages` et `assessment_comments` listés par le script.
- **Note schéma** : l’historique M16 est la table **`criterion_assessment_history`** (pas `assessment_history`).

## Scripts de rejeu (audit)

- `scripts/railway_migration_precheck_v51_001.py`
- `scripts/railway_migration_postcheck_v51_001.py`

## Health HTTP

- Non exécuté depuis cet environnement (URL / réseau produit) — à valider côté déploiement Railway app.
