# Worker ARQ sur Railway (VMS / Couche B)

Référence : DMS-FIX-VMS-PIPELINE-V001 — `vendor_market_signals` est alimenté après scellement par la tâche ARQ `project_sealed_workspace` et par le projector `project_workspace_events_to_couche_b`. Sans processus worker consommant Redis, les files ARQ ne sont pas traitées.

## Prérequis

- Même dépôt / même image que l’API (`Dockerfile` à la racine).
- Variables d’environnement partagées avec l’API (au minimum) :
  - `DATABASE_URL`
  - `REDIS_URL` (même instance Redis que l’API si rate limiting / ARQ unifiés)
- `PYTHONPATH` / layout : identique au conteneur API (`WORKDIR /app`).
- **`UPLOADS_DIR`** : identique sur l’API et le worker (défaut applicatif : `/data/uploads`). Sans cela, le Pass -1 échoue : l’API écrit le ZIP, le worker le lit sur le disque.

## Volume partagé Pass-1 (upload ZIP → `run_pass_minus_1`)

Si l’API et le worker sont **deux services** Railway, le filesystem **n’est pas partagé** par défaut (`/tmp` inclus).

1. **Dashboard Railway** — pour le volume existant (ex. chemin interne du type `/var/lib/containers/.../vol_...`) : vérifier qu’il est **attaché aux deux services** (API + worker) avec le **même mount path** exposé au conteneur (souvent `/data` ou `/data/uploads` selon la config Railway).
2. **Variables** — sur **chaque** service :
   ```bash
   railway variables --service <nom-service-api> | findstr UPLOAD
   railway variables --service <nom-service-worker> | findstr UPLOAD
   ```
   Valeur attendue : la même, par ex. `UPLOADS_DIR=/data/uploads`, si le volume est monté sur `/data` et que les ZIP sont sous `.../uploads`.
3. **Logs** — au démarrage du worker : `[ARQ] UPLOADS_DIR (Pass-1) prêt : ...`. Côté API après upload : `[W1] ZIP Pass-1 enregistré ... path=...`.

Sans volume partagé, alternative documentée : passer le ZIP par **base de données ou objet** (bytea / S3) et un identifiant dans le job ARQ plutôt qu’un chemin disque.

## Créer le service worker

1. Dans le projet Railway **decision-memory-v1-production**, ajouter un **nouveau service** depuis le même dépôt GitHub.
2. **Build** : Dockerfile (comme l’API), ou laisser Railway détecter le `Dockerfile` racine.
3. **Deploy** — commande de démarrage :
   ```bash
   python -m arq src.workers.arq_config.WorkerSettings
   ```
   Alternative équivalente : `arq src.workers.arq_config.WorkerSettings` (si le CLI `arq` est dans le PATH).
4. Optionnel : pointer le service vers le fichier [`railway.worker.toml`](../../railway.worker.toml) comme configuration « config as code », si votre projet Railway lie un fichier par service.
5. **Pas** de `healthcheckPath` HTTP obligatoire pour un worker ARQ (pas de serveur HTTP). Utiliser les logs (`[SEAL-PROJ]`, `[PROJ]`).

## Vérification

- Logs du worker après un seal : messages `[W3] project_sealed_workspace enqueue` côté API, puis `[SEAL-PROJ]` côté worker.
- Script local : `python scripts/with_railway_env.py python scripts/smoke_arq_worker.py` (si `REDIS_URL` est dans `.env.railway.local`).

## Sécurité

Ne pas committer d’URL Redis ou secrets ; les variables restent dans Railway / `.env` local gitignored.
