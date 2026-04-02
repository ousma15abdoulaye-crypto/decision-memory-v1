# Relier le dépôt local au projet Railway (CLI)

Objectif : exécuter `railway` depuis la racine du repo (variables, logs, `railway run`) et alimenter `RAILWAY_DATABASE_URL` pour les scripts du runbook [RAILWAY_MIGRATION_RUNBOOK.md](RAILWAY_MIGRATION_RUNBOOK.md).

## Ce qui est versionné vs local

| Élément | Emplacement | Git |
|--------|-------------|-----|
| Lien projet / environnement | `.railway/` | **Ignoré** (voir `.gitignore`) — chaque poste crée son lien |
| `services/annotation-backend/railway.json` | Service annotation-backend | Versionné (build Docker, healthcheck) |

Ne jamais committer de secrets (URL DB, tokens).

## Prérequis

- **CLI** : `railway --version` (ex. 4.x). Installation si besoin : `npm install -g @railway/cli` ou `npx @railway/cli`.
- **Répertoire** : ouvrir un terminal à la **racine** du dépôt `decision-memory-v1`.

## 1. Authentification

### Option A — Navigateur (recommandé en local)

```powershell
railway login
```

Suivre l’ouverture du navigateur et valider la session.

### Option B — Token (CI ou sans navigateur)

1. Créer un token dans le compte Railway (Account → Tokens).
2. Sous PowerShell :

```powershell
$env:RAILWAY_TOKEN = "<token>"
railway whoami
```

Pour une session persistante sur le poste, préférer `railway login` plutôt que stocker le token dans un fichier.

## 2. Lier le répertoire au projet Railway

À la racine du repo, **une seule fois** (ou après clone sur une autre machine) :

### Option A — Interactif

```powershell
railway link
```

Choisir workspace, projet, environnement (ex. production) et éventuellement le **service** (stack annotation-backend si plusieurs services).

### Option B — Non interactif (si vous connaissez les identifiants)

```powershell
railway link -w "<workspace>" -p "<project-id-ou-nom>" -e "<environment>" -s "<service>"
```

Vérifier :

```powershell
railway status
railway whoami
```

Le dossier `.railway/` est créé localement ; il ne doit pas être ajouté à Git.

## 3. Obtenir l’URL PostgreSQL pour les scripts locaux

Les scripts attendent **`RAILWAY_DATABASE_URL`** (voir runbook). Deux approches courantes :

### A — Variables Railway (après lien)

```powershell
railway variables
```

Repérer `DATABASE_URL` (ou la variable que vous exposez pour la DB). Ne pas coller l’URL dans le chat ni dans un commit.

### B — Fichier local non versionné

Créer ou éditer **`.env.local`** (déjà ignoré par Git si configuré dans le projet) :

```env
RAILWAY_DATABASE_URL=postgresql+psycopg://...
```

Puis lancer les scripts Python depuis le même shell ou avec chargement explicite de `.env.local` selon votre habitude.

## 4. Commandes utiles après liaison

| Commande | Usage |
|----------|--------|
| `railway variables` | Lister les variables du service lié |
| `railway logs` | Flux de logs du déploiement |
| `railway run <cmd>` | Exécuter une commande avec les variables Railway injectées |

Exemple pour un diagnostic Alembic avec les mêmes vars que Railway :

```powershell
railway run python scripts/diagnose_railway_migrations.py
```

(Le script lit `RAILWAY_DATABASE_URL` ; s’assurer qu’elle est définie dans Railway ou dans l’environnement.)

## 5. Dépannage

- **Unauthorized** : relancer `railway login` ou définir `RAILWAY_TOKEN` valide.
- **Mauvais service / environnement** : `railway link` à nouveau ou `railway environment` selon la version du CLI (`railway environment --help`).
- **Plusieurs projets** : chaque clone peut avoir son `.railway/` ; vérifier `railway status` avant les opérations sensibles.

## Références

- Déploiement général : [docs/RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md)
- Migrations prod : [RAILWAY_MIGRATION_RUNBOOK.md](RAILWAY_MIGRATION_RUNBOOK.md)
- Gouvernance Alembic : [docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md](../adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md)
