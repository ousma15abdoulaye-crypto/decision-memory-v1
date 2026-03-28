# Migration de machine (débranchement → rebranchement)

Guide pour passer d’un PC à un autre (ex. copie sur disque externe) **sans perdre secrets ni données locales ignorées par Git**.

> Migrations **Alembic** (schéma PostgreSQL) : voir [`migration-checklist.md`](migration-checklist.md) — autre sujet.

---

## Procédure complète — nouveau PC (OneDrive ou dossier copié)

Objectif : le successeur ouvre ce fichier, exécute les commandes **dans l’ordre**, sans improviser. Le code, `data/`, `.env` arrivent via **OneDrive** (ou clé USB) : la même arborescence doit être **100 % synchronisée** avant de travailler sur le nouveau PC.

### A. Avant de basculer sur le nouveau PC (ancien PC ou OneDrive)

1. Fermer Cursor, arrêter Docker utile au projet :  
   `docker compose down` (depuis la racine du repo, si tu utilisais Docker).
2. Laisser **OneDrive terminer la synchronisation** (icône sans fichier en attente). Éviter d’éditer le repo sur les deux PC en même temps le jour J.
3. Sur l’ancien PC, optionnel mais utile : à la racine du repo, lancer  
   `.\scripts\verify_migration_bundle.ps1`  
   et noter ce qui manque (`.env`, exports JSONL, `.r2_export_env`, etc.).

### B. Sur le nouveau PC — prérequis logiciels (une fois)

Installer dans cet ordre (liens officiels) :

1. **Python 3.11.x** — https://www.python.org/downloads/ — cocher **Add python.exe to PATH**.
2. **Git** — https://git-scm.com/download/win
3. **Docker Desktop** — https://www.docker.com/products/docker-desktop/ — redémarrage Windows si demandé ; au premier lancement, accepter l’intégration WSL2 si proposée.

Fermer et rouvrir le terminal PowerShell après installation pour que le `PATH` soit à jour.

### C. Où est le dossier du projet ?

Exemples : `C:\Users\<toi>\OneDrive\...\decision-memory-v1` ou `C:\dev\decision-memory-v1`.  
Toutes les commandes ci-dessous supposent que tu **remplaces** le chemin par le tien.

Ouvrir **PowerShell** (pas besoin d’admin pour cette procédure), puis :

```powershell
cd C:\chemin\vers\decision-memory-v1
```

Vérifier que les fichiers sensibles ont bien voyagé avec OneDrive :

```powershell
Test-Path .env
Test-Path .env.local
Test-Path data\annotations\m12_corpus_from_ls.jsonl
```

Si `.env` est absent, la copie OneDrive est incomplète ou le fichier était hors du dossier synchronisé : le recoller depuis une sauvegarde.

### D. Supprimer l’ancien `.venv` si le dossier a été synchronisé avec l’ancien PC

Le dossier `.venv` contient des binaires liés à la machine source. **Ne pas** réutiliser un `.venv` copié tel quel : erreurs bizarres possibles.

```powershell
cd C:\chemin\vers\decision-memory-v1
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
```

Si `.venv` n’existe pas, cette commande ne fait rien (c’est normal).

### E. Premier lancement automatisé (recommandé)

À la racine du repo, **double-cliquer** sur :

`PREMIER_DEMARRAGE.bat`

Ou en ligne de commande :

```powershell
cd C:\chemin\vers\decision-memory-v1
.\PREMIER_DEMARRAGE.bat
```

Ce batch appelle `scripts\premier_demarrage.ps1`, qui enchaîne : création `.venv`, `pip install` des deux `requirements.txt`, `docker compose up -d postgres` si Docker est là, puis `alembic upgrade head`.

Si une étape échoue, lire le message ; corriger (Docker démarré ? `.env` avec un `DATABASE_URL` local cohérent ? port 5432 libre ?) puis relancer le `.bat`.

### F. Équivalent manuel (si tu ne veux pas du `.bat`)

Même résultat que le script, à la main :

```powershell
cd C:\chemin\vers\decision-memory-v1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r services\annotation-backend\requirements.txt
docker compose up -d postgres
Start-Sleep -Seconds 8
.\.venv\Scripts\alembic.exe upgrade head
```

### G. Vérifications après installation

Toujours à la racine :

```powershell
cd C:\chemin\vers\decision-memory-v1
.\scripts\verify_laptop_setup.ps1
.\scripts\verify_migration_bundle.ps1
```

Tests optionnels mais conseillés :

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

### H. Git sur le nouveau PC (branche courante)

Si le dossier vient de OneDrive **avec** l’historique `.git` :

```powershell
cd C:\chemin\vers\decision-memory-v1
git status
git fetch origin
git pull
```

Si le dossier **n’a pas** `.git` (copie fichier seule), cloner à côté puis fusionner les `data/` et `.env` à la main, ou recloner puis recopier `.env` et `data/` depuis OneDrive.

### I. Corpus M12 et export R2 (après coup)

Si `data\annotations\m12_corpus_from_ls.jsonl` est présent :

```powershell
.\.venv\Scripts\python.exe scripts\inventory_m12_corpus_jsonl.py data\annotations\m12_corpus_from_ls.jsonl
```

Réalignement avec Cloudflare R2 (nécessite `S3_*` dans `.env.local` ou `data\annotations\.r2_export_env`, pas seulement Label Studio) :

```powershell
.\.venv\Scripts\python.exe scripts\export_r2_corpus_to_jsonl.py -o data\annotations\m12_corpus_realigned.jsonl --project-id 1 --backfill-from-jsonl data\annotations\m12_corpus_from_ls.jsonl
```

### J. Rappels OneDrive

- Marquer le dossier du projet comme **Toujours garder sur cet appareil** sur le nouveau PC si tu travailles hors ligne.
- Ne pas committer de secrets : `.env`, `.r2_export_env`, `.ls_export_env`, `MISTRAL_KEY.txt` restent hors Git ; OneDrive les transporte, pas `git clone` seul.

---

## Faut-il copier tout le repo sur un disque ?

**Oui, si** tu veux éviter de re-télécharger des données et de reconfigurer à la main :

1. Copie le dossier du projet **tel qu’il est sur le disque** (racine `decision-memory-v1` ou équivalent), **y compris les fichiers que Git n’affiche pas** (`.env`, exports, clés, PDFs locaux).
2. Sur le nouveau laptop, colle ce dossier où tu veux travailler (ex. `C:\dev\decision-memory-v1`).

**Alternative** : `git clone` sur le nouveau PC, puis **recoller uniquement** les fichiers listés en § « À copier absolument » (pas le `.venv`).

**Ne pas copier** (recréable en quelques minutes) :

- `.venv/` — trop lourd et lié à l’ancienne machine ; à refaire avec `python -m venv .venv` + `pip install`.

---

## Vérifier que tout est là avant copie

À la racine du repo :

```powershell
.\scripts\verify_migration_bundle.ps1
```

Le script contrôle les fichiers **critiques** (Docker, Alembic, `requirements`, guide migration) et signale la présence des **fichiers souvent ignorés par Git** (`.env`, exports JSONL, `.ls_export_env`, etc.).

---

## Débranchement (ancien laptop)

- [ ] Fermer Docker / arrêter les conteneurs du projet si besoin (`docker compose down`).
- [ ] Fermer Cursor/VS Code sur ce repo.
- [ ] Copier **tout le dossier du repo** vers le disque externe (copie complète, pas seulement les fichiers suivis par Git).
- [ ] Vérifier que ces éléments **sont bien partis** sur le disque (sinon tu les perds) :

| Élément | Rôle |
|--------|------|
| `.env`, `.env.local` | `DATABASE_URL`, secrets API, etc. |
| `data/annotations/.ls_export_env` | Export Label Studio (optionnel) |
| `data/annotations/.r2_export_env` | Clés / endpoint export corpus **R2** (optionnel ; gitignoré) |
| `data/annotations/m12_corpus*.jsonl` | Exports corpus M12 (gitignorés) — ex. `m12_corpus_from_ls.jsonl` (**57 lignes** = 57 annotations dans **un** JSONL, pas 57 fichiers) |
| `data/annotations/r2_export.env.example` | Modèle pour `.r2_export_env` (versionné) |
| `data/regulatory/MISTRAL_KEY.txt` | Clé locale réglementaire (gitignoré) |
| `data/regulatory/raw/**` | PDFs bruts si tu les as en local |
| Autres sous `data/**` dont tu as besoin | Beaucoup de `.json` / CSV sont gitignorés |

- [ ] (Recommandé) Noter dans un gestionnaire de mots de passe : URL Railway, tokens LS, clés Mistral/Llama — **sans les coller dans le repo**.

---

## Rebranchement (nouveau laptop — ThinkPad ou autre)

**Raccourci si vous ne voulez pas lire toute la page :** à la racine du repo, ouvrir **`LISEZMOI_NOUVEAU_PC.txt`**, puis double-cliquer **`PREMIER_DEMARRAGE.bat`** après avoir installé Python 3.11 et Docker Desktop.

### 1. Prérequis à installer

- **Python 3.11+**
- **Git**
- **Docker Desktop** (recommandé pour PostgreSQL du `docker-compose.yml`)

### 2. Déposer le projet

Coller le dossier copié depuis le disque à l’emplacement voulu.

### 3. Ports à connaître

| Service | Port (défaut repo) |
|---------|-------------------|
| PostgreSQL (Docker) | **5432** (hôte) → conteneur 5432 |
| Redis (profil `full`) | **6379** |
| API (profil `full`) | **8000** |

Si un autre PostgreSQL utilise déjà **5432**, soit arrête-le, soit change le mapping dans `docker-compose.yml` (ex. `5433:5432`) **et** mets à jour `DATABASE_URL`.

### 4. Base de données

```powershell
cd C:\chemin\vers\decision-memory-v1
docker compose up -d postgres
```

Identifiants par défaut du compose : utilisateur **`dms`**, mot de passe **`dms`**, base **`dms`**.  
`DATABASE_URL` typique :

```text
postgresql+psycopg://dms:dms@localhost:5432/dms
```

Si tu utilises une base **locale hors Docker**, adapte `DATABASE_URL` et crée rôle/base (voir [`../audits/SETUP_STATUS.md`](../audits/SETUP_STATUS.md)).

### 5. Environnement Python

```powershell
cd C:\chemin\vers\decision-memory-v1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r services\annotation-backend\requirements.txt
```

### 6. Secrets

- Si tu as recopié **`.env`**, vérifie que les chemins et URLs sont encore valides pour **cette** machine (localhost, ports).
- Sinon : copier **`.env.example`** → **`.env`** et remplir.

**Règle projet** : `DATABASE_URL` en dev local ne doit pas pointer vers Railway ; une URL distante lecture seule se tient plutôt dans une variable séparée (ex. `RAILWAY_DATABASE_URL`). Voir `docs/adr/ADR-MRD2-GENETIC.md`.

### 7. Migrations et vérifs

```powershell
alembic upgrade head
.\scripts\verify_laptop_setup.ps1
```

Tests (optionnel mais conseillé) :

```powershell
pytest -q
```

---

## Script de vérification post-install

À la racine du repo :

```powershell
.\scripts\verify_laptop_setup.ps1
```

Il contrôle : présence de Python, `.venv`, `.env`, Docker, et tente un `docker compose ps` si le compose est présent.

---

## Corpus M12 après migration

- **Inventaire local** : `python scripts/inventory_m12_corpus_jsonl.py data/annotations/m12_corpus_from_ls.jsonl`
- **Réaligner avec Cloudflare R2** (nécessite `S3_*`, pas seulement Label Studio) :  
  `python scripts/export_r2_corpus_to_jsonl.py -o data/annotations/m12_corpus_realigned.jsonl --project-id 1 --backfill-from-jsonl data/annotations/m12_corpus_from_ls.jsonl`  
  Détail : `docs/m12/M12_EXPORT.md`, ancre `docs/freeze/MRD_CURRENT_STATE.md` (section CONTEXT ANCHOR).

---

## Résumé

| Question | Réponse |
|----------|---------|
| Je copie tout le repo sur un disque ? | **Oui** (recommandé), **sauf** tu peux ignorer `.venv` pour gagner de la place — à recréer sur place. |
| Git suffit seul ? | **Non** pour retrouver secrets + données `data/` gitignorées — il faut **recopier** ces fichiers ou tout le dossier disque. |
| Qui gère « débranchement / rebranchement » ? | **Toi** matériellement (copie disque) ; ce document + `verify_laptop_setup.ps1` **standardisent** la remise en route logicielle. |
