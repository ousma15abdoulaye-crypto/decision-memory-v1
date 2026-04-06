# Worker ARQ sur Railway (VMS / Couche B)

Référence : DMS-FIX-VMS-PIPELINE-V001 — `vendor_market_signals` est alimenté après scellement par la tâche ARQ `project_sealed_workspace` et par le projector `project_workspace_events_to_couche_b`. Sans processus worker consommant Redis, les files ARQ ne sont pas traitées.

## Prérequis

- Même dépôt / même image que l’API (`Dockerfile` à la racine).
- Variables d’environnement partagées avec l’API (au minimum) :
  - `DATABASE_URL`
  - `REDIS_URL` (même instance Redis que l’API si rate limiting / ARQ unifiés)
- `PYTHONPATH` / layout : identique au conteneur API (`WORKDIR /app`).

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
