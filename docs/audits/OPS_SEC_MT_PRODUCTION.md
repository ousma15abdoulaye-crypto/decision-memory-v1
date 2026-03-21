# Runbook ops — SEC-MT (Redis, secrets, santé)

## Redis (rate limiting)

- Variable **`REDIS_URL`** : définir en production (ex. Railway Redis). Sans elle, le middleware retombe en **no-op** (requêtes toujours acceptées) avec log **WARNING** ; en environnement marqué production (`RAILWAY_ENVIRONMENT=production` ou `ENV=production`), le même cas est loggé en **ERROR** pour visibilité ops.
- **Local :** `docker compose --profile full up` démarre **Postgres + Redis + API** (voir [`docker-compose.yml`](../../docker-compose.yml) à la racine) pour reproduire le chemin rate-limit réel ; la stack DB seule reste `docker compose up postgres`.
- Le rate limit est **best-effort** (RÈGLE-04) : jamais source de vérité métier.

## Secrets

- **`SECRET_KEY`** / **`JWT_SECRET`** : rotation documentée côté équipe ; tokens émis avant rotation deviennent invalides après déploiement de la nouvelle clé.
- **Base** : l’application en production doit utiliser un rôle PostgreSQL **non superuser** avec **NOBYPASSRLS** (ex. `dm_app` + mot de passe fort), pas `postgres`.

## Santé

- **`GET /api/health`** (sur `main:app` et `src.api.main:app`) : inclut `database: ok|error` (ping SQL via `get_db_cursor`). Si **`REDIS_URL`** est défini, tente un `PING` court (`redis` : `ok|error`). Le statut global reste `healthy` si la DB répond ; sinon `degraded`.

## Références

- `src/couche_a/auth/middleware.py`
- `src/api/health.py`
- [`SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md)
