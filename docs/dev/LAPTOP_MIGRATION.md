# Migration de machine (débranchement → rebranchement)

Guide pour passer d’un PC à un autre (OneDrive, clé USB, dossier copié) **sans perdre secrets ni données locales ignorées par Git**.

> Migrations **Alembic** (schéma PostgreSQL) : voir [`migration-checklist.md`](migration-checklist.md) — autre sujet.

---

## Procédure complète — nouveau PC (OneDrive ou dossier copié)

Objectif : le successeur exécute les étapes **dans l’ordre**, sans improviser. Le code, `data/`, `.env` arrivent via **OneDrive** (ou copie manuelle) : la même arborescence doit être **synchronisée / complète** avant de travailler sur le nouveau PC.

### Garde-fous — STOP si…

- **`.env` absent** à la racine du repo (secrets et `DATABASE_URL` locaux).
- **Dossier corpus local absent** : `data\annotations` manquant alors que vous travaillez sur les exports M12 hors R2.
- **Docker Desktop** n’est pas démarré (icône tray : moteur prêt) **avant** `docker compose` ou `premier_demarrage.bat`.
- **`verify_laptop_setup.ps1`** ou **`verify_migration_bundle.ps1`** se termine avec **ECHEC** — corriger avant de poursuivre.
- **Branche Git** : si vous avez une branche imposée (mandat / release), vérifiez `git branch --show-current` ; pour un contrôle automatique, définissez `$env:DMS_EXPECT_GIT_BRANCH` avant `verify_laptop_setup.ps1`.
- **`alembic heads`** : doit afficher **exactement une** ligne de tête ; plusieurs heads → STOP (voir `migration-checklist.md`).

Versions : utilisez les versions **supportées par la CI du projet** — Python **3.11.x** (voir `.github/workflows/*.yml`, `pyproject.toml` cible `py311`), PostgreSQL via **`docker-compose.yml`** (image **postgres:16** pour le conteneur dev), **Git** et **Docker Desktop** récents stables. Si doute : alignez-vous sur les installateurs officiels listés ci-dessous.

---

### A. Avant de basculer sur le nouveau PC (ancien PC ou OneDrive)

1. Fermer Cursor, arrêter Docker utile au projet :  
   `docker compose down` (depuis la racine du repo, si vous utilisiez Docker).
2. Laisser **OneDrive terminer la synchronisation** (icône sans fichier en attente). Éviter d’éditer le repo sur les deux PC en même temps le jour J.
3. Sur l’**ancien** PC, à la racine du repo, lancer :  
   `.\scripts\verify_migration_bundle.ps1`  
   Corrigez tout **STOP** avant la dernière synchro (`.env`, `data\annotations`, un seul head Alembic si `.venv` est encore présent).

---

### B. Sur le nouveau PC — prérequis logiciels (une fois)

1. **Python 3.11.x** — https://www.python.org/downloads/ — cocher **Add python.exe to PATH**.
2. **Git** — https://git-scm.com/download/win
3. **Docker Desktop** — https://www.docker.com/products/docker-desktop/ — redémarrage Windows si demandé ; au premier lancement, accepter l’intégration WSL2 si proposée.

Fermer et rouvrir le terminal PowerShell après installation pour que le `PATH` soit à jour.

---

### C. Où est le dossier du projet ?

Exemples : `C:\Users\<toi>\OneDrive\...\decision-memory-v1` ou `C:\dev\decision-memory-v1`.

```powershell
cd C:\chemin\vers\decision-memory-v1
```

Vérifications minimales :

```powershell
Test-Path .env
Test-Path data\annotations
```

- Si **`.env` est absent**, la copie est incomplète ou le fichier était hors du dossier synchronisé : le recoller depuis une sauvegarde. **STOP.**
- Si **`data\annotations` est absent** alors que vous comptez sur des exports M12 locaux : **STOP** (ou recréez le dossier et réimportez depuis R2, voir § I).

---

### D. Supprimer l’ancien `.venv` si le dossier vient d’un autre PC

Le dossier `.venv` contient des binaires liés à la machine source. **Ne pas** réutiliser un `.venv` copié tel quel.

```powershell
cd C:\chemin\vers\decision-memory-v1
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
```

Si `.venv` n’existe pas, cette commande ne fait rien (normal).

---

### E. Docker Desktop avant premier bootstrap

1. Ouvrir **Docker Desktop**.
2. Attendre que l’application indique que le **moteur est prêt** (pas d’erreur « Docker Desktop starting… »).
3. Ensuite seulement : premier lancement batch (§ F).

**STOP** si vous lancez `docker compose` ou le `.bat` alors que Docker n’est pas prêt : échecs aléatoires sur Postgres.

---

### F. Premier lancement automatisé (recommandé)

À la racine du dépôt, le point d’entrée unique est le fichier versionné **`premier_demarrage.bat`**. Sous Windows, le système de fichiers est **insensible à la casse** : si votre guide ou votre habitude parle de **`PREMIER_DEMARRAGE.bat`**, c’est **le même fichier** que `premier_demarrage.bat` (ne pas créer un second `.bat` qui s’appelle pareil avec une autre casse : écrasement mutuel).

Double-clic ou :

```powershell
cd C:\chemin\vers\decision-memory-v1
.\premier_demarrage.bat
```

Comportement réel (référence code) : détection **Python 3.11**, création de **`.env`** minimale si absente, **`docker compose up -d`** si Docker est disponible, création **`.venv`**, `pip install -r requirements.txt`, **`alembic upgrade head`**, puis lancement **`uvicorn main:app`** (API locale). En cas d’erreur : lire le message ; vérifier Docker, `.env` / `DATABASE_URL`, port **5432** libre, puis relancer.

---

### G. Équivalent manuel (si vous ne voulez pas du `.bat`)

Aligné sur le batch canonique (sans lancer uvicorn) :

```powershell
cd C:\chemin\vers\decision-memory-v1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
docker compose up -d
Start-Sleep -Seconds 8
alembic upgrade head
```

*(Un second `requirements.txt` existe sous `services\annotation-backend\` pour le service déployé séparément ; le bootstrap racine ci-dessus suit `premier_demarrage.bat`.)*

---

### H. Vérifications après installation

Toujours à la racine :

```powershell
cd C:\chemin\vers\decision-memory-v1
.\scripts\verify_laptop_setup.ps1
.\scripts\verify_migration_bundle.ps1
```

**STOP** si l’un des deux scripts retourne une erreur.

Contrôle optionnel :

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

---

### I. Git sur le nouveau PC (branche, remote, synchro)

Si le dossier contient **`.git`** :

```powershell
cd C:\chemin\vers\decision-memory-v1
git status
git remote -v
git branch --show-current
git fetch origin
git pull
```

**STOP** si la branche courante n’est pas celle attendue pour votre travail (comparer avec le mandat / la release). Pour automatiser :  
`$env:DMS_EXPECT_GIT_BRANCH = "nom/branche"` puis `.\scripts\verify_laptop_setup.ps1`.

Si le dossier **n’a pas** `.git` : `git clone` dans un nouveau dossier, puis **fusionner** `.env` et `data/` depuis la copie OneDrive.

---

### J. Corpus M12 et export R2 (après coup)

Documentation à jour des scripts : **`docs/m12/M12_EXPORT.md`**.

- **Valider un JSONL** local :  
  `python scripts\validate_annotation.py data\annotations\<fichier>.jsonl`
- **Exporter depuis R2** (variables `S3_*` / bucket — voir le script et `ENVIRONMENT.md` backend) :  
  `python scripts\export_r2_corpus_to_jsonl.py --output data\annotations\m12_corpus_r2.jsonl`  
  (options : `--limit`, `--status`, etc. — détail dans l’en-tête du script et `M12_EXPORT.md`).

Il n’existe pas dans le dépôt de script nommé `inventory_m12_corpus_jsonl.py` : pour un inventaire rapide, listez les fichiers (`Get-ChildItem data\annotations\*.jsonl`) et utilisez la validation ci-dessus.

---

### K. Rappels OneDrive

- Marquer le dossier du projet comme **Toujours garder sur cet appareil** sur le nouveau PC si vous travaillez hors ligne.
- Ne pas committer de secrets : `.env`, `.r2_export_env`, `.ls_export_env`, clés locales sous `data/` restent hors Git ; OneDrive les transporte, pas `git clone` seul.

---

## Faut-il copier tout le repo sur un disque ?

**Oui, si** vous voulez éviter de re-télécharger des données et de reconfigurer à la main :

1. Copiez le dossier du projet **tel quel** (racine `decision-memory-v1`), **y compris** les fichiers que Git n’affiche pas (`.env`, exports, PDFs locaux).
2. Sur le nouveau laptop, collez où vous travaillez.

**Alternative** : `git clone`, puis **recoller** `.env` et `data/**` nécessaires.

**Ne pas copier** (recréable) : `.venv/`.

---

## Vérifier que tout est là avant copie

```powershell
.\scripts\verify_migration_bundle.ps1
```

---

## Débranchement (ancien laptop)

- [ ] `docker compose down` si besoin.
- [ ] Fermer Cursor/VS Code sur ce repo.
- [ ] Copie **complète** du dossier (pas seulement l’index Git).
- [ ] Vérifier le départ des éléments hors Git :

| Élément | Rôle |
|--------|------|
| `.env`, `.env.local` | `DATABASE_URL`, secrets API, etc. |
| `data/annotations/.ls_export_env` | Export Label Studio (optionnel) |
| `data/annotations/.r2_export_env` | Export corpus **R2** (optionnel) |
| `data/annotations/m12_corpus*.jsonl` | Exports M12 (gitignorés) |
| `data/regulatory/MISTRAL_KEY.txt` | Clé locale (gitignoré) |
| `data/regulatory/raw/**` | PDFs bruts locaux |

- [ ] Conserver tokens / mots de passe **hors** le dépôt (gestionnaire de secrets).

---

## Rebranchement (nouveau laptop) — raccourci

Ouvrir **`LISEZMOI_NOUVEAU_PC.txt`**, installer les prérequis, supprimer `.venv`, lancer **`premier_demarrage.bat`**, puis **`.\scripts\verify_laptop_setup.ps1`**.

### Ports (défaut repo)

| Service | Port (hôte) |
|---------|-------------|
| PostgreSQL (Docker) | **5432** |
| Redis (profil `full`) | **6379** |
| API (profil `full`) | **8000** |

Conflit **5432** : adapter `docker-compose.yml` **et** `DATABASE_URL`.

### Base de données (manuel)

Identifiants par défaut du compose : utilisateur **`dms`**, mot de passe **`dms`**, base **`dms`**.  
`DATABASE_URL` typique : `postgresql+psycopg://dms:dms@localhost:5432/dms`

---

## Résumé

| Question | Réponse |
|----------|---------|
| Je copie tout le repo ? | **Oui** (recommandé), **sauf** `.venv` à recréer. |
| Git suffit seul ? | **Non** pour secrets + `data/` gitignorés — recopier ces fichiers. |
| Où sont les vérifs ? | `.\scripts\verify_migration_bundle.ps1`, `.\scripts\verify_laptop_setup.ps1` |
