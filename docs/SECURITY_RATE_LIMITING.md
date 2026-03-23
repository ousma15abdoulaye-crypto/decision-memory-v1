# Rate limiting — comportement et multi-instances

## Implémentation

- **Bibliothèque** : `slowapi` — [`src/ratelimit.py`](../src/ratelimit.py).
- **Clé** : `get_remote_address` (IP client) — derrière un reverse proxy, s’assurer que l’IP réelle est transmise (`X-Forwarded-For`) si besoin métier.
- **Décorateurs** : `@limiter.limit(...)` sur `/auth/*` ; constantes `LIMIT_*` pour routes lourdes.

## Stockage

| Environnement | `REDIS_URL` | Comportement |
|---------------|-------------|--------------|
| Tests (`TESTING=true`) | ignoré | `memory://` + décorateurs **no-op** (évite 429 flaky en CI) |
| Prod **avec** `REDIS_URL` | défini | Compteurs **partagés** entre tous les workers — **recommandé** |
| Prod **sans** `REDIS_URL` | absent | `memory://` **par processus** : chaque worker a son propre compteur |

## Risque multi-workers sans Redis

Si plusieurs instances Uvicorn / Railway **sans** Redis :

- Une limite « 5/minute » devient en pratique **5 × N workers / minute** par IP (contournement partiel).
- Les limites restent utiles sur **une** instance ou pour limiter un client très abusif sur un seul worker.

**Recommandation enterprise-light** : définir **`REDIS_URL`** en production — voir [ADR-016](adr/ADR-016_rate_limiting_redis.md).

## Logs au démarrage

Le module log une description **non sensible** du backend (`backend=memory` ou `backend=redis host=...`) — jamais le mot de passe Redis dans l’URL complète n’est nécessaire ; en cas de doute, vérifier que `REDIS_URL` n’est pas loggé en entier ailleurs.
