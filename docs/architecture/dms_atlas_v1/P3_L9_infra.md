# P3 — Livrable 9 : Infrastructure et déploiement

## 9.1 Railway (API)

- **Fichier** : [`railway.toml`](../../../railway.toml) — build Docker (`Dockerfile`), pas de `startCommand` forcé dans ce fichier (voir commentaire : `start.sh` / Dockerfile).
- **Worker ARQ** : [`railway.worker.toml`](../../../railway.worker.toml) + [`docs/ops/RAILWAY_ARQ_WORKER_SERVICE.md`](../../ops/RAILWAY_ARQ_WORKER_SERVICE.md) (référence ops).
- **RAM/CPU/région/custom domain** : **NON TRANCHÉ** dans le dépôt — configuration console Railway / variables d’environnement.

## 9.2 PostgreSQL (développement local)

[`docker-compose.yml`](../../../docker-compose.yml) :

- Image **`postgres:16`**
- Port **5432**

CI GitHub Actions ([`ci-main.yml`](../../../.github/workflows/ci-main.yml)) : **`pgvector/pgvector:pg15`** pour les tests.

**Paramètres `max_connections` / tuning prod** : **NON** versionnés dans ce repo.

## 9.3 Redis

[`docker-compose.yml`](../../../docker-compose.yml) : **`redis:7-alpine`**, port 6379 (profil `full`).

**Persistence RDB/AOF / maxmemory** : **NON TRANCHÉ** dans les fichiers cités — dépend du service managé (Railway) ou du `redis.conf` non présent ici.

Rôles : rate limiting ([`src/ratelimit.py`](../../../src/ratelimit.py)), middleware Redis ([`middleware.py`](../../../src/couche_a/auth/middleware.py)) — cache reconstructible (RÈGLE-04).

## 9.4 CI/CD

- **Workflow principal** : [`.github/workflows/ci-main.yml`](../../../.github/workflows/ci-main.yml)
- **Étapes clés** : install deps, `compileall`, garde **single Alembic head**, `alembic upgrade head`, Ruff, Black, audits auth FastAPI, **pytest** avec couverture `src` (voir L10).

**Environnements** : au minimum **CI** sur PR/push `main` ; staging/prod **NON** décrits comme workflows séparés dans ce fichier.

**Rollback** : **NON TRANCHÉ** — procédure Railway / runbook humain.

## 9.5 Monitoring

- **Health** : `GET /health` ([`main.py`](../../../main.py)), `GET /api/health` (router health).
- **Langfuse** : **NON** imposé par le code analysé pour ce livrable.
- **Dashboards** : **NON** dans le dépôt.
