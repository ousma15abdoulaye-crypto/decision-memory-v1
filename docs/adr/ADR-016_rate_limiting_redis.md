# ADR-016 — Rate Limiting Redis Production

Date    : 2026-03-17  
Statut  : ACCEPTÉ  
Auteur  : Abdoulaye Ousmane — CTO  
Réf     : ASAP-07, ASAP-08, audit CTO senior 2026-03-17

## Contexte

L'audit CTO senior 2026-03-17 a révélé deux problèmes critiques :

1. **ASAP-07** : Le rate limiting utilisait `memory://` en fixe — non persistant entre restarts, non partagé entre instances.
2. **ASAP-08** : La ligne `limiter.limit = conditional_limit` (ancienne L63 de ratelimit.py) écrasait silencieusement la méthode `limit()` de slowapi. Tous les `@limiter.limit("5/minute")` dans auth_router.py, couche_a/routers.py et api/cases.py étaient des **no-ops** — les routes croyaient être protégées, elles ne l'étaient pas depuis le début du projet.

## Décision

### Storage

- **Production** : `REDIS_URL` → Redis (persistant, partagé entre instances).
- **Test** : `TESTING=true` → `memory://`.
- **Fallback** : Sans `REDIS_URL` → `memory://` avec warning explicite (configurer REDIS_URL sur Railway).

### Limiter natif restauré

- Supprimer la ligne `limiter.limit = conditional_limit`.
- Le limiter slowapi natif reprend son rôle.
- Tous les `@limiter.limit()` existants redeviennent actifs.

### API publique

- `route_limit(rate)` : alias propre de `limiter.limit()` pour lisibilité.
- `conditional_limit()` : lève `RuntimeError` avec ref ASAP-08 — interdiction d'utilisation.
- Constantes `LIMIT_AUTH`, `LIMIT_UPLOAD`, etc. — figées, modification GO CTO obligatoire.

### Configuration Railway

- Variable d'environnement `REDIS_URL` à configurer dans Railway Dashboard.
- Log attendu au démarrage : `[RATELIMIT] Redis — production mode`.

## Périmètre

- `src/ratelimit.py` — refonte complète
- Routes auth, upload, scoring, export — désormais réellement limitées

## Conséquences

- Routes auth protégées contre brute-force (10/minute).
- Rate limiting persistant en production.
- INV-01 strict : 0 sqlalchemy dans src/ (ASAP-09 corrigé en parallèle).
