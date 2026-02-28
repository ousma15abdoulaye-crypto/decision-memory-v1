# ADR-M2B-001 — Hardening DB + Migrations M2B

## Statut
PROPOSÉ

## Date
2026-02-26

## Contexte

M2 terminé — tag v4.1.0-m2-done · CI 574 passed · 0 failed.
M2B inséré hors freeze initial V4.1.0 pour empêcher
la dette fraîche de contaminer M3+.

Preuves PROBE complètes :

| Item | Résultat PROBE |
|---|---|
| users.created_at | TEXT · formats mixtes ISO datetime + date-only · cast UTC possible |
| FK NOT VALID | fk_pipeline_runs_case_id · 166 orphelins DB locale · prod non sondée |
| role_id usages | 7 usages runtime · 2 fichiers · DROP BLOQUÉ |
| 4 skipped suspects | 4/4 légitimes · 1 message skip erroné à corriger |
| comptes smoke prod | DB locale propre · Railway prod à confirmer |
| downgrades 037/038 | cycle downgrade/upgrade/pytest vert · DETTE-ALEMBIC-01 FERMÉE |
| ruff / black | 0 erreur baseline |

## Décision

Insertion de M2B entre M2 et M3.

STOP-M2B-2 levé :
  Migration 039 autorisée pour users.created_at uniquement.
  Formulation de cast fixée :
    USING created_at::timestamp AT TIME ZONE 'UTC'
  Raison : cast::timestamptz brut dépend du TimeZone de session.
  Formulation UTC explicite = déterministe entre environnements.

STOP-M2B-3 — résolution finale :
  Le DELETE des 166 orphelins DB locale est impossible.
  Raison : trigger trg_pipeline_runs_append_only (ADR-0012)
           BEFORE DELETE sur pipeline_runs lève une exception.
  Décision : ADR-0012 prime. Trigger non désactivé.
  DB locale : NOT VALID assumé et documenté — DETTE-M0B-01 ouverte.
  DB prod   : VALIDATE CONSTRAINT déplacé en ACTE 6
              après PROBE orphelins prod.
  Nouvelle dette : DETTE-FIXTURE-01 tracée.

## Périmètre retenu

### Bloc A — non destructif

A1. Correction skip reason test_depot_dashboard_and_export
    "Endpoint non encore implémenté (Milestone 2B / M5)"
    →  "Endpoint non encore implémenté — prévu M5"

A2. Création scripts/runbook_m2b_local.sql
    Contenu : COUNT orphelins · DELETE orphelins · COUNT post-purge
              VALIDATE CONSTRAINT · SELECT confirmation

A3. Mise à jour TECHNICAL_DEBT.md
    DETTE-ALEMBIC-01 : FERMÉE
    DETTE-M2-04      : en cours · prod à confirmer
    DETTE-M0B-01     : runbook local préparé · prod en attente
    DETTE-M1-04      : active · role_id 7 usages · DROP bloqué

### Bloc B — destructif conditionnel

B1. Migration 039 — schéma uniquement
    ALTER TABLE users
      ALTER COLUMN created_at TYPE TIMESTAMPTZ
      USING created_at::timestamp AT TIME ZONE 'UTC'
    downgrade() inverse testé.
    Contenu posté et validé humainement avant alembic upgrade.

B2. Runbook local scripts/runbook_m2b_local.sql
    Exécuté après B1 ou indépendamment.
    Résultats postés avant VALIDATE CONSTRAINT.

B3. Runbook prod Railway
    PROBE orphelins prod en premier.
    Backup Railway confirmé humainement.
    Si orphan_count = 0 → VALIDATE CONSTRAINT.
    Si orphan_count > 0 → IDs postés · décision humaine · DELETE sur IDs explicites.

## Exclusions définitives

- DROP users.role_id : BLOQUÉ — 7 usages runtime confirmés
- Audit global 36 skipped : hors scope
- Refactor auth : hors scope
- Toute feature métier : hors scope
- Tout fichier hors périmètre : interdit

## Préconditions destructives

- Backup Railway confirmé humainement avant migration 039 sur prod
- PROBE orphelins prod avant VALIDATE sur prod
- Contenu migration 039 posté et validé avant alembic upgrade
- GO humain explicite avant chaque item Bloc B

## Plan de rollback

Bloc A : non destructif — pas de rollback nécessaire.

Migration 039 :
  alembic downgrade -1
  → restore users.created_at TYPE TEXT
  Cycle testé : downgrade -1 → upgrade head → pytest vert requis.
  Le downgrade restaure users.created_at en TEXT, mais ne garantit
  pas la restitution exacte du format textuel historique ligne à ligne ;
  il restaure une représentation textuelle cohérente.

Runbook prod :
  Backup Railway permet restore complet si nécessaire.
  DELETE sur IDs explicites uniquement — pas de purge pattern.

## Conséquences

- Socle durci avant M3
- users.created_at correct — requêtes temporelles fiables
- FK validée après runbook — intégrité référentielle garantie
- DROP role_id reporté post-M2B — préconditions non réunies
- DETTE-ALEMBIC-01 soldée

## Auteur
CTO DMS V4.1.0 — 2026-02-26
