# Checklist Railway — Redis, API et worker ARQ

**Objectif :** réduire le risque DD-006 (worker sans `REDIS_URL` opérationnel, `redis_settings=None` dans [`src/workers/arq_config.py`](../../src/workers/arq_config.py)).

## Variables

| Service Railway | Variable | Rôle |
|-----------------|----------|------|
| API DMS | `REDIS_URL` | Rate limiting (`slowapi`) — dégradation possible si absent |
| Worker ARQ | `REDIS_URL` | File de jobs ARQ — **obligatoire** pour exécuter les tâches |
| Les deux | `DATABASE_URL` | PostgreSQL partagé |

**Vérification :** dans le dashboard Railway, confirmer que le **worker** réutilise la même instance Redis que celle prévue pour l’API (ou documenter pourquoi non).

## Au démarrage

1. Logs du service **worker** : absence de traceback Redis / connexion refusée.
2. Logs du service **API** : si `REDIS_URL` manquant, le rate limit peut être en mode no-op (voir [`src/ratelimit`](../../src/ratelimit) / middleware).

## Références

- [`docs/ops/RAILWAY_ARQ_WORKER_SERVICE.md`](RAILWAY_ARQ_WORKER_SERVICE.md)
- [`railway.worker.toml`](../../railway.worker.toml)
