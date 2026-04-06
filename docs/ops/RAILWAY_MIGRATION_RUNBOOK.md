# Runbook — Migrations Railway DMS

**Gouvernance** : preuve live, GO CTO et checklist post-sync sont décrites dans [docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md](../adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md) (ne pas mettre à jour le MRD sans mesure `diagnose_railway_migrations.py`).

## Pre-requis

- CLI Railway relié au dépôt local : [RAILWAY_CLI_LOCAL_LINK.md](RAILWAY_CLI_LOCAL_LINK.md)
- `RAILWAY_DATABASE_URL` disponible (Railway Variables ou `.env.local`)
- Branche locale a jour avec `main` (ou branche de deploiement)
- Python 3.11+ avec `sqlalchemy`, `psycopg`, `alembic` installes

## Etape 1 — Diagnostic

```bash
python scripts/diagnose_railway_migrations.py
```

Sortie attendue :
- Head local : `056_evaluation_documents` (ou le dernier head)
- Revision DB : la revision actuelle de Railway
- Liste des migrations manquantes si ecart

## Etape 2 — Dry-run (simulation)

```bash
python scripts/apply_railway_migrations_safe.py
```

Le mode dry-run est le comportement par defaut (sans `--apply`).
Verifie le nombre de migrations en attente sans rien appliquer.

Note : le flag `--dry-run` n'existe pas dans ce script. Omettre `--apply` suffit.

## Etape 3 — Application

```bash
python scripts/apply_railway_migrations_safe.py --apply
```

Le script :
1. Applique chaque migration une par une
2. Verifie que la revision a bien avance apres chaque etape
3. S'arrete immediatement si une migration echoue
4. Affiche le temps par migration

## Etape 4 — Verification post-migration

```bash
python scripts/diagnose_railway_migrations.py
```

Doit afficher `[OK] La DB est synchronisee avec le head local.`

## Etape 5 — Activer les migrations automatiques (optionnel)

Dans Railway Variables, ajouter :
```
DMS_ALLOW_RAILWAY_MIGRATE=1
```

Cela permet a `start.sh` d'executer `alembic upgrade head` a chaque deploiement.

## Rollback

Alembic supporte le downgrade :
```bash
alembic downgrade <revision_precedente>
```

ATTENTION : certaines migrations contiennent des `DROP` irreversibles.
Toujours verifier le contenu de la migration avant downgrade.

## Remédiation post-audit

Après une due diligence ou un écart détecté entre DB et head, voir [`POST_DD_RISK_REMEDIATION_2026-04-06.md`](POST_DD_RISK_REMEDIATION_2026-04-06.md) (preuve dry-run / apply / décision `DMS_ALLOW_RAILWAY_MIGRATE`).

## Signaux STOP (CLAUDE.md)

- STOP-1 : `alembic heads` retourne plus d'une ligne → ne pas deployer
- STOP-2 : une correction necessite de modifier une migration existante → CTO
