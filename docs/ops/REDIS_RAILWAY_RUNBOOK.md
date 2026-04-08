# Runbook Redis — Railway (P1-INFRA-01)

## Contexte

`REDIS_URL` est optionnel dans plusieurs chemins (ARQ, rate limiting). Sans Redis, les workers et la limitation de débit peuvent être dégradés ou inactifs.

## Actions recommandées

1. Créer un service **Redis** sur le projet Railway (même région que Postgres / API).
2. Lier la variable `REDIS_URL` au service **web** DMS (format `redis://...`).
3. Redéployer l’API ; vérifier les logs de démarrage : absence de warning « Redis non disponible » si le middleware ARQ est utilisé.
4. Documenter dans les variables Railway si un worker séparé consomme la même URL.

## Vérification

- Logs au boot : connexion pool Redis ou message explicite de dégradation.
- Sonde : `redis-cli -u "$REDIS_URL" PING` depuis un one-off container si besoin.

## Références

- Dette : [`docs/audit/DMS_TECHNICAL_DEBT_P0_P3.md`](../audit/DMS_TECHNICAL_DEBT_P0_P3.md) — P1-INFRA-01
